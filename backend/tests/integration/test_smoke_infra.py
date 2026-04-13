"""Testes de smoke validando a infraestrutura de testes de integração (T001-BE).

Estes testes verificam que:
- Banco de teste é criado e descartado por função (sem vazamento de estado)
- Override de dependência redireciona para banco de teste
- Chamadas HTTP externas são bloqueadas automaticamente
- Fixture de IA retorna payload determinístico
- Fixture de IA falha com erro descritivo para arquivo inexistente
"""

import logging
import uuid

import pytest
from sqlalchemy import select

from app.infrastructure.db.models import ApiKeyModel, ShortenedUrlModel

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


class TestBancoIsoladoPorFuncao:
    """Verifica que banco de teste é criado e descartado por função."""

    async def test_insercao_no_teste1_nao_aparece_no_teste2_parte1(self, db_session):
        """Parte 1: Insere um registro no banco de teste."""
        model = ShortenedUrlModel(
            original_url="https://www.exemplo-smoke-1.com/longa",
            short_code=f"smk{uuid.uuid4().hex[:4]}",
            session_id="session-smoke-1",
        )
        db_session.add(model)
        await db_session.flush()

        result = await db_session.execute(select(ShortenedUrlModel))
        urls = result.scalars().all()
        assert len(urls) == 1, f"Esperado 1 registro, obtido {len(urls)}"

    async def test_insercao_no_teste1_nao_aparece_no_teste2_parte2(self, db_session):
        """Parte 2: Banco deve estar vazio (isolado do teste anterior)."""
        result = await db_session.execute(select(ShortenedUrlModel))
        urls = result.scalars().all()
        assert len(urls) == 0, f"Esperado 0 registros (banco isolado), obtido {len(urls)}: {urls}"

    async def test_banco_criado_com_schema_correto(self, db_session):
        """Verifica que schema foi criado corretamente no banco de teste."""
        await db_session.execute(select(ShortenedUrlModel))
        await db_session.execute(select(ApiKeyModel))
        assert True

    async def test_sessao_permite_inserir_e_ler_api_key(self, db_session):
        """ApiKey inserida diretamente no banco é encontrada na query."""
        api_key = ApiKeyModel(
            id=str(uuid.uuid4()),
            key=f"smoke-direct-{uuid.uuid4().hex[:10]}",
            owner="smoke-owner",
            is_active=True,
        )
        db_session.add(api_key)
        await db_session.commit()

        result = await db_session.execute(
            select(ApiKeyModel).where(ApiKeyModel.owner == "smoke-owner")
        )
        found = result.scalar_one_or_none()
        assert found is not None, "ApiKey deve ser encontrada após inserção direta"
        assert bool(found.is_active) is True, "ApiKey deve estar ativa"


class TestOverrideDependencia:
    """Verifica que override de dependência redireciona para banco de teste."""

    async def test_post_shorten_usa_banco_de_teste(self, client_no_rate_limit):
        """POST /api/shorten cria registro no banco de teste (não no banco real)."""
        ac, api_key_value, session = client_no_rate_limit

        response = await ac.post(
            "/api/shorten",
            json={"url": "https://www.teste-smoke-override.com/pagina-longa"},
        )

        assert response.status_code == 201, (
            f"Esperado 201, obtido {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "short_code" in data, "Response deve conter 'short_code'"
        assert data["short_code"], "short_code não deve ser nulo ou vazio"

        # Assertion direta no banco de teste (não via API)
        result = await session.execute(
            select(ShortenedUrlModel).where(
                ShortenedUrlModel.original_url
                == "https://www.teste-smoke-override.com/pagina-longa"
            )
        )
        urls = result.scalars().all()
        assert len(urls) == 1, (
            f"URL deve estar no banco de TESTE (não em produção). Encontrado {len(urls)} registros."
        )

    async def test_banco_de_teste_inicia_vazio(self, db_session):
        """Banco de teste começa vazio para cada função de teste."""
        result = await db_session.execute(select(ShortenedUrlModel))
        urls = result.scalars().all()
        assert len(urls) == 0, (
            f"Banco deve estar vazio no início do teste, obtido {len(urls)}: {urls}"
        )


class TestInterceptadoresHTTP:
    """Verifica que chamadas HTTP externas são bloqueadas."""

    async def test_fixture_block_external_disponivel(self, block_external_http):
        """Fixture block_external_http deve ser não-nula (respx instalado)."""
        assert block_external_http is not None, (
            "Fixture block_external_http deve estar disponível. "
            "Verifique se respx está instalado (pip install respx)."
        )

    async def test_chamada_github_api_e_bloqueada(self, block_external_http):
        """Chamada para api.github.com levanta ConnectionError com mensagem descritiva."""
        import httpx

        with pytest.raises((ConnectionError, Exception)) as exc_info:
            async with httpx.AsyncClient() as http_client:
                await http_client.get("https://api.github.com/repos/test/test")

        error_msg = str(exc_info.value)
        assert (
            "bloqueada" in error_msg.lower()
            or "github" in error_msg.lower()
            or exc_info.type.__name__ in ("ConnectionError", "ConnectError")
        ), f"Erro de bloqueio esperado, obtido: {error_msg}"

    async def test_chamada_jira_api_e_bloqueada(self, block_external_http):
        """Chamada para api.atlassian.com levanta ConnectionError."""
        import httpx

        with pytest.raises((ConnectionError, Exception)):
            async with httpx.AsyncClient() as http_client:
                await http_client.get("https://api.atlassian.com/jira/test")


class TestFixturasIA:
    """Verifica que fixtures de IA retornam payloads determinísticos."""

    def test_fixture_generate_short_code_retorna_dict(self, ai_response_fixture):
        """ai_response_fixture('generate_short_code') retorna dict com choices."""
        result = ai_response_fixture("generate_short_code")

        assert isinstance(result, dict), f"Esperado dict, obtido {type(result)}"
        assert "choices" in result, f"Esperado chave 'choices', obtido: {list(result.keys())}"

    def test_fixture_generate_short_code_conteudo_correto(self, ai_response_fixture):
        """Fixture generate_short_code tem o conteúdo esperado ('aB12x')."""
        result = ai_response_fixture("generate_short_code")

        content = result["choices"][0]["message"]["content"]
        assert content == "aB12x", f"Conteúdo esperado 'aB12x', obtido '{content}'"

    def test_fixture_retorna_mesmo_payload_em_chamadas_repetidas(self, ai_response_fixture):
        """Chamadas repetidas retornam exatamente o mesmo dict (determinismo)."""
        result1 = ai_response_fixture("generate_short_code")
        result2 = ai_response_fixture("generate_short_code")

        assert result1 == result2, (
            "Fixture deve ser determinística — valores diferentes detectados!"
        )

    def test_fixture_analyze_url_retorna_dict(self, ai_response_fixture):
        """ai_response_fixture('analyze_url') retorna dict válido."""
        result = ai_response_fixture("analyze_url")
        assert isinstance(result, dict), f"Esperado dict, obtido {type(result)}"
        assert "choices" in result, "Payload deve conter 'choices'"

    def test_fixture_workflow_complete_retorna_dict(self, ai_response_fixture):
        """ai_response_fixture('workflow_complete') retorna dict válido."""
        result = ai_response_fixture("workflow_complete")
        assert isinstance(result, dict), f"Esperado dict, obtido {type(result)}"
        assert "choices" in result, "Payload deve conter 'choices'"

    def test_fixture_arquivo_inexistente_lanca_file_not_found(self, ai_response_fixture):
        """FileNotFoundError com mensagem descritiva para arquivo inexistente."""
        with pytest.raises(FileNotFoundError) as exc_info:
            ai_response_fixture("arquivo_que_nao_existe_jamais")

        error_msg = str(exc_info.value)
        assert "arquivo_que_nao_existe_jamais" in error_msg, (
            f"Mensagem de erro deve conter o nome do arquivo. Obtido: {error_msg}"
        )

    def test_todas_as_tres_fixtures_existem(self, ai_response_fixture):
        """As 3 fixtures de IA obrigatórias existem e são carregáveis."""
        fixtures_requeridas = ["generate_short_code", "analyze_url", "workflow_complete"]

        for nome in fixtures_requeridas:
            payload = ai_response_fixture(nome)
            assert isinstance(payload, dict), (
                f"Fixture '{nome}' deve retornar dict, obtido {type(payload)}"
            )
