"""Testes unitários para comportamentos da entidade ShortenedUrl."""

from datetime import UTC, datetime, timedelta

from app.domain.entities.shortened_url import ShortenedUrl


class TestShortenedUrlRegisterClick:
    """Testes para o método register_click da entidade ShortenedUrl."""

    def test_register_click_incrementa_contador(self):
        entity = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="abc123",
            session_id="sess-001",
        )
        assert entity.click_count == 0
        entity.register_click()
        assert entity.click_count == 1

    def test_register_click_tres_vezes_incrementa_para_3(self):
        entity = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="abc123",
            session_id="sess-001",
        )
        entity.register_click()
        entity.register_click()
        entity.register_click()
        assert entity.click_count == 3

    def test_register_click_atualiza_last_clicked_at(self):
        entity = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="abc123",
            session_id="sess-001",
        )
        assert entity.last_clicked_at is None
        entity.register_click()
        assert entity.last_clicked_at is not None

    def test_register_click_com_timestamp_customizado(self):
        entity = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="abc123",
            session_id="sess-001",
        )
        timestamp = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
        entity.register_click(timestamp=timestamp)
        assert entity.last_clicked_at == timestamp

    def test_register_click_sem_timestamp_usa_now(self):
        entity = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="abc123",
            session_id="sess-001",
        )
        before = datetime.now(UTC)
        entity.register_click()
        after = datetime.now(UTC)
        assert entity.last_clicked_at is not None
        assert before <= entity.last_clicked_at <= after


class TestShortenedUrlIsExpired:
    """Testes para o método is_expired da entidade ShortenedUrl."""

    def test_is_expired_retorna_false_sem_expires_at(self):
        entity = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="abc123",
            session_id="sess-001",
        )
        assert entity.is_expired() is False

    def test_is_expired_retorna_true_com_data_passada(self):
        entity = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="abc123",
            session_id="sess-001",
            expires_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        assert entity.is_expired() is True

    def test_is_expired_retorna_false_com_data_futura(self):
        future = datetime.now(UTC) + timedelta(hours=1)
        entity = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="abc123",
            session_id="sess-001",
            expires_at=future,
        )
        assert entity.is_expired() is False

    def test_is_expired_retorna_false_com_expires_at_none(self):
        entity = ShortenedUrl(
            original_url="https://exemplo.com",
            short_code="abc123",
            session_id="sess-001",
            expires_at=None,
        )
        assert entity.is_expired() is False
