"""DTOs para o use case de encurtamento de URL."""

from pydantic import BaseModel


class ShortenUrlRequest(BaseModel):
    """DTO de request para encurtamento de URL.

    A validação da URL é feita no use case via UrlValue,
    que lança ValueError capturado pelo router e convertido em HTTP 422.
    """

    url: str


class ShortenUrlResponse(BaseModel):
    """DTO de response para o link encurtado."""

    short_code: str
    short_url: str
    original_url: str
