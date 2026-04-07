"""Módulo de sanitização explícita de inputs do usuário."""

import re
import unicodedata

from app.domain.exceptions import InvalidUrlError

_MAX_URL_LENGTH = 2048
_MAX_SLUG_LENGTH = 50


def sanitize_url(raw: str) -> str:
    """Sanitiza uma URL bruta antes de qualquer validação ou persistência.

    Operações:
        1. Remove espaços em branco nas extremidades
        2. Remove caracteres de controle Unicode (categoria Cc)
        3. Normaliza scheme para lowercase
        4. Valida tamanho máximo (2048 chars)

    Args:
        raw: A string bruta recebida do usuário.

    Returns:
        URL sanitizada pronta para validação estrutural.

    Raises:
        InvalidUrlError: Se a URL exceder 2048 caracteres após sanitização.
    """
    # 1. Remove espaços nas extremidades
    result = raw.strip()

    # 2. Remove caracteres de controle Unicode (categoria Cc)
    result = "".join(ch for ch in result if unicodedata.category(ch) != "Cc")

    # 3. Normaliza scheme para lowercase preservando o restante da URL
    if "://" in result:
        scheme, rest = result.split("://", 1)
        result = f"{scheme.lower()}://{rest}"

    # 4. Valida tamanho máximo
    if len(result) > _MAX_URL_LENGTH:
        raise InvalidUrlError(
            url=raw,
            reason=f"URL excede {_MAX_URL_LENGTH} caracteres",
        )

    return result


def sanitize_slug(raw: str) -> str:
    """Sanitiza um slug customizado antes de qualquer validação ou persistência.

    Operações:
        1. Remove espaços em branco nas extremidades
        2. Converte para lowercase
        3. Remove caracteres não alfanuméricos (exceto hífen e underscore)
        4. Valida tamanho máximo (50 chars)

    Args:
        raw: O slug bruto recebido do usuário.

    Returns:
        Slug sanitizado.

    Raises:
        InvalidUrlError: Se o slug exceder 50 caracteres após sanitização.
    """
    # 1. Remove espaços e converte para lowercase
    result = raw.strip().lower()

    # 2. Remove caracteres não alfanuméricos, exceto hífen e underscore
    result = re.sub(r"[^\w\-]", "", result)

    # 3. Valida tamanho máximo
    if len(result) > _MAX_SLUG_LENGTH:
        raise InvalidUrlError(
            url=raw,
            reason=f"slug excede {_MAX_SLUG_LENGTH} caracteres",
        )

    return result
