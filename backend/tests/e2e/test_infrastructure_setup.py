"""Testes de validação da infraestrutura E2E.

Verifica que todos os componentes necessários para testes E2E com Playwright
estão corretamente configurados: dependências, fixtures, seed, docker-compose.
"""

import importlib
import subprocess
from pathlib import Path

import pytest

# Caminhos de referência (relativos ao arquivo de teste)
# tests/e2e/test_*.py -> parents[0]=e2e, parents[1]=tests, parents[2]=backend, parents[3]=encurtador-url-1
BACKEND_DIR = Path(__file__).parents[2]
PROJECT_ROOT = Path(__file__).parents[3]
E2E_DIR = Path(__file__).parent


# ————————————————————————————————————————————————————
# Testes de dependências Python
# ————————————————————————————————————————————————————


@pytest.mark.e2e
class TestDependenciasE2E:
    """Verifica que as dependências de E2E estão disponíveis."""

    def test_playwright_importavel(self):
        """playwright deve estar instalado e importável."""
        try:
            importlib.import_module("playwright")
        except ImportError:
            pytest.fail("playwright não está instalado. Execute: pip install playwright")

    def test_pytest_playwright_importavel(self):
        """pytest-playwright deve estar instalado e importável."""
        try:
            importlib.import_module("pytest_playwright")
        except ImportError:
            pytest.fail(
                "pytest-playwright não está instalado. Execute: pip install pytest-playwright"
            )

    def test_pytest_rerunfailures_importavel(self):
        """pytest-rerunfailures deve estar instalado e importável."""
        try:
            importlib.import_module("pytest_rerunfailures")
        except ImportError:
            pytest.fail(
                "pytest-rerunfailures não está instalado. Execute: pip install pytest-rerunfailures"
            )

    def test_pytest_timeout_importavel(self):
        """pytest-timeout deve estar instalado e importável."""
        try:
            importlib.import_module("pytest_timeout")
        except ImportError:
            pytest.fail("pytest-timeout não está instalado. Execute: pip install pytest-timeout")

    def test_requirements_dev_contem_playwright(self):
        """requirements-dev.txt deve conter playwright."""
        req_file = BACKEND_DIR / "requirements-dev.txt"
        assert req_file.exists(), f"requirements-dev.txt não encontrado em {req_file}"
        content = req_file.read_text()
        assert "playwright" in content, "playwright não encontrado em requirements-dev.txt"

    def test_requirements_dev_contem_pytest_playwright(self):
        """requirements-dev.txt deve conter pytest-playwright."""
        req_file = BACKEND_DIR / "requirements-dev.txt"
        content = req_file.read_text()
        assert "pytest-playwright" in content, (
            "pytest-playwright não encontrado em requirements-dev.txt"
        )

    def test_requirements_dev_contem_pytest_rerunfailures(self):
        """requirements-dev.txt deve conter pytest-rerunfailures (retry policy)."""
        req_file = BACKEND_DIR / "requirements-dev.txt"
        content = req_file.read_text()
        assert "pytest-rerunfailures" in content, (
            "pytest-rerunfailures não encontrado em requirements-dev.txt"
        )

    def test_requirements_dev_contem_pytest_timeout(self):
        """requirements-dev.txt deve conter pytest-timeout."""
        req_file = BACKEND_DIR / "requirements-dev.txt"
        content = req_file.read_text()
        assert "pytest-timeout" in content, "pytest-timeout não encontrado em requirements-dev.txt"


# ————————————————————————————————————————————————————
# Testes de estrutura de arquivos
# ————————————————————————————————————————————————————


@pytest.mark.e2e
class TestEstruturaArquivosE2E:
    """Verifica que a estrutura de arquivos E2E está correta."""

    def test_pasta_e2e_existe(self):
        """Pasta tests/e2e deve existir."""
        assert E2E_DIR.is_dir(), f"Pasta e2e não encontrada: {E2E_DIR}"

    def test_init_e2e_existe(self):
        """tests/e2e/__init__.py deve existir."""
        init_file = E2E_DIR / "__init__.py"
        assert init_file.exists(), f"__init__.py não encontrado em {init_file}"

    def test_conftest_e2e_existe(self):
        """tests/e2e/conftest.py deve existir."""
        conftest = E2E_DIR / "conftest.py"
        assert conftest.exists(), f"conftest.py não encontrado em {conftest}"

    def test_seed_py_existe(self):
        """tests/e2e/seed.py deve existir."""
        seed_file = E2E_DIR / "seed.py"
        assert seed_file.exists(), (
            f"seed.py não encontrado em {seed_file}. "
            "Crie tests/e2e/seed.py com função create_test_api_key"
        )

    def test_docker_compose_e2e_existe(self):
        """docker-compose.e2e.yml deve existir na raiz do projeto."""
        compose_file = PROJECT_ROOT / "docker-compose.e2e.yml"
        assert compose_file.exists(), f"docker-compose.e2e.yml não encontrado em {compose_file}"


# ————————————————————————————————————————————————————
# Testes de configuração do seed
# ————————————————————————————————————————————————————


@pytest.mark.e2e
class TestSeedE2E:
    """Verifica que o seed de dados E2E funciona corretamente."""

    def test_seed_modulo_importavel(self):
        """tests/e2e/seed.py deve ser importável."""
        try:
            from tests.e2e import seed  # noqa: F401
        except ImportError as e:
            pytest.fail(f"Não foi possível importar tests.e2e.seed: {e}")

    def test_seed_tem_funcao_create_test_api_key(self):
        """seed.py deve expor a função create_test_api_key."""
        from tests.e2e import seed

        assert hasattr(seed, "create_test_api_key"), (
            "seed.py não possui função 'create_test_api_key'"
        )
        assert callable(seed.create_test_api_key), (
            "'create_test_api_key' em seed.py deve ser callable"
        )

    def test_seed_tem_constante_test_api_key(self):
        """seed.py deve expor a constante TEST_API_KEY."""
        from tests.e2e import seed

        assert hasattr(seed, "TEST_API_KEY"), "seed.py não possui constante 'TEST_API_KEY'"
        assert isinstance(seed.TEST_API_KEY, str), "TEST_API_KEY deve ser string"
        assert len(seed.TEST_API_KEY) > 0, "TEST_API_KEY não pode ser string vazia"


# ————————————————————————————————————————————————————
# Testes de configuração do pytest
# ————————————————————————————————————————————————————


@pytest.mark.e2e
class TestConfiguracaoPytest:
    """Verifica que o pytest está corretamente configurado para E2E."""

    def test_pyproject_contem_marcador_e2e(self):
        """pyproject.toml deve conter o marcador e2e registrado."""
        pyproject = BACKEND_DIR / "pyproject.toml"
        assert pyproject.exists(), f"pyproject.toml não encontrado em {pyproject}"
        content = pyproject.read_text()
        assert "e2e" in content, "Marcador 'e2e' não encontrado em pyproject.toml"

    def test_pyproject_contem_timeout(self):
        """pyproject.toml deve conter configuração de timeout."""
        pyproject = BACKEND_DIR / "pyproject.toml"
        content = pyproject.read_text()
        assert "timeout" in content, "Configuração 'timeout' não encontrada em pyproject.toml"

    def test_pyproject_contem_reruns(self):
        """pyproject.toml deve conter configuração de reruns."""
        pyproject = BACKEND_DIR / "pyproject.toml"
        content = pyproject.read_text()
        assert "reruns" in content, "Configuração 'reruns' não encontrada em pyproject.toml"


# ————————————————————————————————————————————————————
# Testes de fixtures do conftest E2E
# ————————————————————————————————————————————————————


@pytest.mark.e2e
class TestFixturesConftest:
    """Verifica que o conftest.py de E2E contém as fixtures necessárias."""

    def test_conftest_tem_fixture_e2e_base_url(self):
        """conftest.py deve conter fixture e2e_base_url."""
        conftest = E2E_DIR / "conftest.py"
        content = conftest.read_text()
        assert "e2e_base_url" in content, (
            "Fixture 'e2e_base_url' não encontrada em tests/e2e/conftest.py"
        )

    def test_conftest_tem_fixture_e2e_api_key(self):
        """conftest.py deve conter fixture e2e_api_key."""
        conftest = E2E_DIR / "conftest.py"
        content = conftest.read_text()
        assert "e2e_api_key" in content, (
            "Fixture 'e2e_api_key' não encontrada em tests/e2e/conftest.py"
        )

    def test_conftest_tem_fixture_playwright_page(self):
        """conftest.py deve conter fixture playwright_page."""
        conftest = E2E_DIR / "conftest.py"
        content = conftest.read_text()
        assert "playwright_page" in content or "browser_context" in content, (
            "Fixture de browser Playwright não encontrada em tests/e2e/conftest.py. "
            "Deve existir 'playwright_page' ou 'browser_context'"
        )

    def test_conftest_tem_fixture_api_client(self):
        """conftest.py deve conter fixture api_client."""
        conftest = E2E_DIR / "conftest.py"
        content = conftest.read_text()
        assert "api_client" in content, (
            "Fixture 'api_client' não encontrada em tests/e2e/conftest.py"
        )

    def test_conftest_tem_fixture_db_cleanup(self):
        """conftest.py deve conter fixture db_cleanup com autouse."""
        conftest = E2E_DIR / "conftest.py"
        content = conftest.read_text()
        assert "db_cleanup" in content, (
            "Fixture 'db_cleanup' não encontrada em tests/e2e/conftest.py"
        )
        assert "autouse" in content, (
            "Fixture 'db_cleanup' deve ter autouse=True em tests/e2e/conftest.py"
        )


# ————————————————————————————————————————————————————
# Testes de configuração do docker-compose.e2e.yml
# ————————————————————————————————————————————————————


@pytest.mark.e2e
class TestDockerComposeE2E:
    """Verifica que docker-compose.e2e.yml está corretamente configurado."""

    def _get_compose_content(self) -> str:
        compose_file = PROJECT_ROOT / "docker-compose.e2e.yml"
        if not compose_file.exists():
            pytest.skip("docker-compose.e2e.yml ainda não existe")
        return compose_file.read_text()

    def test_compose_tem_servico_app_e2e(self):
        """docker-compose.e2e.yml deve ter serviço app-e2e."""
        content = self._get_compose_content()
        assert "app-e2e" in content, "Serviço 'app-e2e' não encontrado em docker-compose.e2e.yml"

    def test_compose_expoe_porta_8001(self):
        """docker-compose.e2e.yml deve expor porta 8001."""
        content = self._get_compose_content()
        assert "8001" in content, "Porta 8001 não encontrada em docker-compose.e2e.yml"

    def test_compose_tem_environment_test(self):
        """docker-compose.e2e.yml deve configurar ENVIRONMENT=test."""
        content = self._get_compose_content()
        assert "test" in content.lower(), (
            "ENVIRONMENT=test não encontrado em docker-compose.e2e.yml"
        )

    def test_compose_tem_healthcheck(self):
        """docker-compose.e2e.yml deve ter healthcheck configurado."""
        content = self._get_compose_content()
        assert "healthcheck" in content, "healthcheck não encontrado em docker-compose.e2e.yml"

    def test_compose_valido_sintaxe(self):
        """docker-compose.e2e.yml deve ter sintaxe YAML válida."""
        compose_file = PROJECT_ROOT / "docker-compose.e2e.yml"
        if not compose_file.exists():
            pytest.skip("docker-compose.e2e.yml ainda não existe")
        try:
            import yaml  # type: ignore[import-not-found]

            with open(compose_file) as f:
                data = yaml.safe_load(f)
            assert data is not None, "docker-compose.e2e.yml está vazio"
        except ImportError:
            # Se pyyaml não estiver disponível, tentar com docker-compose
            result = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "config", "--quiet"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, (
                f"docker-compose.e2e.yml tem sintaxe inválida: {result.stderr}"
            )


# ————————————————————————————————————————————————————
# Testes de documentação
# ————————————————————————————————————————————————————


@pytest.mark.e2e
class TestDocumentacaoE2E:
    """Verifica que a documentação E2E está presente no README."""

    def _find_readme_with_content(self, search: str) -> bool:
        """Verifica se algum README contém o texto buscado."""
        for readme_path in [
            PROJECT_ROOT / "README.md",
            BACKEND_DIR / "README.md",
        ]:
            if readme_path.exists():
                content = readme_path.read_text()
                if search in content:
                    return True
        return False

    def test_readme_tem_secao_testes_e2e(self):
        """README.md deve conter seção 'Testes E2E'."""
        assert self._find_readme_with_content("Testes E2E"), (
            "Seção 'Testes E2E' não encontrada em nenhum README.md do projeto"
        )

    def test_readme_tem_comando_docker_compose_e2e(self):
        """README.md deve conter comando docker-compose.e2e.yml."""
        assert self._find_readme_with_content("docker-compose.e2e.yml"), (
            "Comando 'docker-compose.e2e.yml' não encontrado em nenhum README.md"
        )

    def test_readme_tem_comando_pytest_e2e(self):
        """README.md deve conter comando para executar testes E2E."""
        assert self._find_readme_with_content("pytest -m e2e"), (
            "Comando 'pytest -m e2e' não encontrado em nenhum README.md"
        )
