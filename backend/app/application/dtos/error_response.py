"""DTO para respostas de erro padronizadas da API.

Define o contrato público de erro: status_code, error_type e message.
Utilizado pelos exception handlers globais registrados no main.py.
"""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Resposta de erro padronizada para todos os endpoints da API.

    Attributes:
        status_code: Código HTTP do erro (ex.: 401, 404, 422, 429, 500).
        error_type: Identificador semântico do tipo de erro em SNAKE_CASE
                    (ex.: "NOT_FOUND", "UNAUTHORIZED", "VALIDATION_ERROR").
        message: Mensagem legível por humanos descrevendo o erro.
    """

    status_code: int
    error_type: str
    message: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "status_code": 404,
                "error_type": "NOT_FOUND",
                "message": "URL encurtada não encontrada.",
            }
        }
    }
