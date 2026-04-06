"""DTOs para o endpoint de listagem de links por sessão."""

from datetime import datetime

from pydantic import BaseModel


class LinkItemResponse(BaseModel):
    """DTO de um link encurtado na listagem."""

    short_code: str
    original_url: str
    short_url: str
    click_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LinkListResponse(BaseModel):
    """DTO de response da listagem de links."""

    links: list[LinkItemResponse]
