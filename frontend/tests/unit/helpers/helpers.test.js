/**
 * Testes de smoke para os helpers de test setup.
 * Valida que os helpers de mock funcionam corretamente.
 */

import { setupDOM, teardownDOM } from './dom-mock.js';
import { mockFetch, restoreFetch } from './fetch-mock.js';
import { mockClipboard } from './clipboard-mock.js';

describe('setupDOM()', () => {
  beforeEach(() => {
    setupDOM();
  });

  afterEach(() => {
    teardownDOM();
  });

  it('configura o elemento #shorten-form', () => {
    expect(document.getElementById('shorten-form')).not.toBeNull();
  });

  it('configura o elemento #url-input', () => {
    expect(document.getElementById('url-input')).not.toBeNull();
  });

  it('configura o elemento #url-error', () => {
    expect(document.getElementById('url-error')).not.toBeNull();
  });

  it('configura o elemento #shorten-btn', () => {
    expect(document.getElementById('shorten-btn')).not.toBeNull();
  });

  it('configura o elemento #error-banner', () => {
    expect(document.getElementById('error-banner')).not.toBeNull();
  });

  it('configura o elemento #result-section', () => {
    expect(document.getElementById('result-section')).not.toBeNull();
  });

  it('configura o elemento #short-url-display', () => {
    expect(document.getElementById('short-url-display')).not.toBeNull();
  });

  it('configura o elemento #copy-btn', () => {
    expect(document.getElementById('copy-btn')).not.toBeNull();
  });

  it('configura o elemento #links-panel', () => {
    expect(document.getElementById('links-panel')).not.toBeNull();
  });

  it('configura o elemento #empty-state', () => {
    expect(document.getElementById('empty-state')).not.toBeNull();
  });

  it('configura o elemento #links-table-wrapper', () => {
    expect(document.getElementById('links-table-wrapper')).not.toBeNull();
  });

  it('configura o elemento #links-tbody', () => {
    expect(document.getElementById('links-tbody')).not.toBeNull();
  });
});

describe('teardownDOM()', () => {
  it('limpa o document.body após os testes', () => {
    setupDOM();
    expect(document.getElementById('shorten-form')).not.toBeNull();

    teardownDOM();
    expect(document.getElementById('shorten-form')).toBeNull();
  });
});

describe('mockFetch()', () => {
  afterEach(() => {
    restoreFetch();
  });

  it('substitui globalThis.fetch por um vi.fn()', () => {
    const spy = mockFetch(201, { short_url: 'http://short.ly/aB12x' });
    expect(globalThis.fetch).toBe(spy);
    expect(vi.isMockFunction(globalThis.fetch)).toBe(true);
  });

  it('retorna resposta com status configurado', async () => {
    mockFetch(201, { short_url: 'http://short.ly/aB12x' });
    const response = await globalThis.fetch('http://example.com');
    expect(response.status).toBe(201);
  });

  it('retorna ok=true para status 2xx', async () => {
    mockFetch(201, {});
    const response = await globalThis.fetch('http://example.com');
    expect(response.ok).toBe(true);
  });

  it('retorna ok=false para status 4xx', async () => {
    mockFetch(404, {});
    const response = await globalThis.fetch('http://example.com');
    expect(response.ok).toBe(false);
  });

  it('retorna body via response.json()', async () => {
    const body = { short_url: 'http://short.ly/aB12x' };
    mockFetch(201, body);
    const response = await globalThis.fetch('http://example.com');
    const data = await response.json();
    expect(data).toEqual(body);
  });
});

describe('mockClipboard()', () => {
  it('substitui navigator.clipboard.writeText por vi.fn()', () => {
    const spy = mockClipboard();
    expect(vi.isMockFunction(navigator.clipboard.writeText)).toBe(true);
    expect(navigator.clipboard.writeText).toBe(spy);
  });

  it('resolve Promise sem erro ao ser chamado', async () => {
    mockClipboard();
    await expect(navigator.clipboard.writeText('texto')).resolves.toBeUndefined();
  });

  it('registra os argumentos passados', async () => {
    const spy = mockClipboard();
    await navigator.clipboard.writeText('url-copiada');
    expect(spy).toHaveBeenCalledWith('url-copiada');
  });
});
