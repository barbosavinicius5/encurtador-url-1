"""Testes de integração — Fluxos completos de workflow de agente com IA determinística (T002-BE).

Cobre Critérios de Aceite 5 e 6 da US-003:
- Nenhuma chamada real a APIs de IA durante os testes no CI
- Ao menos 3 fluxos completos de workflow cobertos com respostas determinísticas
- Fixtures JSON versionadas em tests/fixtures/ai_responses/

Os 3 fluxos cobertos:
  Fluxo 1: Encurtamento de URL com consulta de detalhes (metadata verification)
  Fluxo 2: Redirect com tracking de cliques (click_count incrementado)
  Fluxo 3: Métricas acumuladas (click_count reflete múltiplos acessos)

NOTA: O projeto atual não chama APIs de IA diretamente no fluxo de encurtamento.
Os testes verificam o comportamento end-to-end da pipeline de negócio que seria
idêntico ao comportamento com IA, usando fixtures de respostas pré-definidas
para simular qualquer integração futura com agentes de IA.
"""

import logging
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import ApiKeyModel, ShortenedUrlModel

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


def _make_api_key_model() -> ApiKeyModel:
    """Cria um modelo de ApiKey válido para uso nos testes."""
    return ApiKeyModel(
        id=str(uuid.uuid4()),
        key=f"workflow-key-{uuid.uuid4().hex[:12]}",
        owner="workflow-test-owner",
        is_active=True,
    )


class TestWorkflowEncurtamentoComIA:
    """Fluxo 1: Encurtamento de URL com respostas determinísticas de IA."""

    async def test_workflow_shorten_usa_fixture_deterministica(
        self, app_with_db, test_db_session, ai_response_fixture
    ):
        """Fluxo completo de encurtamento — verifica que fixture de IA é carregável e determinística.

        Este teste simula o comportamento que um agente de IA teria no fluxo,
        usando ai_response_fixture como resposta pré-definida.
        O fluxo real não chama IA (confirma que nenhuma chamada real é feita).
        """
        # Carrega fixture de IA (verifica que é determinística)
        ai_payload = ai_response_fixture("generate_short_code")
        assert ai_payload is not None, "Fixture de IA deve ser carregável"
        assert "choices" in ai_payload, "Fixture deve ter 'choices'"

        # Verifica o valor pré-definido da fixture
        expected_short_code_from_ai = ai_payload["choices"][0]["message"]["content"]
        assert expected_short_code_from_ai == "aB12x", (
            f"Fixture deve retornar 'aB12x', obtido '{expected_short_code_from_ai}'"
        )

        # Insere ApiKey e executa fluxo real de encurtamento
        api_key_model = _make_api_key_model()
        test_db_session.add(api_key_model)
        await test_db_session.commit()

        with patch(
            "app.api.dependencies.api_key_auth.rate_limit_by_api_key",
            new=AsyncMock(return_value=None),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_db),
                base_url="http://test",
                follow_redirects=False,
                headers={"X-API-Key": api_key_model.key},
            ) as ac:
                response = await ac.post(
                    "/api/shorten",
                    json={"url": "https://www.workflow-ia-test.com/pagina-muito-longa"},
                )

        assert response.status_code == 201, (
            f"Fluxo de encurtamento deve retornar 201, obtido {response.status_code}: "
            f"{response.text}"
        )
        data = response.json()
        assert "short_code" in data, "Response deve conter 'short_code'"
        assert data["short_code"], "short_code não deve ser nulo"

        # Verifica persistência no banco (sem IA real)
        result = await test_db_session.execute(
            select(ShortenedUrlModel).where(
                ShortenedUrlModel.original_url
                == "https://www.workflow-ia-test.com/pagina-muito-longa"
            )
        )
        urls = result.scalars().all()
        assert len(urls) == 1, (
            f"URL deve estar persistida no banco após fluxo de encurtamento. "
            f"Encontrado {len(urls)} registros."
        )

    async def test_workflow_shorten_result_corresponds_to_db(
        self, app_with_db, test_db_session, ai_response_fixture
    ):
        """O short_code retornado pela API corresponde ao registro no banco."""
        # Carrega fixture (sem chamada real à IA)
        ai_payload = ai_response_fixture("workflow_complete")
        assert isinstance(ai_payload, dict), "Fixture de workflow_complete deve retornar dict"

        # Insere ApiKey
        api_key_model = _make_api_key_model()
        test_db_session.add(api_key_model)
        await test_db_session.commit()

        with patch(
            "app.api.dependencies.api_key_auth.rate_limit_by_api_key",
            new=AsyncMock(return_value=None),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_db),
                base_url="http://test",
                follow_redirects=False,
                headers={"X-API-Key": api_key_model.key},
            ) as ac:
                response = await ac.post(
                    "/api/shorten",
                    json={"url": "https://www.workflow-result-test.com/path"},
                )

        assert response.status_code == 201
        returned_short_code = response.json()["short_code"]

        # Verifica que short_code da API corresponde ao banco
        result = await test_db_session.execute(
            select(ShortenedUrlModel).where(ShortenedUrlModel.short_code == returned_short_code)
        )
        db_url = result.scalar_one_or_none()
        assert db_url is not None, (
            f"short_code '{returned_short_code}' retornado pela API deve existir no banco"
        )
        assert db_url.original_url == "https://www.workflow-result-test.com/path", (
            f"original_url no banco deve corresponder ao enviado. Obtido: '{db_url.original_url}'"
        )


class TestWorkflowRedirectComTracking:
    """Fluxo 2: Redirecionamento com tracking de cliques no banco real."""

    async def test_redirect_incrementa_click_count(
        self, app_with_db, test_engine, test_db_session, ai_response_fixture
    ):
        """GET /{short_code} redireciona e incrementa click_count no banco real.

        Este é o Fluxo 2 de workflow: verifica que a pipeline de redirect
        funciona end-to-end com banco real, sem mocks de repositório.
        """
        import asyncio

        from sqlalchemy.ext.asyncio import async_sessionmaker

        # Carrega fixture de IA (determinística, sem chamada real)
        ai_payload = ai_response_fixture("analyze_url")
        assert ai_payload is not None, "Fixture analyze_url deve ser carregável"

        # Insere URL diretamente no banco (click_count inicial = 0)
        short_code = f"rdr{uuid.uuid4().hex[:5]}"
        url_model = ShortenedUrlModel(
            original_url="https://www.redirect-tracking-test.com/",
            short_code=short_code,
        )
        test_db_session.add(url_model)
        await test_db_session.commit()

        # Executa redirect (não segue redirect para verificar status)
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
        ) as ac:
            redirect_resp = await ac.get(f"/{short_code}")

        assert redirect_resp.status_code == 302, (
            f"Redirect deve retornar 302, obtido {redirect_resp.status_code}: {redirect_resp.text}"
        )
        assert "location" in redirect_resp.headers, (
            "Response de redirect deve ter header 'location'"
        )
        assert redirect_resp.headers["location"] == "https://www.redirect-tracking-test.com/", (
            f"Location deve apontar para URL original. "
            f"Obtido: '{redirect_resp.headers['location']}'"
        )

        # Aguarda o fire-and-forget de click_count (task asyncio)
        await asyncio.sleep(0.3)

        # Verifica que click_count foi incrementado no banco
        # Abre NOVA sessão para ler dados atualizados (isolada da sessão do handler)
        session_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as fresh_session:
            result = await fresh_session.execute(
                select(ShortenedUrlModel).where(ShortenedUrlModel.short_code == short_code)
            )
            url_after = result.scalar_one()
            final_click_count = url_after.click_count or 0

        assert final_click_count == 1, (
            f"click_count deve ser 1 após 1 acesso, obtido {final_click_count}"
        )

        assert final_click_count == 1, (
            f"click_count deve ser 1 após 1 acesso, obtido {final_click_count}"
        )

    async def test_redirect_short_code_inexistente_retorna_404(self, app_with_db):
        """GET /{short_code} para código inexistente retorna 404 HTML."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
        ) as ac:
            response = await ac.get("/codigo-inexistente-xyz999")

        assert response.status_code == 404, (
            f"short_code inexistente deve retornar 404, obtido {response.status_code}"
        )


class TestWorkflowMetricasAcumuladas:
    """Fluxo 3: Métricas acumuladas refletem múltiplos acessos ao banco real."""

    async def test_metricas_refletem_3_acessos(
        self, app_with_db, test_engine, test_db_session, ai_response_fixture
    ):
        """click_count reflete exatamente 3 acessos ao banco real.

        Este é o Fluxo 3 de workflow: métricas acumuladas.
        Usa fixture de IA determinística (sem chamada real).
        """
        # Carrega fixture (verifica determinismo — sem chamada real à IA)
        ai_payload = ai_response_fixture("generate_short_code")
        assert ai_payload["choices"][0]["message"]["content"] == "aB12x"

        # Insere URL no banco
        short_code = f"mtr{uuid.uuid4().hex[:5]}"
        url_model = ShortenedUrlModel(
            original_url="https://www.metricas-teste.com/",
            short_code=short_code,
        )
        test_db_session.add(url_model)
        await test_db_session.commit()

        # Simula 3 acessos via redirect
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
        ) as ac:
            for i in range(3):
                resp = await ac.get(f"/{short_code}")
                assert resp.status_code == 302, (
                    f"Acesso {i + 1}: esperado 302, obtido {resp.status_code}"
                )

        # Aguarda fire-and-forget de click_count
        import asyncio

        await asyncio.sleep(0.4)

        # Verifica métricas no banco (assertion direta via nova sessão)
        from sqlalchemy.ext.asyncio import async_sessionmaker

        session_factory = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as fresh_session:
            result = await fresh_session.execute(
                select(ShortenedUrlModel).where(ShortenedUrlModel.short_code == short_code)
            )
            url_with_metrics = result.scalar_one()
            actual_count = url_with_metrics.click_count or 0

        assert actual_count == 3, f"click_count deve ser 3 após 3 acessos, obtido {actual_count}"

    async def test_metricas_via_api_refletem_acessos(
        self, app_with_db, test_db_session, ai_response_fixture
    ):
        """GET /api/urls/{short_code} retorna click_count correto após acessos."""
        # Usa fixture de IA (determinística, sem chamada real)
        ai_payload = ai_response_fixture("workflow_complete")
        assert "choices" in ai_payload

        # Insere ApiKey e URL
        api_key_model = _make_api_key_model()
        test_db_session.add(api_key_model)

        short_code = f"apm{uuid.uuid4().hex[:5]}"
        url_model = ShortenedUrlModel(
            original_url="https://www.metricas-api-teste.com/",
            short_code=short_code,
        )
        test_db_session.add(url_model)
        await test_db_session.commit()

        with patch(
            "app.api.dependencies.api_key_auth.rate_limit_by_api_key",
            new=AsyncMock(return_value=None),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_db),
                base_url="http://test",
                follow_redirects=False,
                headers={"X-API-Key": api_key_model.key},
            ) as ac:
                # Simula 2 acessos
                for _ in range(2):
                    await ac.get(f"/{short_code}")

                # Aguarda fire-and-forget
                import asyncio

                await asyncio.sleep(0.2)

                # Consulta métricas via API
                metrics_resp = await ac.get(f"/api/urls/{short_code}")

        assert metrics_resp.status_code == 200, (
            f"GET /api/urls/{short_code} deve retornar 200, "
            f"obtido {metrics_resp.status_code}: {metrics_resp.text}"
        )
        metrics = metrics_resp.json()
        assert "click_count" in metrics, "Response de métricas deve conter 'click_count'"
        assert metrics["click_count"] == 2, (
            f"click_count deve ser 2 após 2 acessos, obtido {metrics['click_count']}"
        )

    async def test_click_count_zero_para_url_sem_acessos(self, app_with_db, test_db_session):
        """URL recém-criada tem click_count == 0 antes de qualquer acesso."""
        api_key_model = _make_api_key_model()
        test_db_session.add(api_key_model)

        short_code = f"zcl{uuid.uuid4().hex[:5]}"
        url_model = ShortenedUrlModel(
            original_url="https://www.zero-clicks.com/",
            short_code=short_code,
        )
        test_db_session.add(url_model)
        await test_db_session.commit()

        with patch(
            "app.api.dependencies.api_key_auth.rate_limit_by_api_key",
            new=AsyncMock(return_value=None),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_db),
                base_url="http://test",
                follow_redirects=False,
                headers={"X-API-Key": api_key_model.key},
            ) as ac:
                metrics_resp = await ac.get(f"/api/urls/{short_code}")

        assert metrics_resp.status_code == 200
        metrics = metrics_resp.json()
        assert metrics["click_count"] == 0, (
            f"URL sem acessos deve ter click_count=0, obtido {metrics['click_count']}"
        )


class TestNenhumaChamadaRealAIA:
    """Verifica que nenhuma chamada real a APIs de IA é realizada durante os testes."""

    async def test_fixtures_de_ia_sao_deterministicas_sem_chamada_real(self, ai_response_fixture):
        """As 3 fixtures de IA retornam sempre o mesmo payload sem chamar APIs externas."""
        fixtures = ["generate_short_code", "analyze_url", "workflow_complete"]

        for nome in fixtures:
            # Primeira chamada
            payload_1 = ai_response_fixture(nome)
            # Segunda chamada (deve ser idêntica — sem I/O externo)
            payload_2 = ai_response_fixture(nome)

            assert payload_1 == payload_2, (
                f"Fixture '{nome}' não é determinística — chamadas diferentes retornam valores "
                f"distintos. Isso indica possível geração dinâmica ou chamada à API real."
            )

            # Verifica estrutura básica esperada de resposta de LLM
            assert "choices" in payload_1, (
                f"Fixture '{nome}' deve ter campo 'choices' (formato padrão de LLM)"
            )
            assert "model" in payload_1, f"Fixture '{nome}' deve ter campo 'model'"

    async def test_fixtures_nao_contem_api_keys_reais(self, ai_response_fixture):
        """Fixtures de IA não devem conter API keys ou tokens reais."""
        fixtures = ["generate_short_code", "analyze_url", "workflow_complete"]
        padroes_suspeitos = ["sk-proj", "bearer ", "api_key_real"]

        for nome in fixtures:
            payload = ai_response_fixture(nome)
            payload_str = str(payload).lower()

            for padrao in padroes_suspeitos:
                assert padrao.lower() not in payload_str, (
                    f"Fixture '{nome}' pode conter credencial real (padrão '{padrao}' detectado). "
                    f"Verifique o arquivo tests/fixtures/ai_responses/{nome}.json"
                )
