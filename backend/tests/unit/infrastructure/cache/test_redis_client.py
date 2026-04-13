"""Testes unitários para MockRedisClient (comportamento do RedisClient)."""

import pytest
from tests.helpers import MockRedisClient


@pytest.fixture
def redis():
    """Fixture que fornece um MockRedisClient limpo."""
    return MockRedisClient()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_e_get_armazena_e_recupera_valor(redis):
    """set + get: armazena e recupera valor corretamente."""
    await redis.set("chave", "valor")
    resultado = await redis.get("chave")
    assert resultado == "valor"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_chave_inexistente_retorna_none(redis):
    """get com chave inexistente retorna None."""
    resultado = await redis.get("chave-que-nao-existe")
    assert resultado is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_remove_chave(redis):
    """delete remove a chave e get retorna None em seguida."""
    await redis.set("chave-temporaria", "valor-temporario")
    assert await redis.get("chave-temporaria") == "valor-temporario"

    await redis.delete("chave-temporaria")
    assert await redis.get("chave-temporaria") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_chave_inexistente_nao_levanta_erro(redis):
    """delete de chave inexistente não levanta exceção."""
    await redis.delete("chave-que-nao-existe")  # Não deve lançar erro


@pytest.mark.unit
@pytest.mark.asyncio
async def test_increment_with_ttl_incrementa_corretamente(redis):
    """increment_with_ttl incrementa de 1 em 1."""
    resultado1 = await redis.increment_with_ttl("contador")
    resultado2 = await redis.increment_with_ttl("contador")
    resultado3 = await redis.increment_with_ttl("contador")

    assert resultado1 == 1
    assert resultado2 == 2
    assert resultado3 == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_increment_with_ttl_valor_persistido(redis):
    """Valor após increment_with_ttl é acessível via get."""
    await redis.increment_with_ttl("contador")
    await redis.increment_with_ttl("contador")
    await redis.increment_with_ttl("contador")

    valor = await redis.get("contador")
    assert valor == "3"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_sobrescreve_valor_existente(redis):
    """set sobrescreve valor já existente."""
    await redis.set("chave", "valor-original")
    await redis.set("chave", "valor-novo")
    resultado = await redis.get("chave")
    assert resultado == "valor-novo"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_nao_levanta_erro(redis):
    """close() não levanta exceção."""
    await redis.close()  # Deve ser no-op sem erros
