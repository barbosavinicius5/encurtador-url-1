"""Script de seed para criação de dados de teste no ambiente E2E.

Insere uma API key conhecida no banco de dados PostgreSQL do ambiente E2E isolado.
Deve ser executado uma vez antes de rodar os testes contra o servidor real Docker.

Uso:
    python -m tests.e2e.seed
    # ou com URL customizada:
    E2E_DATABASE_URL=postgresql+asyncpg://... python -m tests.e2e.seed

Idempotente: não recria a API key se ela já existir.
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone

# API key fixa para os testes E2E — usada em todos os testes contra o servidor real
TEST_API_KEY = "test-e2e-api-key-factor-12345"

# URL do banco de dados E2E (pode ser sobrescrita via variável de ambiente)
DEFAULT_E2E_DATABASE_URL = os.getenv(
    "E2E_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5456/urlshortener_e2e",
)


def create_test_api_key(db_url: str = DEFAULT_E2E_DATABASE_URL) -> str:
    """Insere a API key de teste no banco de dados E2E via SQLAlchemy async.

    Args:
        db_url: URL de conexão com o banco de dados E2E.

    Returns:
        O valor da API key criada ou já existente.

    Raises:
        Exception: Se não for possível conectar ao banco ou inserir a chave.
    """
    return asyncio.run(_async_create_test_api_key(db_url))


async def _async_create_test_api_key(db_url: str) -> str:
    """Implementação async de create_test_api_key."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.begin() as conn:
            # Verificar se já existe
            result = await conn.execute(
                text("SELECT key FROM api_keys WHERE key = :key"),
                {"key": TEST_API_KEY},
            )
            existing = result.fetchone()

            if existing:
                print(f"[seed] API key já existe: {TEST_API_KEY}")
                return TEST_API_KEY

            # Inserir nova API key
            key_id = str(uuid.uuid4())
            created_at = datetime.now(timezone.utc).isoformat()

            await conn.execute(
                text(
                    """
                    INSERT INTO api_keys (id, key, owner, is_active, created_at)
                    VALUES (:id, :key, :owner, :is_active, :created_at)
                    """
                ),
                {
                    "id": key_id,
                    "key": TEST_API_KEY,
                    "owner": "e2e-test-suite",
                    "is_active": True,
                    "created_at": created_at,
                },
            )

        print(f"[seed] API key criada com sucesso: {TEST_API_KEY}")
        return TEST_API_KEY

    finally:
        await engine.dispose()


if __name__ == "__main__":
    import sys

    db_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_E2E_DATABASE_URL
    print(f"[seed] Conectando ao banco: {db_url}")
    api_key = create_test_api_key(db_url)
    print(f"[seed] Concluído. API key: {api_key}")
