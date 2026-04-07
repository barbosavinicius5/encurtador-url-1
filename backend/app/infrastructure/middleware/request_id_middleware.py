"""Middleware de geração e propagação de request_id via contextvars."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_id import generate_request_id, set_request_id


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware que gera um UUID v4 para cada requisição.

    O request_id é:
    - Armazenado em contextvars para ser acessível em qualquer camada
    - Adicionado ao header de resposta X-Request-ID para rastreabilidade
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Gera request_id, armazena no contextvars e adiciona ao header de resposta.

        Args:
            request: Requisição HTTP recebida.
            call_next: Próximo middleware ou handler na cadeia.

        Returns:
            Resposta com header X-Request-ID adicionado.
        """
        request_id = generate_request_id()
        set_request_id(request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response
