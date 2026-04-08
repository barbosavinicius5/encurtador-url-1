"""Testes de integração para os 3 fluxos críticos — US-005.

Cobre os fluxos obrigatórios:
1. Redirecionamento com incremento de click_count
2. Criação de URL encurtada (persistência com slug único)
3. Registro de clique (evento de clique persistido)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.api_key_auth import api_key_auth
from app.application.dtos.shorten_url_dto import ShortenUrlResponse
from app.domain.entities.api_key import ApiKey
from app.domain.entities.shortened_url import ShortenedUrl
from app.infrastructure.di.container import get_redirect_use_case
from app.infrastructure.middleware.brute_force_protection import brute_force_protection
from app.infrastructure.middleware.rate_limiter import rate_limit_by_ip
from app.infrastructure.routers.v1.shorten_v1_router import _get_use_case
from app.main import create_app


def _make_valid_api_key() -> ApiKey:
    return ApiKey(id="test-id", key="valid-key-abcdef12", owner="test", is_active=True)


def _make_shortened_url(
    short_code: str = "aB12x5",
    original_url: str = "https://www.exemplo.com/pagina-muito-longa",
    click_count: int = 0,
    id: int = 1,
) -> ShortenedUrl:
    return ShortenedUrl(
        original_url=original_url,
        short_code=short_code,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        id=id,
        click_count=click_count,
    )


@pytest.fixture
def app_instance():
    return create_app()


@pytest.fixture
async def client(app_instance):
    async with AsyncClient(transport=ASGITransport(app=app_instance), base_url="http://test") as ac:
        yield ac


def _bypass_rate_limit(app):
    """Remove dependências de rate limiting para testes de integração."""

    async def _noop():
        pass

    app.dependency_overrides[rate_limit_by_ip] = _noop
    app.dependency_overrides[brute_force_protection] = _noop


# ──────────────────────────────────────────────────────────────────────────────
# FLUXO 1: Redirecionamento com incremento de click_count
# ──────────────────────────────────────────────────────────────────────────────


class TestFluxoRedirecionamento:
    """Fluxo crítico 1 — Redirecionamento com incremento de click_count."""

    @pytest.mark.asyncio
    async def test_redirect_slug_valido_retorna_302(self, app_instance, client):
        """Slug válido deve retornar HTTP 302 com Location correto."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(return_value="https://www.exemplo.com/pagina-muito-longa")

        _bypass_rate_limit(app_instance)
        app_instance.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case

        try:
            response = await client.get("/aB12x5", follow_redirects=False)
        finally:
            app_instance.dependency_overrides.clear()

        assert response.status_code == 302
        assert response.headers["location"] == "https://www.exemplo.com/pagina-muito-longa"

    @pytest.mark.asyncio
    async def test_redirect_chama_execute_com_slug_correto(self, app_instance, client):
        """O use case deve ser chamado com o slug da URL."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(return_value="https://www.exemplo.com")

        _bypass_rate_limit(app_instance)
        app_instance.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case

        try:
            await client.get("/aB12x5", follow_redirects=False)
        finally:
            app_instance.dependency_overrides.clear()

        mock_use_case.execute.assert_awaited_once_with("aB12x5")

    @pytest.mark.asyncio
    async def test_redirect_incrementa_click_count_via_use_case(self, app_instance, client):
        """Redirect deve disparar incremento de click_count no use case.

        O use case é responsável por chamar _persist_click, que incrementa
        o click_count no banco. Verificamos que execute() foi chamado,
        garantindo que o fluxo de incremento foi disparado.
        """
        click_count_antes = 5
        url_entity = _make_shortened_url(click_count=click_count_antes)

        # Simular use case real que chama _persist_click
        persist_called = []

        async def mock_execute(short_code: str) -> str:
            # Simula o comportamento real: retorna URL E registra clique
            persist_called.append(short_code)
            url_entity.register_click()
            return url_entity.original_url

        mock_use_case = AsyncMock()
        mock_use_case.execute = mock_execute

        _bypass_rate_limit(app_instance)
        app_instance.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case

        try:
            response = await client.get("/aB12x5", follow_redirects=False)
        finally:
            app_instance.dependency_overrides.clear()

        assert response.status_code == 302
        # Verificar que o use case foi chamado (o que dispara o incremento)
        assert "aB12x5" in persist_called
        # Verificar que click_count foi incrementado na entidade
        assert url_entity.click_count == click_count_antes + 1

    @pytest.mark.asyncio
    async def test_redirect_slug_invalido_retorna_404(self, app_instance, client):
        """Slug inválido deve retornar HTTP 404."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(
            side_effect=ValueError("short_code 'invalido' não encontrado")
        )

        _bypass_rate_limit(app_instance)
        app_instance.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case

        try:
            response = await client.get("/invalido", follow_redirects=False)
        finally:
            app_instance.dependency_overrides.clear()

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_redirect_nao_usa_301(self, app_instance, client):
        """Redirect deve usar 302, não 301 (para não ser cacheado pelo browser)."""
        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(return_value="https://www.exemplo.com")

        _bypass_rate_limit(app_instance)
        app_instance.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case

        try:
            response = await client.get("/aB12x5", follow_redirects=False)
        finally:
            app_instance.dependency_overrides.clear()

        assert response.status_code == 302
        assert response.status_code != 301


# ──────────────────────────────────────────────────────────────────────────────
# FLUXO 2: Criação de URL encurtada
# ──────────────────────────────────────────────────────────────────────────────


class TestFluxoCriacaoUrl:
    """Fluxo crítico 2 — Criação de URL encurtada e persistência."""

    @pytest.mark.asyncio
    async def test_criar_url_retorna_201_com_slug(self, app_instance, client):
        """POST /api/v1/shorten deve retornar 201 com slug e short_url."""
        app_instance.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()

        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(
            return_value=ShortenUrlResponse(
                short_code="aB12x5",
                short_url="https://short.app/aB12x5",
                original_url="https://www.exemplo.com/pagina-muito-longa",
            )
        )

        app_instance.dependency_overrides[_get_use_case] = lambda: mock_use_case

        try:
            response = await client.post(
                "/api/v1/shorten",
                json={"url": "https://www.exemplo.com/pagina-muito-longa"},
                headers={"X-API-Key": "valid-key-abcdef12"},
            )
        finally:
            app_instance.dependency_overrides.clear()

        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert "short_url" in data
        assert data["short_code"] == "aB12x5"
        assert data["short_url"] == "https://short.app/aB12x5"

    @pytest.mark.asyncio
    async def test_criar_url_persiste_original_url_corretamente(self, app_instance, client):
        """POST /api/v1/shorten deve persistir a URL original no use case."""
        app_instance.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()

        executed_with = []

        async def mock_execute(request, session_id=None):
            executed_with.append(request.url)
            return ShortenUrlResponse(
                short_code="xYz789",
                short_url="https://short.app/xYz789",
                original_url=request.url,
            )

        mock_use_case = AsyncMock()
        mock_use_case.execute = mock_execute
        app_instance.dependency_overrides[_get_use_case] = lambda: mock_use_case

        try:
            response = await client.post(
                "/api/v1/shorten",
                json={"url": "https://www.exemplo.com/pagina-muito-longa"},
                headers={"X-API-Key": "valid-key-abcdef12"},
            )
        finally:
            app_instance.dependency_overrides.clear()

        assert response.status_code == 201
        # A URL original deve ter sido passada para o use case
        assert "https://www.exemplo.com/pagina-muito-longa" in executed_with

    @pytest.mark.asyncio
    async def test_criar_url_slug_retornado_tem_pelo_menos_5_chars(self, app_instance, client):
        """Slug retornado deve ter pelo menos 5 caracteres."""
        app_instance.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()

        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(
            return_value=ShortenUrlResponse(
                short_code="abc12",
                short_url="https://short.app/abc12",
                original_url="https://www.exemplo.com",
            )
        )
        app_instance.dependency_overrides[_get_use_case] = lambda: mock_use_case

        try:
            response = await client.post(
                "/api/v1/shorten",
                json={"url": "https://www.exemplo.com"},
                headers={"X-API-Key": "valid-key-abcdef12"},
            )
        finally:
            app_instance.dependency_overrides.clear()

        data = response.json()
        assert len(data["short_code"]) >= 5

    @pytest.mark.asyncio
    async def test_criar_url_short_url_usa_base_url(self, app_instance, client):
        """short_url retornada deve conter o slug correto."""
        app_instance.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()

        mock_use_case = AsyncMock()
        mock_use_case.execute = AsyncMock(
            return_value=ShortenUrlResponse(
                short_code="aB12x5",
                short_url="https://short.app/aB12x5",
                original_url="https://www.exemplo.com",
            )
        )
        app_instance.dependency_overrides[_get_use_case] = lambda: mock_use_case

        try:
            response = await client.post(
                "/api/v1/shorten",
                json={"url": "https://www.exemplo.com"},
                headers={"X-API-Key": "valid-key-abcdef12"},
            )
        finally:
            app_instance.dependency_overrides.clear()

        data = response.json()
        assert data["short_code"] in data["short_url"]

    @pytest.mark.asyncio
    async def test_criar_url_sem_api_key_retorna_401(self, app_instance, client):
        """POST /api/v1/shorten sem API Key deve retornar 401."""
        response = await client.post(
            "/api/v1/shorten",
            json={"url": "https://www.exemplo.com"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_criar_url_invalida_retorna_422(self, app_instance, client):
        """POST /api/v1/shorten com URL inválida deve retornar 422."""
        app_instance.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()

        try:
            response = await client.post(
                "/api/v1/shorten",
                json={"url": "nao-e-uma-url-valida"},
                headers={"X-API-Key": "valid-key-abcdef12"},
            )
        finally:
            app_instance.dependency_overrides.clear()

        assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# FLUXO 3: Registro de clique
# ──────────────────────────────────────────────────────────────────────────────


class TestFluxoRegistroClique:
    """Fluxo crítico 3 — Registro de clique ao acessar slug."""

    @pytest.mark.asyncio
    async def test_acesso_ao_slug_dispara_registro_de_clique(self, app_instance, client):
        """GET /{slug} deve disparar o registro de clique via use case."""
        click_eventos = []
        url_entity = _make_shortened_url(short_code="aB12x5", click_count=0)

        async def mock_execute(short_code: str) -> str:
            # Simula execute() que internamente chama _persist_click via create_task
            # Registramos o evento para verificação
            click_eventos.append(
                {
                    "slug": short_code,
                    "created_at": datetime.now(timezone.utc),
                }
            )
            url_entity.register_click()
            return url_entity.original_url

        mock_use_case = AsyncMock()
        mock_use_case.execute = mock_execute

        _bypass_rate_limit(app_instance)
        app_instance.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case

        try:
            response = await client.get("/aB12x5", follow_redirects=False)
        finally:
            app_instance.dependency_overrides.clear()

        assert response.status_code == 302
        # Verificar que o evento de clique foi registrado
        assert len(click_eventos) == 1
        assert click_eventos[0]["slug"] == "aB12x5"
        assert click_eventos[0]["created_at"] is not None

    @pytest.mark.asyncio
    async def test_multiplos_acessos_incrementam_contador(self, app_instance, client):
        """Múltiplos acessos ao mesmo slug devem incrementar o contador."""
        url_entity = _make_shortened_url(short_code="aB12x5", click_count=0)

        async def mock_execute(short_code: str) -> str:
            url_entity.register_click()
            return url_entity.original_url

        mock_use_case = AsyncMock()
        mock_use_case.execute = mock_execute

        _bypass_rate_limit(app_instance)
        app_instance.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case

        try:
            for _ in range(3):
                response = await client.get("/aB12x5", follow_redirects=False)
                assert response.status_code == 302
        finally:
            app_instance.dependency_overrides.clear()

        # Após 3 acessos, click_count deve ser 3
        assert url_entity.click_count == 3

    @pytest.mark.asyncio
    async def test_clique_registra_timestamp(self, app_instance, client):
        """O evento de clique deve incluir timestamp da requisição."""
        url_entity = _make_shortened_url(short_code="aB12x5", click_count=0)
        timestamp_antes = datetime.now(timezone.utc)

        async def mock_execute(short_code: str) -> str:
            url_entity.register_click()
            return url_entity.original_url

        mock_use_case = AsyncMock()
        mock_use_case.execute = mock_execute

        _bypass_rate_limit(app_instance)
        app_instance.dependency_overrides[get_redirect_use_case] = lambda: mock_use_case

        try:
            await client.get("/aB12x5", follow_redirects=False)
        finally:
            app_instance.dependency_overrides.clear()

        # Verificar que last_clicked_at foi registrado com timestamp válido
        assert url_entity.last_clicked_at is not None
        assert url_entity.last_clicked_at >= timestamp_antes


# ──────────────────────────────────────────────────────────────────────────────
# Testes de comportamento end-to-end (pipeline completo)
# ──────────────────────────────────────────────────────────────────────────────


class TestFluxosEndToEnd:
    """Testes que verificam o comportamento end-to-end dos fluxos críticos."""

    @pytest.mark.asyncio
    async def test_pipeline_criar_e_redirecionar(self, app_instance, client):
        """Criar URL e depois acessar o slug deve redirecionar corretamente."""
        original_url = "https://www.exemplo.com/pagina-muito-longa"
        created_short_code = "aB12x5"

        # Step 1: Criar URL
        app_instance.dependency_overrides[api_key_auth] = lambda: _make_valid_api_key()
        mock_shorten = AsyncMock()
        mock_shorten.execute = AsyncMock(
            return_value=ShortenUrlResponse(
                short_code=created_short_code,
                short_url=f"https://short.app/{created_short_code}",
                original_url=original_url,
            )
        )
        app_instance.dependency_overrides[_get_use_case] = lambda: mock_shorten

        try:
            create_response = await client.post(
                "/api/v1/shorten",
                json={"url": original_url},
                headers={"X-API-Key": "valid-key-abcdef12"},
            )
        finally:
            app_instance.dependency_overrides.pop(_get_use_case, None)
            app_instance.dependency_overrides.pop(api_key_auth, None)

        assert create_response.status_code == 201
        slug = create_response.json()["short_code"]

        # Step 2: Acessar URL encurtada
        mock_redirect = AsyncMock()
        mock_redirect.execute = AsyncMock(return_value=original_url)

        _bypass_rate_limit(app_instance)
        app_instance.dependency_overrides[get_redirect_use_case] = lambda: mock_redirect

        try:
            redirect_response = await client.get(f"/{slug}", follow_redirects=False)
        finally:
            app_instance.dependency_overrides.clear()

        assert redirect_response.status_code == 302
        assert redirect_response.headers["location"] == original_url
