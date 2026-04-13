/**
 * Helper para mockar navigator.clipboard nos testes.
 *
 * Substitui navigator.clipboard.writeText por um vi.fn() que resolve imediatamente.
 */

/**
 * Substitui navigator.clipboard.writeText por um vi.fn() que resolve imediatamente.
 * @returns {import('vitest').MockInstance} - O spy criado
 */
export function mockClipboard() {
  const writeTextSpy = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: writeTextSpy },
    writable: true,
    configurable: true,
  });
  return writeTextSpy;
}
