"""Testes E2E — Fluxo Encurtar → Redirecionar.

Verifica o ciclo completo: encurtar uma URL e em seguida redirecionar pelo
short_code gerado. Testa o comportamento end-to-end do sistema sem mocks.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
class TestEncurtarRedirecionarFluxo:
    """Fluxo E2E: encurtar uma URL e redirecionar pelo short_code."""

    async def test_encurtar_url_e_redirecionar(
        self, e2e_authenticated_client: tuple[AsyncClient, str]
    ):
        """Fluxo completo: encurtar URL → redirecionar → verificar destino."""
        client, _ = e2e_authenticated_client
        url_original = "https://www.exemplo.com.br/pagina/produto"

        # 1. Encurtar
        resp_shorten = await client.post(
            "/api/shorten",
            json={"url": url_original},
        )
        assert resp_shorten.status_code == 201, (
            f"Esperado 201, obtido {resp_shorten.status_code}: {resp_shorten.text}"
        )
        data = resp_shorten.json()
        assert "short_code" in data, "Resposta deve conter 'short_code'"
        short_code = data["short_code"]
        assert len(short_code) > 0

        # 2. Redirecionar
        resp_redirect = await client.get(f"/{short_code}")
        assert resp_redirect.status_code == 302, f"Esperado 302, obtido {resp_redirect.status_code}"
        assert resp_redirect.headers.get("location") == url_original

    async def test_encurtar_multiplas_urls_short_codes_distintos(
        self, e2e_authenticated_client: tuple[AsyncClient, str]
    ):
        """Múltiplas URLs encurtadas geram short_codes distintos."""
        client, _ = e2e_authenticated_client
        urls = [
            "https://www.site-a.com/pagina1",
            "https://www.site-b.org/recurso",
            "https://www.site-c.net/path/to/page",
        ]

        short_codes = []
        for url in urls:
            resp = await client.post("/api/shorten", json={"url": url})
            assert resp.status_code == 201
            code = resp.json()["short_code"]
            short_codes.append(code)

        # Todos os short_codes devem ser únicos
        assert len(short_codes) == len(set(short_codes)), (
            "short_codes devem ser únicos para URLs diferentes"
        )

    async def test_redirecionar_short_code_inexistente_retorna_404(self, e2e_client: AsyncClient):
        """Redirecionar short_code inexistente retorna 404 com página de erro."""
        resp = await e2e_client.get("/codigo-que-nao-existe-e2e")
        assert resp.status_code == 404
        assert "text/html" in resp.headers.get("content-type", "")

    async def test_encurtar_sem_autenticacao_retorna_401(self, e2e_client: AsyncClient):
        """Encurtar sem API Key retorna 401."""
        resp = await e2e_client.post(
            "/api/shorten",
            json={"url": "https://www.exemplo.com"},
        )
        assert resp.status_code == 401

    async def test_health_check_disponivel(self, e2e_client: AsyncClient):
        """Health check responde com 200."""
        resp = await e2e_client.get("/health")
        assert resp.status_code == 200


@pytest.mark.e2e
class TestEncurtarConsultarFluxo:
    """Fluxo E2E: encurtar → redirecionar → consultar métricas de clique."""

    async def test_click_count_incrementa_apos_redirect(
        self, e2e_authenticated_client: tuple[AsyncClient, str]
    ):
        """Cada redirect incrementa o click_count da URL."""
        client, _ = e2e_authenticated_client
        url_original = "https://www.metricas-e2e.com/pagina"

        # Encurtar
        resp_shorten = await client.post("/api/shorten", json={"url": url_original})
        assert resp_shorten.status_code == 201
        short_code = resp_shorten.json()["short_code"]

        # Verificar click_count inicial = 0
        resp_details_antes = await client.get(f"/api/urls/{short_code}")
        assert resp_details_antes.status_code == 200
        click_count_antes = resp_details_antes.json().get("click_count", 0)
        assert click_count_antes == 0

        # Executar redirect (incrementa clique)
        await client.get(f"/{short_code}")

        # Verificar click_count = 1
        resp_details_depois = await client.get(f"/api/urls/{short_code}")
        assert resp_details_depois.status_code == 200
        click_count_depois = resp_details_depois.json().get("click_count", 0)
        assert click_count_depois == 1

    async def test_consultar_url_details_retorna_url_original(
        self, e2e_authenticated_client: tuple[AsyncClient, str]
    ):
        """Consultar detalhes retorna a URL original encurtada."""
        client, _ = e2e_authenticated_client
        url_original = "https://www.consulta-e2e.com/detalhe"

        resp_shorten = await client.post("/api/shorten", json={"url": url_original})
        assert resp_shorten.status_code == 201
        short_code = resp_shorten.json()["short_code"]

        resp_details = await client.get(f"/api/urls/{short_code}")
        assert resp_details.status_code == 200
        data = resp_details.json()
        assert data.get("original_url") == url_original or data.get("url") == url_original

    async def test_consultar_url_inexistente_retorna_404(
        self, e2e_authenticated_client: tuple[AsyncClient, str]
    ):
        """Consultar short_code inexistente retorna 404."""
        client, _ = e2e_authenticated_client
        resp = await client.get("/api/urls/codigo-inexistente-e2e")
        assert resp.status_code == 404


@pytest.mark.e2e
class TestListagemLinksFluxo:
    """Fluxo E2E: encurtar múltiplas URLs e listar via cookie de sessão."""

    async def test_encurtar_e_listar_links_da_sessao(
        self, e2e_authenticated_client: tuple[AsyncClient, str]
    ):
        """Após encurtar URLs, /api/links retorna lista com os links da sessão.

        A resposta do endpoint é no formato {"links": [...]} ou lista direta.
        """
        client, _ = e2e_authenticated_client
        urls = [
            "https://www.lista-e2e-a.com",
            "https://www.lista-e2e-b.com",
        ]

        # Encurtar URLs (o servidor seta cookie de sessão)
        session_cookie = None
        for url in urls:
            resp = await client.post("/api/shorten", json={"url": url})
            assert resp.status_code == 201
            if "session_id" in resp.cookies:
                session_cookie = resp.cookies["session_id"]

        # Listar links da sessão (se cookie foi setado)
        if session_cookie:
            resp_links = await client.get(
                "/api/links",
                cookies={"session_id": session_cookie},
            )
            assert resp_links.status_code == 200
            data = resp_links.json()
            # Suporta tanto {"links": [...]} quanto lista direta
            links = data.get("links", data) if isinstance(data, dict) else data
            assert isinstance(links, list), f"Esperado lista, obtido: {type(data)}"
            assert len(links) >= 1, "Esperado ao menos 1 link na sessão"

    async def test_listar_links_sem_sessao_retorna_lista_vazia(self, e2e_client: AsyncClient):
        """Listar links sem cookie de sessão retorna lista vazia."""
        resp = await e2e_client.get("/api/links")
        assert resp.status_code == 200
        data = resp.json()
        # Suporta tanto {"links": [...]} quanto lista direta
        links = data.get("links", data) if isinstance(data, dict) else data
        assert isinstance(links, list), f"Esperado lista, obtido: {type(data)}"
        assert len(links) == 0
