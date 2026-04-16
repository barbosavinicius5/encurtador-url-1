"""Testes de integração para o endpoint POST /api/shorten."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.api_key_auth import api_key_auth
from app.domain.entities.api_key import ApiKey
from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _make_valid_api_key() -> ApiKey:
    return ApiKey(id="test-id", key="valid-key", owner="test", is_active=True)


class TestShortenEndpoint:
    """Testes de integração para o endpoint de encurtamento."""

    @pytest.mark.asyncio
    async def test_post_url_valida_retorna_201(self, app, client):
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="aB3kZ9",
                    short_url="https://short.app/aB3kZ9",
                    original_url="https://exemplo.com/pagina-longa",
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com/pagina-longa"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert "short_url" in data
        assert "original_url" in data

    @pytest.mark.asyncio
    async def test_post_url_invalida_retorna_422(self, app, client):
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": "nao-e-uma-url"},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_url_vazia_retorna_422(self, app, client):
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": ""},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_sem_protocolo_retorna_422(self, app, client):
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": "exemplo.com/pagina"},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_response_short_code_tem_minimo_5_chars(self, app, client):
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="abc12",
                    short_url="https://short.app/abc12",
                    original_url="https://exemplo.com",
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert len(data["short_code"]) >= 5

    @pytest.mark.asyncio
    async def test_response_short_url_comeca_com_https(self, app, client):
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="abc12",
                    short_url="https://short.app/abc12",
                    original_url="https://exemplo.com",
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert data["short_url"].startswith("https://")


class TestShortenEndpointUrlsNaoConvencionais:
    """Testes de integração para URLs válidas não convencionais — Cenários A, B, C."""

    @pytest.mark.asyncio
    async def test_shorten_aceita_url_com_percent_encoding_no_path(self, app, client):
        """Cenário A: URL com percent-encoding no path deve retornar 201."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        original_url = "https://exemplo.com/path%20com%20espacos"
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="aB12x",
                    short_url="https://short.app/aB12x",
                    original_url=original_url,
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": original_url},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        assert "short_url" in response.json()

    @pytest.mark.asyncio
    async def test_shorten_aceita_url_com_query_string_complexa(self, app, client):
        """Cenário B: URL com query string complexa (+ e %26) deve retornar 201."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        original_url = "https://exemplo.com/search?q=hello+world&filter=a%26b"
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="cD34y",
                    short_url="https://short.app/cD34y",
                    original_url=original_url,
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": original_url},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        assert "short_url" in response.json()

    @pytest.mark.asyncio
    async def test_shorten_aceita_url_com_fragmento(self, app, client):
        """Cenário C: URL com fragmento (#section) deve retornar 201."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        original_url = "https://exemplo.com/page#section-1"
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="eF56z",
                    short_url="https://short.app/eF56z",
                    original_url=original_url,
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": original_url},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        assert "short_url" in response.json()

    @pytest.mark.asyncio
    async def test_shorten_aceita_url_com_path_e_fragmento(self, app, client):
        """Cenário C (variante): URL com query string e fragmento deve retornar 201."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        original_url = "https://exemplo.com/page?q=1#top"
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="gH78w",
                    short_url="https://short.app/gH78w",
                    original_url=original_url,
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": original_url},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_shorten_regressao_url_simples_valida(self, app, client):
        """Regressão — Cenário 8: URL simples válida deve continuar funcionando."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        original_url = "https://www.exemplo.com/produtos/categoria/promocao-verao-2026"
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="iJ90v",
                    short_url="https://short.app/iJ90v",
                    original_url=original_url,
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": original_url},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert "short_url" in data


class TestShortenEndpointUrlsInvalidasSeguranca:
    """Testes de integração para rejeição de URLs inválidas — Cenários D, E, F."""

    @pytest.mark.asyncio
    async def test_shorten_rejeita_javascript_url(self, app, client):
        """Cenário D: URL com esquema javascript: deve retornar 422."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": "javascript:alert(1)"},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_shorten_rejeita_data_url(self, app, client):
        """Cenário D: URL com esquema data: deve retornar 422."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": "data:text/html,<script>alert(1)</script>"},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_shorten_rejeita_vbscript_url(self, app, client):
        """Cenário D: URL com esquema vbscript: deve retornar 422."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": "vbscript:msgbox(1)"},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_shorten_rejeita_ftp_url(self, app, client):
        """Cenário E: URL com esquema ftp: deve retornar 422."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": "ftp://exemplo.com/file"},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_shorten_rejeita_url_apenas_espacos(self, app, client):
        """Cenário F: URL com apenas espaços deve retornar 422."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": "   "},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422


class TestShortenEndpointMensagensDeErro:
    """Testes para mensagens de erro orientativas — Cenários C e D da spec."""

    @pytest.mark.asyncio
    async def test_campo_url_ausente_retorna_mensagem_orientativa(self, app, client):
        """Cenário C: body sem campo 'url' deve retornar 422 com mensagem orientativa."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422
        data = response.json()
        detail = str(data.get("detail", "")).lower()
        # Deve conter instrução de ação ao usuário
        assert any(
            keyword in detail
            for keyword in ["url", "obrigatório", "obrigatorio", "informe", "campo"]
        ), f"Mensagem de erro não é orientativa: {data.get('detail')}"

    @pytest.mark.asyncio
    async def test_url_invalida_retorna_mensagem_mencionando_protocolo(self, app, client):
        """Cenário D: URL sem protocolo deve retornar 422 com mensagem mencionando http/https."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": "not-a-url"},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422
        data = response.json()
        detail = str(data.get("detail", "")).lower()
        # Deve mencionar http:// ou https://
        assert "http" in detail, f"Mensagem não menciona protocolo http/https: {data.get('detail')}"

    @pytest.mark.asyncio
    async def test_javascript_url_retorna_mensagem_orientativa(self, app, client):
        """Cenário D: URL javascript: deve retornar 422 com mensagem orientativa."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": "javascript:alert(1)"},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422
        data = response.json()
        detail = str(data.get("detail", "")).lower()
        assert "http" in detail, f"Mensagem não menciona protocolo http/https: {data.get('detail')}"

    @pytest.mark.asyncio
    async def test_url_vazia_string_retorna_mensagem_orientativa(self, app, client):
        """Cenário C: URL vazia deve retornar 422 com mensagem orientativa."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        response = await client.post(
            "/api/shorten",
            json={"url": ""},
            headers={"X-API-Key": "valid-key"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 422
        data = response.json()
        detail = str(data.get("detail", ""))
        # Mensagem deve ter conteúdo orientativo (não vazia)
        assert len(detail) > 10, f"Mensagem de erro muito curta ou vazia: '{detail}'"


class TestShortenEndpointSanitizacao:
    """Testes para sanitização da resposta — Cenário E da spec."""

    @pytest.mark.asyncio
    async def test_resposta_short_url_nao_contem_tags_html(self, app, client):
        """Cenário E: campo short_url na resposta não deve conter tags HTML."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="aB12x",
                    short_url="https://short.app/aB12x",
                    original_url="https://exemplo.com",
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        # Campos não devem conter tags HTML
        assert "<" not in data["short_url"], "short_url contém tag HTML"
        assert ">" not in data["short_url"], "short_url contém tag HTML"
        assert "<" not in data["original_url"], "original_url contém tag HTML"
        assert ">" not in data["original_url"], "original_url contém tag HTML"

    @pytest.mark.asyncio
    async def test_resposta_original_url_nao_contem_tags_html(self, app, client):
        """Cenário E: campo original_url na resposta não deve conter tags HTML."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        original_url = "https://exemplo.com/path?q=test&filter=value"
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="cD34y",
                    short_url="https://short.app/cD34y",
                    original_url=original_url,
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": original_url},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert "<" not in data["original_url"]
        assert ">" not in data["original_url"]

    @pytest.mark.asyncio
    async def test_resposta_contem_short_url_e_original_url(self, app, client):
        """Cenário E: resposta de sucesso deve conter campos short_url e original_url."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                return_value=MagicMock(
                    short_code="eF56z",
                    short_url="https://short.app/eF56z",
                    original_url="https://exemplo.com",
                )
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert "short_url" in data
        assert "original_url" in data
        # Valores devem ser strings simples
        assert isinstance(data["short_url"], str)
        assert isinstance(data["original_url"], str)


class TestShortenEndpointErroInterno:
    """Testes para erro interno 500 — Cenário F da spec."""

    @pytest.mark.asyncio
    async def test_excecao_generica_retorna_500(self, app, client):
        """Cenário F: exceção genérica no use case deve retornar 500."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(side_effect=Exception("Erro inesperado"))
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_erro_500_nao_expoe_stack_trace(self, app, client):
        """Cenário F: resposta 500 não deve conter stack trace ou informações internas."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(
                side_effect=Exception("Erro de banco de dados interno")
            )
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 500
        data = response.json()
        detail = str(data.get("detail", "")).lower()
        # Não deve conter termos que indiquem stack trace ou internos
        assert "traceback" not in detail
        assert "exception" not in detail
        assert "erro de banco" not in detail
        assert "interno" in detail or "tente novamente" in detail or "instantes" in detail

    @pytest.mark.asyncio
    async def test_erro_500_retorna_mensagem_generica_orientativa(self, app, client):
        """Cenário F: resposta 500 deve ter mensagem genérica que orienta o usuário."""
        app.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        with patch("app.infrastructure.di.container.get_shorten_use_case") as mock_dep:
            mock_use_case = AsyncMock()
            mock_use_case.execute = AsyncMock(side_effect=RuntimeError("Colisão de short_code"))
            mock_dep.return_value = mock_use_case

            response = await client.post(
                "/api/shorten",
                json={"url": "https://exemplo.com"},
                headers={"X-API-Key": "valid-key"},
            )
        app.dependency_overrides.clear()

        assert response.status_code == 500
        data = response.json()
        detail = data.get("detail", "")
        # Mensagem deve ser genérica e orientar o usuário
        assert len(detail) > 10, "Mensagem de erro muito curta"
        assert "Colisão" not in detail, "Mensagem expõe detalhe interno"
        assert "short_code" not in detail, "Mensagem expõe detalhe interno"
