"""Testes de integração — CRUD completo de URLs e ApiKeys (T002-BE).

Cobre os Critérios de Aceite 1-3 da US-003:
- Criação, leitura e verificação de URLs encurtadas
- Assertions diretas no banco de dados (sem mocks de repositório)
- Validação de todas as camadas: router → use case → repository → SQLite em memória
"""

import logging

import pytest
from sqlalchemy import select

from app.infrastructure.db.models import ApiKeyModel, ShortenedUrlModel

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


class TestUrlCRUD:
    """CRUD completo de URLs encurtadas atravessando todas as camadas — sem mocks de repository."""

    async def test_create_url_retorna_201_com_short_code(self, client_no_rate_limit):
        """POST /api/shorten com URL válida retorna 201 e short_code não nulo."""
        ac, api_key, _ = client_no_rate_limit

        response = await ac.post(
            "/api/shorten",
            json={"url": "https://www.exemplo.com/produtos/categoria/promocao-verao-2026"},
        )

        assert response.status_code == 201, (
            f"Esperado 201, obtido {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "short_code" in data, f"Resposta deve conter 'short_code': {data}"
        assert data["short_code"], "short_code não deve ser nulo ou vazio"
        assert len(data["short_code"]) >= 5, (
            f"short_code deve ter ao menos 5 chars, obtido: {data['short_code']!r}"
        )
        assert "original_url" in data
        assert (
            data["original_url"] == "https://www.exemplo.com/produtos/categoria/promocao-verao-2026"
        )

    async def test_create_url_persiste_no_banco(self, client_no_rate_limit):
        """POST /api/shorten cria registro no banco real (assertion direta)."""
        ac, api_key, db = client_no_rate_limit

        payload_url = "https://www.banco-real-teste.com/pagina-muito-longa-para-encurtar"
        response = await ac.post(
            "/api/shorten",
            json={"url": payload_url},
        )

        assert response.status_code == 201
        short_code = response.json()["short_code"]

        # Assertion DIRETA no banco — sem chamar a API novamente
        result = await db.execute(
            select(ShortenedUrlModel).where(ShortenedUrlModel.short_code == short_code)
        )
        url_model = result.scalar_one_or_none()

        assert url_model is not None, (
            f"Registro com short_code={short_code!r} não encontrado no banco"
        )
        assert url_model.original_url == payload_url, (
            f"original_url no banco difere do enviado: {url_model.original_url!r}"
        )
        assert url_model.click_count == 0, (
            f"click_count inicial deve ser 0, obtido: {url_model.click_count}"
        )

    async def test_create_url_short_url_comeca_com_https(self, client_no_rate_limit):
        """short_url retornado pela API deve começar com https://."""
        ac, api_key, _ = client_no_rate_limit

        response = await ac.post(
            "/api/shorten",
            json={"url": "https://www.exemplo.com/path"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "short_url" in data, f"Resposta deve conter 'short_url': {data}"
        assert data["short_url"].startswith("https://"), (
            f"short_url deve começar com 'https://', obtido: {data['short_url']!r}"
        )

    async def test_list_urls_retorna_url_criada(self, client_no_rate_limit):
        """GET /api/links retorna URLs criadas na sessão."""
        ac, api_key, _ = client_no_rate_limit

        # Cria URL
        create_resp = await ac.post(
            "/api/shorten",
            json={"url": "https://www.listagem-teste.com/path"},
        )
        assert create_resp.status_code == 201

        # Verifica que aparece na listagem (usando mesmo cookie de sessão)
        list_resp = await ac.get("/api/links")
        assert list_resp.status_code == 200

        data = list_resp.json()
        assert "links" in data, f"Resposta deve conter 'links': {data.keys()}"
        links = data["links"]
        assert len(links) >= 1, f"Deve haver ao menos 1 link, obtido: {len(links)}"

    async def test_get_url_details_por_short_code(self, client_no_rate_limit):
        """GET /api/urls/{short_code} retorna detalhes completos da URL."""
        ac, api_key, db = client_no_rate_limit

        # Cria URL
        create_resp = await ac.post(
            "/api/shorten",
            json={"url": "https://www.detalhes-teste.com/pagina"},
        )
        assert create_resp.status_code == 201
        short_code = create_resp.json()["short_code"]

        # Consulta detalhes
        details_resp = await ac.get(
            f"/api/urls/{short_code}",
        )

        assert details_resp.status_code == 200, (
            f"Esperado 200, obtido {details_resp.status_code}: {details_resp.text}"
        )
        data = details_resp.json()
        assert "original_url" in data, f"Falta 'original_url': {data}"
        assert "short_code" in data, f"Falta 'short_code': {data}"
        assert "click_count" in data, f"Falta 'click_count': {data}"
        assert data["short_code"] == short_code
        assert data["original_url"] == "https://www.detalhes-teste.com/pagina"

    async def test_url_inexistente_retorna_404(self, client_no_rate_limit):
        """GET /api/urls/{short_code} para código inexistente retorna 404."""
        ac, api_key, _ = client_no_rate_limit

        response = await ac.get("/api/urls/codigo-que-nao-existe-nunca-xyz")

        assert response.status_code == 404, (
            f"Esperado 404, obtido {response.status_code}: {response.text}"
        )

    async def test_url_invalida_retorna_422(self, client_no_rate_limit):
        """POST /api/shorten com URL inválida retorna 422."""
        ac, api_key, _ = client_no_rate_limit

        response = await ac.post(
            "/api/shorten",
            json={"url": "nao-e-uma-url-valida"},
        )

        assert response.status_code == 422, (
            f"Esperado 422, obtido {response.status_code}: {response.text}"
        )

    async def test_url_sem_protocolo_retorna_422(self, client_no_rate_limit):
        """POST /api/shorten com URL sem protocolo retorna 422."""
        ac, api_key, _ = client_no_rate_limit

        response = await ac.post(
            "/api/shorten",
            json={"url": "exemplo.com/sem-protocolo"},
        )

        assert response.status_code == 422


class TestApiKeyCRUD:
    """Testes de estado de ApiKey com banco de dados real."""

    async def test_api_key_inserida_no_banco_existe(self, test_db_session):
        """ApiKey inserida via ORM é encontrada no banco de teste."""
        import uuid

        key_value = f"test-crud-key-{uuid.uuid4().hex[:8]}"
        api_key_model = ApiKeyModel(
            id=str(uuid.uuid4()),
            key=key_value,
            owner="crud-test-owner",
            is_active=True,
        )
        test_db_session.add(api_key_model)
        await test_db_session.flush()

        # Assertion direta no banco
        result = await test_db_session.execute(
            select(ApiKeyModel).where(ApiKeyModel.key == key_value)
        )
        found = result.scalar_one_or_none()

        assert found is not None, f"ApiKey {key_value!r} não encontrada no banco"
        assert found.is_active is True
        assert found.owner == "crud-test-owner"

    async def test_api_key_inativa_e_identificavel(self, test_db_session):
        """ApiKey com is_active=False é distinguível de ativa."""
        import uuid

        # Insere chave inativa
        inactive_key = ApiKeyModel(
            id=str(uuid.uuid4()),
            key=f"inactive-key-{uuid.uuid4().hex[:8]}",
            owner="inactive-owner",
            is_active=False,
        )
        # Insere chave ativa
        active_key = ApiKeyModel(
            id=str(uuid.uuid4()),
            key=f"active-key-{uuid.uuid4().hex[:8]}",
            owner="active-owner",
            is_active=True,
        )
        test_db_session.add(inactive_key)
        test_db_session.add(active_key)
        await test_db_session.flush()

        # Filtra apenas ativas
        result = await test_db_session.execute(
            select(ApiKeyModel).where(ApiKeyModel.is_active.is_(True))
        )
        active_keys = result.scalars().all()

        active_owners = [k.owner for k in active_keys]
        assert "active-owner" in active_owners, "Chave ativa deve aparecer na listagem"
        assert "inactive-owner" not in active_owners, (
            "Chave inativa NÃO deve aparecer na listagem de ativas"
        )
