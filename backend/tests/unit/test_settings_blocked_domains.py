"""Testes unitários para configuração de blocked_domains no Settings."""

import os
from unittest.mock import patch

from app.config import Settings


class TestSettingsBlockedDomains:
    """Testes para o campo blocked_domains no Settings."""

    def test_blocked_domains_padrao_lista_vazia(self):
        """blocked_domains deve ser lista vazia por padrão."""
        env = {k: v for k, v in os.environ.items() if k != "BLOCKED_DOMAINS_CSV"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.blocked_domains == []

    def test_blocked_domains_com_um_dominio(self):
        with patch.dict(os.environ, {"BLOCKED_DOMAINS_CSV": "phishing.com"}):
            settings = Settings()
            assert "phishing.com" in settings.blocked_domains

    def test_blocked_domains_com_multiplos_dominios(self):
        with patch.dict(os.environ, {"BLOCKED_DOMAINS_CSV": "phishing.com,malware.net,evil.org"}):
            settings = Settings()
            assert "phishing.com" in settings.blocked_domains
            assert "malware.net" in settings.blocked_domains
            assert "evil.org" in settings.blocked_domains
            assert len(settings.blocked_domains) == 3

    def test_blocked_domains_remove_espacos(self):
        with patch.dict(os.environ, {"BLOCKED_DOMAINS_CSV": "phishing.com, malware.net, evil.org"}):
            settings = Settings()
            assert "phishing.com" in settings.blocked_domains
            assert "malware.net" in settings.blocked_domains
            assert "evil.org" in settings.blocked_domains
            # Garante que não há espaços nos domínios
            for domain in settings.blocked_domains:
                assert domain == domain.strip()

    def test_blocked_domains_ignora_entradas_vazias(self):
        with patch.dict(os.environ, {"BLOCKED_DOMAINS_CSV": "phishing.com,,malware.net"}):
            settings = Settings()
            # Entradas vazias devem ser ignoradas
            assert "" not in settings.blocked_domains

    def test_blocked_domains_string_vazia_resulta_lista_vazia(self):
        with patch.dict(os.environ, {"BLOCKED_DOMAINS_CSV": ""}):
            settings = Settings()
            assert settings.blocked_domains == []
