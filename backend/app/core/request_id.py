"""Módulo de gestão de request_id via contextvars.

Provê geração de UUID v4 e armazenamento/recuperação via ContextVar,
garantindo isolamento entre requisições concorrentes.
"""

import uuid
from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar("request_id", default="N/A")


def get_request_id() -> str:
    """Retorna o request_id do contexto atual.

    Returns:
        UUID da requisição atual, ou "N/A" se não houver requisição ativa.
    """
    return _request_id_var.get()


def set_request_id(value: str) -> None:
    """Define o request_id no contexto atual.

    Args:
        value: UUID da requisição a ser armazenado no contextvars.
    """
    _request_id_var.set(value)


def generate_request_id() -> str:
    """Gera um novo UUID v4 para identificar uma requisição.

    Returns:
        String com UUID v4 gerado.
    """
    return str(uuid.uuid4())
