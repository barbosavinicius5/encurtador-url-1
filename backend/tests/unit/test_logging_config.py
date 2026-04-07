"""Testes unitários para o logging configurado com JSON formatter e RequestIdFilter."""

import io
import json
import logging

import pytest

from app.core.request_id import set_request_id


class TestRequestIdFilter:
    """Testa o RequestIdFilter que injeta request_id nos LogRecords."""

    def test_filter_injeta_request_id_no_log_record(self):
        """O filter deve adicionar o atributo request_id ao LogRecord."""
        from app.core.logging_config import RequestIdFilter

        filtro = RequestIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="mensagem teste",
            args=(),
            exc_info=None,
        )
        filtro.filter(record)
        assert hasattr(record, "request_id")

    def test_filter_usa_contextvars_para_request_id(self):
        """O filter deve ler o request_id do contextvars."""
        from app.core.logging_config import RequestIdFilter

        set_request_id("test-uuid-xyz")
        filtro = RequestIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="mensagem teste",
            args=(),
            exc_info=None,
        )
        filtro.filter(record)
        assert record.request_id == "test-uuid-xyz"

    def test_filter_retorna_na_quando_sem_contexto(self):
        """Quando não há request_id no contextvars, deve usar 'N/A'."""
        from app.core.logging_config import RequestIdFilter

        # Garantir contexto limpo - usar valor padrão
        set_request_id("N/A")
        filtro = RequestIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="mensagem teste",
            args=(),
            exc_info=None,
        )
        result = filtro.filter(record)
        assert result is True  # Nunca deve lançar exceção
        assert record.request_id == "N/A"

    def test_filter_nunca_lanca_excecao(self):
        """O filter nunca deve lançar exceção, independente do estado do contextvars."""
        from app.core.logging_config import RequestIdFilter

        filtro = RequestIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="erro teste",
            args=(),
            exc_info=None,
        )
        # Não deve lançar exceção
        try:
            filtro.filter(record)
        except Exception as e:
            pytest.fail(f"Filter lançou exceção inesperada: {e}")


class TestJsonLoggingOutput:
    """Testa se o output de logging é JSON válido com campos obrigatórios."""

    def test_log_output_eh_json_valido(self):
        """A saída do logging deve ser JSON parseável."""
        from app.core.logging_config import build_json_handler

        stream = io.StringIO()
        handler = build_json_handler(stream=stream)

        logger = logging.getLogger("test_json_valid")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False

        set_request_id("req-id-123")
        logger.info("Mensagem de teste JSON")

        output = stream.getvalue().strip()
        assert output, "A saída do log não pode estar vazia"

        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_log_contém_campos_obrigatorios(self):
        """O JSON deve conter: timestamp, level, request_id e message."""
        from app.core.logging_config import build_json_handler

        stream = io.StringIO()
        handler = build_json_handler(stream=stream)

        logger = logging.getLogger("test_campos_obrigatorios")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False

        set_request_id("req-abc-789")
        logger.info("Verificando campos obrigatórios")

        output = stream.getvalue().strip()
        parsed = json.loads(output)

        assert "timestamp" in parsed, "Campo 'timestamp' ausente"
        assert "level" in parsed, "Campo 'level' ausente"
        assert "request_id" in parsed, "Campo 'request_id' ausente"
        assert "message" in parsed, "Campo 'message' ausente"

    def test_timestamp_formato_iso8601(self):
        """O campo timestamp deve estar em formato ISO 8601."""
        import re

        from app.core.logging_config import build_json_handler

        stream = io.StringIO()
        handler = build_json_handler(stream=stream)

        logger = logging.getLogger("test_timestamp")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False

        logger.info("Testando timestamp ISO 8601")

        output = stream.getvalue().strip()
        parsed = json.loads(output)

        # ISO 8601 básico: YYYY-MM-DDTHH:MM:SS
        iso_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.match(iso_pattern, parsed["timestamp"]), (
            f"Timestamp '{parsed['timestamp']}' não está em formato ISO 8601"
        )

    def test_request_id_presente_no_log(self):
        """O request_id definido no contextvars deve aparecer no log."""
        from app.core.logging_config import build_json_handler

        stream = io.StringIO()
        handler = build_json_handler(stream=stream)

        logger = logging.getLogger("test_request_id_log")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False

        expected_id = "my-test-request-id-42"
        set_request_id(expected_id)
        logger.info("Testando request_id no log")

        output = stream.getvalue().strip()
        parsed = json.loads(output)

        assert parsed["request_id"] == expected_id

    def test_level_correto_no_log(self):
        """O campo level deve refletir o nível de severidade correto."""
        from app.core.logging_config import build_json_handler

        stream = io.StringIO()
        handler = build_json_handler(stream=stream)

        logger = logging.getLogger("test_level")
        logger.handlers = [handler]
        logger.setLevel(logging.WARNING)
        logger.propagate = False

        logger.warning("Mensagem de warning")

        output = stream.getvalue().strip()
        parsed = json.loads(output)

        assert parsed["level"] == "WARNING"
