"""
Teste de Carga — Redirecionamento (GET /{short_code})

Objetivo: Validar que p95 de latência é ≤ 100ms sob 50 usuários virtuais simultâneos.

Pré-requisitos:
  - locust instalado: pip install locust
  - Aplicação rodando com short_code pré-aquecido no cache Redis

Uso:
  locust -f locustfile.py --headless -u 50 -r 10 --run-time 30s --host http://localhost:8001

Variáveis de ambiente:
  PERF_SHORT_CODE: short_code válido pré-cadastrado (default: perf01)
"""

import os

from locust import HttpUser, between, task

SHORT_CODE = os.getenv("PERF_SHORT_CODE", "perf01")


class RedirectUser(HttpUser):
    """Usuário virtual que testa o endpoint de redirecionamento."""

    wait_time = between(0.05, 0.15)  # Pausa de 50–150ms entre requisições por VU

    @task
    def redirect(self):
        """Realiza GET /{short_code} sem seguir o redirect."""
        with self.client.get(
            f"/{SHORT_CODE}",
            allow_redirects=False,
            catch_response=True,
            name="GET /{short_code}",
        ) as response:
            if response.status_code in (301, 302):
                response.success()
            else:
                response.failure(f"Status inesperado: {response.status_code}")
