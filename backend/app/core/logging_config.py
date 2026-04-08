"""Configuração de logging estruturado JSON com propagação de request_id.

Fornece:
- RequestIdFilter: injeta request_id do contextvars em cada LogRecord
- CustomJsonFormatter: formata logs em JSON com campos obrigatórios
- build_json_handler: constrói um StreamHandler com formatter e filter configurados
- configure_logging: configura o root logger com JSON formatter
"""

import datetime
import logging
from typing import IO, Optional

from pythonjsonlogger.json import JsonFormatter

from app.core.request_id import get_request_id


class RequestIdFilter(logging.Filter):
    """Filter que injeta o request_id do contextvars em cada LogRecord.

    Garante que todos os logs emitidos durante o processamento de uma
    requisição contenham o mesmo request_id, facilitando a rastreabilidade.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Adiciona o request_id ao LogRecord.

        Args:
            record: LogRecord a ser processado.

        Returns:
            True sempre (nunca filtra registros).
        """
        try:
            record.request_id = get_request_id()
        except Exception:
            record.request_id = "N/A"
        return True


class CustomJsonFormatter(JsonFormatter):
    """Formatter JSON com campos obrigatórios: timestamp, level, request_id e message.

    Garante que o timestamp seja em formato ISO 8601 e que o request_id
    esteja sempre presente nos logs.
    """

    def add_fields(
        self,
        log_record: dict,
        record: logging.LogRecord,
        message_dict: dict,
    ) -> None:
        """Adiciona campos personalizados ao log record JSON.

        Args:
            log_record: Dicionário de saída do log.
            record: LogRecord original do Python.
            message_dict: Dicionário com informações da mensagem.
        """
        super().add_fields(log_record, record, message_dict)

        # Timestamp em formato ISO 8601 com UTC
        log_record["timestamp"] = (
            datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%f"
            )[:-3]
            + "Z"
        )

        # Nível de severidade
        log_record["level"] = record.levelname

        # request_id do contextvars (injetado pelo RequestIdFilter)
        log_record["request_id"] = getattr(record, "request_id", "N/A")

        # Remover campos redundantes gerados pelo json-logger base
        log_record.pop("color_message", None)


def build_json_handler(
    stream: Optional[IO] = None,
) -> logging.StreamHandler:
    """Constrói um StreamHandler configurado com JSON formatter e RequestIdFilter.

    Args:
        stream: Stream de saída (padrão: sys.stderr via StreamHandler default).

    Returns:
        StreamHandler configurado.
    """
    if stream is not None:
        handler = logging.StreamHandler(stream=stream)
    else:
        handler = logging.StreamHandler()

    formatter = CustomJsonFormatter(
        fmt="%(message)s %(name)s",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    return handler


# Configuração compatível com logging.config.dictConfig
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "app.core.logging_config.RequestIdFilter",
        },
    },
    "formatters": {
        "json": {
            "()": "app.core.logging_config.CustomJsonFormatter",
            "fmt": "%(message)s %(name)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_id"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
