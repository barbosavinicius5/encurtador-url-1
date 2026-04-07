"""DTOs para o use case de consulta de detalhes de URL."""

from pydantic import BaseModel


class GetUrlDetailsResponse(BaseModel):
    """Resposta com detalhes de uma URL encurtada."""

    original_url: str
    short_code: str
    short_url: str
    click_count: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "original_url": "https://www.exemplo.com/minha-pagina-muito-longa",
                "short_code": "abc123",
                "short_url": "https://short.app/abc123",
                "click_count": 42,
            }
        }
    }
