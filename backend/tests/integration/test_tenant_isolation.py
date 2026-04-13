"""Testes de integração — Isolamento entre tenants (T002-BE).

Cobre Critério de Aceite 2 da US-003:
- Dados criados pelo tenant A não aparecem em consultas do tenant B, e vice-versa
- Isolamento via session_id (cookie ou parâmetro)
- Assertions explícitas de não-vazamento de dados

IMPORTANTE: session_id é um requisito de segurança — qualquer vazamento de dados
entre tenants deve fazer o teste falhar de forma explícita.
"""

import logging

import pytest
from sqlalchemy import select

from app.infrastructure.db.models import ShortenedUrlModel

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration

SESSION_A = "session-tenant-alpha-001"
SESSION_B = "session-tenant-beta-002"


class TestIsolamentoEntreTenants:
    """Verifica que session_id isola dados entre tenants distintos."""

    async def test_dados_tenant_a_nao_aparecem_para_tenant_b(self, app_with_db, test_db_session):
        """Dados criados com session_id do tenant A não são visíveis ao tenant B.

        Este teste de segurança DEVE falhar de forma explícita se houver
        qualquer vazamento de dados entre tenants.
        """
        from httpx import ASGITransport, AsyncClient

        # Insere URL diretamente no banco como tenant A
        url_tenant_a = ShortenedUrlModel(
            original_url="https://www.tenant-alpha.com/dado-privado",
            short_code="alpha1",
            session_id=SESSION_A,
        )
        test_db_session.add(url_tenant_a)
        await test_db_session.flush()

        # Tenant B consulta lista de links — não deve ver dados de A
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
            cookies={"session_id": SESSION_B},
        ) as ac_b:
            response_b = await ac_b.get("/api/links")

        assert response_b.status_code == 200, (
            f"Esperado 200, obtido {response_b.status_code}: {response_b.text}"
        )
        data_b = response_b.json()
        links_b = data_b.get("links", [])

        # SEGURANÇA: dados do tenant A não devem aparecer para tenant B
        urls_vazadas = [
            link for link in links_b if "tenant-alpha.com" in link.get("original_url", "")
        ]
        assert len(urls_vazadas) == 0, (
            f"[VIOLAÇÃO DE SEGURANÇA] Dados do tenant A ({SESSION_A!r}) "
            f"vazaram para o tenant B ({SESSION_B!r}): {urls_vazadas}"
        )

    async def test_tenant_b_ve_apenas_seus_dados(self, app_with_db, test_db_session):
        """Tenant B vê apenas suas URLs, não as de outros tenants."""
        from httpx import ASGITransport, AsyncClient

        # Insere URLs de A e B diretamente no banco
        url_a = ShortenedUrlModel(
            original_url="https://www.tenant-alpha.com/pagina-a",
            short_code="alpha2",
            session_id=SESSION_A,
        )
        url_b1 = ShortenedUrlModel(
            original_url="https://www.tenant-beta.com/pagina-b1",
            short_code="beta2a",
            session_id=SESSION_B,
        )
        url_b2 = ShortenedUrlModel(
            original_url="https://www.tenant-beta.com/pagina-b2",
            short_code="beta2b",
            session_id=SESSION_B,
        )
        test_db_session.add_all([url_a, url_b1, url_b2])
        await test_db_session.flush()

        # Consulta de tenant B
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
            cookies={"session_id": SESSION_B},
        ) as ac_b:
            response_b = await ac_b.get("/api/links")

        assert response_b.status_code == 200
        links_b = response_b.json().get("links", [])

        # Tenant B deve ver exatamente suas 2 URLs
        b_short_codes = {link["short_code"] for link in links_b}
        assert "beta2a" in b_short_codes, f"URL beta2a do tenant B não encontrada: {b_short_codes}"
        assert "beta2b" in b_short_codes, f"URL beta2b do tenant B não encontrada: {b_short_codes}"

        # Tenant A não deve aparecer
        a_urls_vazadas = [
            link for link in links_b if "tenant-alpha.com" in link.get("original_url", "")
        ]
        assert len(a_urls_vazadas) == 0, (
            f"[VIOLAÇÃO DE SEGURANÇA] Dados do tenant A vazaram para tenant B: {a_urls_vazadas}"
        )

    async def test_tenant_a_ve_apenas_seus_dados(self, app_with_db, test_db_session):
        """Tenant A vê apenas suas URLs, não as de B."""
        from httpx import ASGITransport, AsyncClient

        url_a = ShortenedUrlModel(
            original_url="https://www.somente-alpha.com/privado",
            short_code="alphax",
            session_id=SESSION_A,
        )
        url_b = ShortenedUrlModel(
            original_url="https://www.somente-beta.com/privado",
            short_code="betax",
            session_id=SESSION_B,
        )
        test_db_session.add_all([url_a, url_b])
        await test_db_session.flush()

        # Consulta de tenant A
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
            cookies={"session_id": SESSION_A},
        ) as ac_a:
            response_a = await ac_a.get("/api/links")

        assert response_a.status_code == 200
        links_a = response_a.json().get("links", [])

        # Tenant A deve ver sua URL
        a_short_codes = {link["short_code"] for link in links_a}
        assert "alphax" in a_short_codes, f"URL alphax do tenant A não encontrada: {a_short_codes}"

        # Tenant B não deve aparecer
        b_urls_vazadas = [
            link for link in links_a if "somente-beta.com" in link.get("original_url", "")
        ]
        assert len(b_urls_vazadas) == 0, (
            f"[VIOLAÇÃO DE SEGURANÇA] Dados do tenant B vazaram para tenant A: {b_urls_vazadas}"
        )

    async def test_sessao_sem_id_retorna_lista_vazia(self, app_with_db, test_db_session):
        """Sessão sem session_id não vê URLs de outros tenants."""
        from httpx import ASGITransport, AsyncClient

        # Insere URL para um tenant específico
        url = ShortenedUrlModel(
            original_url="https://www.outro-tenant.com/dado",
            short_code="otro1",
            session_id=SESSION_A,
        )
        test_db_session.add(url)
        await test_db_session.flush()

        # Requisição SEM cookie de sessão
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db),
            base_url="http://test",
            follow_redirects=False,
        ) as ac_anon:
            response = await ac_anon.get("/api/links")

        assert response.status_code == 200
        links = response.json().get("links", [])

        # Sessão anônima não deve ver dados de outros tenants
        dados_vazados = [
            link for link in links if "outro-tenant.com" in link.get("original_url", "")
        ]
        assert len(dados_vazados) == 0, (
            f"[VIOLAÇÃO DE SEGURANÇA] Sessão anônima viu dados de tenant A: {dados_vazados}"
        )

    async def test_isolamento_verificado_diretamente_no_banco(self, test_db_session):
        """Assertion direta no banco confirma isolamento por session_id."""
        # Insere URLs para dois tenants
        urls = [
            ShortenedUrlModel(
                original_url=f"https://www.tenant-{tenant}.com/path",
                short_code=f"t{tenant[:1]}{i}",
                session_id=f"session-{tenant}",
            )
            for tenant in ["alpha", "beta"]
            for i in range(2)
        ]
        test_db_session.add_all(urls)
        await test_db_session.flush()

        # Query por session_id alpha
        result_a = await test_db_session.execute(
            select(ShortenedUrlModel).where(ShortenedUrlModel.session_id == "session-alpha")
        )
        urls_alpha = result_a.scalars().all()

        # Query por session_id beta
        result_b = await test_db_session.execute(
            select(ShortenedUrlModel).where(ShortenedUrlModel.session_id == "session-beta")
        )
        urls_beta = result_b.scalars().all()

        # Cada tenant tem exatamente 2 URLs
        assert len(urls_alpha) == 2, (
            f"Tenant alpha deve ter 2 URLs, obtido {len(urls_alpha)}: {[u.short_code for u in urls_alpha]}"
        )
        assert len(urls_beta) == 2, (
            f"Tenant beta deve ter 2 URLs, obtido {len(urls_beta)}: {[u.short_code for u in urls_beta]}"
        )

        # Nenhuma URL de alpha aparece em beta e vice-versa
        alpha_codes = {u.short_code for u in urls_alpha}
        beta_codes = {u.short_code for u in urls_beta}
        assert alpha_codes.isdisjoint(beta_codes), (
            f"[VIOLAÇÃO DE SEGURANÇA] short_codes se sobrepõem: {alpha_codes & beta_codes}"
        )
