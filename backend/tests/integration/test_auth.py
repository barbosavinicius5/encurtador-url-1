"""Testes de integração — Autenticação e Autorização com banco real (T002-BE).

Cobre Critério de Aceite 3 da US-003:
- Ao menos 2 cenários: acesso permitido com ApiKey válida e acesso negado com ApiKey inválida/ausente
- Todos os cenários usam banco SQLite em memória — sem mocks de repositório
- Assertions verificam tanto o status HTTP quanto que nenhum dado sensível é exposto

REGRA DE SEGURANÇA: Body de erro não deve conter stack trace, informações de banco ou dados internos.
"""

import logging
import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.infrastructure.db.models import ApiKeyModel, ShortenedUrlModel

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio


class TestAutenticacaoComBancoReal:
    """Testes de autenticação e autorização usando banco de dados real (SQLite em memória)."""

    async def test_acesso_permitido_com_api_key_valida(self, app_with_db, test_db_session):
        """ApiKey válida inserida no banco real concede acesso — retorna 201."""
        # Insere ApiKey válida diretamente no banco de teste
        api_key_value = f"valid-key-auth-test-{uuid.uuid4().hex[:12]}"
        api_key_model = ApiKeyModel(
            id=str(uuid.uuid4()),
            key=api_key_value,
            owner="auth-test-owner",
            is_active=True,
        )
        test_db_session.add(api_key_model)
        await test_db_session.commit()

        # Faz requisição autenticada com rate limiter bypassed
        with patch(
            "app.api.dependencies.api_key_auth.rate_limit_by_api_key",
            new=__import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock(return_value=None),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_db),
                base_url="http://test",
                follow_redirects=False,
                headers={"X-API-Key": api_key_value},
            ) as ac:
                response = await ac.post(
                    "/api/shorten",
                    json={"url": "https://www.auth-test-valid.com/pagina"},
                )

        assert response.status_code == 201, (
            f"ApiKey válida deve conceder acesso (201), obtido {response.status_code}: "
            f"{response.text}"
        )
        data = response.json()
        assert "short_code" in data, "Response deve conter 'short_code'"

        # Verificação dupla: URL foi salva no banco
        result = await test_db_session.execute(
            select(ShortenedUrlModel).where(
                ShortenedUrlModel.original_url == "https://www.auth-test-valid.com/pagina"
            )
        )
        urls = result.scalars().all()
        assert len(urls) == 1, (
            f"URL deve ter sido salva no banco após autenticação válida. "
            f"Encontrado {len(urls)} registros."
        )

    async def test_acesso_negado_sem_api_key(self, app_with_db):
        """Requisição sem X-API-Key retorna 401 sem expor informações sensíveis."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
        ) as ac:
            response = await ac.post(
                "/api/shorten",
                json={"url": "https://www.auth-sem-key.com/"},
            )

        assert response.status_code == 401, (
            f"Sem X-API-Key deve retornar 401, obtido {response.status_code}: {response.text}"
        )

        # Verifica que body não expõe dados sensíveis
        body = response.json()
        body_str = str(body).lower()
        assert "traceback" not in body_str, "Body de erro não deve conter traceback"
        assert "sqlalchemy" not in body_str, "Body de erro não deve expor SQLAlchemy"
        assert "database" not in body_str, "Body de erro não deve expor informações de banco"
        assert "detail" in body, "Response de erro deve conter campo 'detail'"

    async def test_acesso_negado_api_key_invalida(self, app_with_db, test_db_session):
        """ApiKey não cadastrada no banco retorna 401 sem expor dados sensíveis."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
            headers={"X-API-Key": "chave-inexistente-no-banco-xyz123"},
        ) as ac:
            response = await ac.post(
                "/api/shorten",
                json={"url": "https://www.auth-key-invalida.com/"},
            )

        assert response.status_code == 401, (
            f"ApiKey inválida deve retornar 401, obtido {response.status_code}: {response.text}"
        )

        # Verifica que body não expõe dados sensíveis
        body = response.json()
        body_str = str(body).lower()
        assert "traceback" not in body_str, "Body de erro não deve conter traceback"
        assert "sqlalchemy" not in body_str, "Body de erro não deve expor SQLAlchemy"

    async def test_acesso_negado_api_key_inativa(self, app_with_db, test_db_session):
        """ApiKey inativa no banco retorna 401."""
        # Insere ApiKey inativa
        api_key_value = f"inactive-key-{uuid.uuid4().hex[:12]}"
        api_key_model = ApiKeyModel(
            id=str(uuid.uuid4()),
            key=api_key_value,
            owner="inactive-owner",
            is_active=False,
        )
        test_db_session.add(api_key_model)
        await test_db_session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
            headers={"X-API-Key": api_key_value},
        ) as ac:
            response = await ac.post(
                "/api/shorten",
                json={"url": "https://www.auth-inativa.com/"},
            )

        assert response.status_code == 401, (
            f"ApiKey inativa deve retornar 401, obtido {response.status_code}: {response.text}"
        )

    async def test_acesso_negado_endpoint_url_details_sem_key(self, app_with_db):
        """GET /api/urls/{short_code} sem X-API-Key retorna 401."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
        ) as ac:
            response = await ac.get("/api/urls/qualquer-codigo")

        assert response.status_code == 401, (
            f"GET /api/urls sem autenticação deve retornar 401, obtido {response.status_code}"
        )

    async def test_acesso_permitido_em_endpoint_que_nao_requer_auth(self, app_with_db):
        """GET /api/links não requer autenticação — retorna 200 sem X-API-Key."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
        ) as ac:
            response = await ac.get("/api/links")

        # /api/links não requer auth — retorna lista (possivelmente vazia)
        assert response.status_code == 200, (
            f"GET /api/links deve ser público (200), obtido {response.status_code}: {response.text}"
        )

    async def test_api_key_valida_persiste_corretamente_no_banco(self, test_db_session):
        """ApiKey inserida via ORM é lida corretamente do banco de teste."""
        key_value = f"persist-verify-{uuid.uuid4().hex[:12]}"
        api_key = ApiKeyModel(
            id=str(uuid.uuid4()),
            key=key_value,
            owner="persist-verify-owner",
            is_active=True,
        )
        test_db_session.add(api_key)
        await test_db_session.commit()

        # Busca pelo repositório real (não mock)
        from app.infrastructure.db.repositories.api_key_repository import (
            PostgreSQLApiKeyRepository,
        )

        repo = PostgreSQLApiKeyRepository(test_db_session)
        found = await repo.get_by_key(key_value)

        assert found is not None, f"ApiKey '{key_value}' deve ser encontrada pelo repositório real"
        assert found.key == key_value, f"key esperada '{key_value}', obtida '{found.key}'"
        assert found.is_active is True, "ApiKey deve estar ativa"
        assert found.owner == "persist-verify-owner", (
            f"owner esperado 'persist-verify-owner', obtido '{found.owner}'"
        )

    async def test_dois_tenants_com_keys_diferentes_isolados(self, app_with_db, test_db_session):
        """Duas ApiKeys diferentes não interferem entre si — autenticação isolada por key."""
        key_a = f"key-owner-a-{uuid.uuid4().hex[:8]}"
        key_b = f"key-owner-b-{uuid.uuid4().hex[:8]}"

        # Insere duas ApiKeys válidas
        test_db_session.add(
            ApiKeyModel(id=str(uuid.uuid4()), key=key_a, owner="owner-a", is_active=True)
        )
        test_db_session.add(
            ApiKeyModel(id=str(uuid.uuid4()), key=key_b, owner="owner-b", is_active=True)
        )
        await test_db_session.commit()

        with patch(
            "app.api.dependencies.api_key_auth.rate_limit_by_api_key",
            new=__import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock(return_value=None),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app_with_db),
                base_url="http://test",
                follow_redirects=False,
            ) as ac:
                # Key A autentica com sucesso
                resp_a = await ac.post(
                    "/api/shorten",
                    json={"url": "https://www.owner-a.com/"},
                    headers={"X-API-Key": key_a},
                )
                # Key B autentica com sucesso
                resp_b = await ac.post(
                    "/api/shorten",
                    json={"url": "https://www.owner-b.com/"},
                    headers={"X-API-Key": key_b},
                )

        assert resp_a.status_code == 201, (
            f"Key A deve autenticar (201), obtido {resp_a.status_code}"
        )
        assert resp_b.status_code == 201, (
            f"Key B deve autenticar (201), obtido {resp_b.status_code}"
        )
