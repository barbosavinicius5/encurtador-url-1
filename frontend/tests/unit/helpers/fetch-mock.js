/**
 * Helper para mockar globalThis.fetch nos testes.
 *
 * Substitui o fetch global por um vi.fn() que retorna a resposta configurada.
 */

/**
 * Substitui globalThis.fetch por um vi.fn() que retorna a resposta configurada.
 * @param {number} status - HTTP status code
 * @param {object} body - Objeto a ser retornado por response.json()
 * @returns {import('vitest').MockInstance} - O spy criado
 */
export function mockFetch(status, body) {
  const fetchSpy = vi.fn().mockResolvedValue({
    status,
    ok: status >= 200 && status < 400,
    json: vi.fn().mockResolvedValue(body),
  });
  globalThis.fetch = fetchSpy;
  return fetchSpy;
}

/**
 * Restaura fetch para undefined (limpar após testes).
 */
export function restoreFetch() {
  globalThis.fetch = undefined;
}
