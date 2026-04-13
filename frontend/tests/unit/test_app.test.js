/**
 * Testes unitários para app.js
 *
 * Cobre funções puras, funções DOM e funções de API do frontend.
 * Usa helpers centralizados de dom-mock, fetch-mock e clipboard-mock.
 *
 * NOTA IMPORTANTE sobre a arquitetura de testes:
 * O app.js captura referências DOM em variáveis de nível de módulo no momento
 * do import. Por isso, o setupDOM() deve ser chamado UMA VEZ antes do import
 * do módulo, e o DOM não pode ser destruído entre testes que usam as funções
 * DOM do módulo (pois as referências ficam inválidas após teardownDOM).
 *
 * Estratégia adotada:
 * - setupDOM() é chamado uma vez no início do arquivo (antes de qualquer import)
 * - O módulo app.js é importado uma única vez no topo
 * - Cada suite de testes DOM usa beforeEach/afterEach para resetar APENAS o
 *   innerHTML dos elementos relevantes, sem destruir o DOM inteiro
 */

import { setupDOM, teardownDOM } from './helpers/dom-mock.js';
import { mockFetch, restoreFetch } from './helpers/fetch-mock.js';
import { mockClipboard } from './helpers/clipboard-mock.js';

// Silenciar console.error nos testes
const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

// ————————————————————————————————————————————————————
// Setup global: DOM deve existir ANTES do import do módulo
// O módulo captura referências DOM em variáveis de nível de módulo
// ————————————————————————————————————————————————————
setupDOM();

// Importar o módulo após setup do DOM para que as refs sejam resolvidas corretamente
const {
  isValidUrl,
  setLoading,
  showFieldError,
  showBannerError,
  clearErrors,
  showResult,
  shortenUrl,
  truncateUrl,
  copyWithFeedback,
  renderLinks,
  loadLinks,
} = await import('../../scripts/app.js');

// ————————————————————————————————————————————————————
// Helpers de reset de estado DOM entre testes
// ————————————————————————————————————————————————————

/**
 * Reseta o estado dos elementos DOM para o estado inicial (sem erros, sem loading).
 * Chamado no afterEach de cada suite que modifica o DOM.
 */
function resetDOMState() {
  // Reset input
  const urlInput = document.getElementById('url-input');
  if (urlInput) {
    urlInput.value = '';
    urlInput.removeAttribute('aria-invalid');
  }

  // Reset url-error
  const urlError = document.getElementById('url-error');
  if (urlError) {
    urlError.hidden = true;
    urlError.textContent = '';
  }

  // Reset error-banner
  const errorBanner = document.getElementById('error-banner');
  if (errorBanner) {
    errorBanner.hidden = true;
    errorBanner.textContent = '';
  }

  // Reset result-section
  const resultSection = document.getElementById('result-section');
  if (resultSection) {
    resultSection.hidden = true;
  }

  // Reset short-url-display
  const shortUrlDisplay = document.getElementById('short-url-display');
  if (shortUrlDisplay) {
    shortUrlDisplay.textContent = '';
    shortUrlDisplay.href = '#';
  }

  // Reset copy-btn
  const copyBtn = document.getElementById('copy-btn');
  if (copyBtn) {
    copyBtn.textContent = 'Copiar';
    copyBtn.classList.remove('copied');
  }

  // Reset shorten-btn
  const shortenBtn = document.getElementById('shorten-btn');
  if (shortenBtn) {
    shortenBtn.disabled = false;
    shortenBtn.textContent = 'Encurtar';
  }

  // Reset links-panel
  const linksPanel = document.getElementById('links-panel');
  if (linksPanel) {
    linksPanel.hidden = true;
  }

  // Reset empty-state
  const emptyState = document.getElementById('empty-state');
  if (emptyState) {
    emptyState.classList.add('hidden');
  }

  // Reset links-table-wrapper
  const tableWrapper = document.getElementById('links-table-wrapper');
  if (tableWrapper) {
    tableWrapper.classList.add('hidden');
  }

  // Reset links-tbody
  const tbody = document.getElementById('links-tbody');
  if (tbody) {
    tbody.innerHTML = '';
  }
}

// ————————————————————————————————————————————————————
// Testes de isValidUrl (função pura, sem DOM)
// ————————————————————————————————————————————————————

describe('isValidUrl()', () => {
  it('retorna true para URL válida com http', () => {
    expect(isValidUrl('http://exemplo.com')).toBe(true);
  });

  it('retorna true para URL válida com https', () => {
    expect(isValidUrl('https://exemplo.com/pagina')).toBe(true);
  });

  it('retorna true para URL com path e query', () => {
    expect(isValidUrl('https://www.exemplo.com/artigo?q=teste')).toBe(true);
  });

  it('retorna false para URL sem protocolo', () => {
    expect(isValidUrl('exemplo.com')).toBe(false);
  });

  it('retorna false para string vazia', () => {
    expect(isValidUrl('')).toBe(false);
  });

  it('retorna false para texto simples', () => {
    expect(isValidUrl('isso nao e uma url')).toBe(false);
  });

  it('retorna false para ftp://', () => {
    expect(isValidUrl('ftp://arquivo.com')).toBe(false);
  });
});

// ————————————————————————————————————————————————————
// Testes de setLoading (função DOM)
// ————————————————————————————————————————————————————

describe('setLoading()', () => {
  afterEach(() => {
    resetDOMState();
  });

  it('desabilita o botão quando isLoading=true', () => {
    setLoading(true);
    const btn = document.getElementById('shorten-btn');
    expect(btn.disabled).toBe(true);
  });

  it('altera o texto do botão para "Encurtando..." quando isLoading=true', () => {
    setLoading(true);
    const btn = document.getElementById('shorten-btn');
    expect(btn.textContent).toBe('Encurtando...');
  });

  it('habilita o botão quando isLoading=false', () => {
    setLoading(true);
    setLoading(false);
    const btn = document.getElementById('shorten-btn');
    expect(btn.disabled).toBe(false);
  });

  it('restaura o texto do botão para "Encurtar" quando isLoading=false', () => {
    setLoading(true);
    setLoading(false);
    const btn = document.getElementById('shorten-btn');
    expect(btn.textContent).toBe('Encurtar');
  });
});

// ————————————————————————————————————————————————————
// Testes de showFieldError (função DOM)
// ————————————————————————————————————————————————————

describe('showFieldError()', () => {
  afterEach(() => {
    resetDOMState();
  });

  it('define o texto do erro no elemento url-error', () => {
    showFieldError('URL inválida');
    const errorEl = document.getElementById('url-error');
    expect(errorEl.textContent).toBe('URL inválida');
  });

  it('torna o elemento url-error visível', () => {
    showFieldError('URL inválida');
    const errorEl = document.getElementById('url-error');
    expect(errorEl.hidden).toBe(false);
  });

  it('define aria-invalid="true" no input', () => {
    showFieldError('URL inválida');
    const input = document.getElementById('url-input');
    expect(input.getAttribute('aria-invalid')).toBe('true');
  });
});

// ————————————————————————————————————————————————————
// Testes de showBannerError (função DOM)
// ————————————————————————————————————————————————————

describe('showBannerError()', () => {
  afterEach(() => {
    resetDOMState();
  });

  it('define o texto do banner de erro', () => {
    showBannerError('Erro de conexão');
    const banner = document.getElementById('error-banner');
    expect(banner.textContent).toBe('Erro de conexão');
  });

  it('torna o banner de erro visível', () => {
    showBannerError('Erro de conexão');
    const banner = document.getElementById('error-banner');
    expect(banner.hidden).toBe(false);
  });
});

// ————————————————————————————————————————————————————
// Testes de clearErrors (função DOM)
// ————————————————————————————————————————————————————

describe('clearErrors()', () => {
  afterEach(() => {
    resetDOMState();
  });

  it('esconde o url-error após showFieldError', () => {
    showFieldError('Erro de campo');
    clearErrors();
    const errorEl = document.getElementById('url-error');
    expect(errorEl.hidden).toBe(true);
  });

  it('limpa o texto do url-error', () => {
    showFieldError('Erro de campo');
    clearErrors();
    const errorEl = document.getElementById('url-error');
    expect(errorEl.textContent).toBe('');
  });

  it('remove aria-invalid do input', () => {
    showFieldError('Erro de campo');
    clearErrors();
    const input = document.getElementById('url-input');
    expect(input.getAttribute('aria-invalid')).toBeNull();
  });

  it('esconde o banner de erro após showBannerError', () => {
    showBannerError('Erro no banner');
    clearErrors();
    const banner = document.getElementById('error-banner');
    expect(banner.hidden).toBe(true);
  });

  it('limpa o texto do banner de erro', () => {
    showBannerError('Erro no banner');
    clearErrors();
    const banner = document.getElementById('error-banner');
    expect(banner.textContent).toBe('');
  });
});

// ————————————————————————————————————————————————————
// Testes de showResult (função DOM)
// ————————————————————————————————————————————————————

describe('showResult()', () => {
  afterEach(() => {
    resetDOMState();
  });

  it('define o texto da URL encurtada', () => {
    showResult('http://short.ly/abc123');
    const display = document.getElementById('short-url-display');
    expect(display.textContent).toBe('http://short.ly/abc123');
  });

  it('define o href da URL encurtada', () => {
    showResult('http://short.ly/abc123');
    const display = document.getElementById('short-url-display');
    expect(display.href).toBe('http://short.ly/abc123');
  });

  it('torna a seção de resultado visível', () => {
    showResult('http://short.ly/abc123');
    const section = document.getElementById('result-section');
    expect(section.hidden).toBe(false);
  });
});

// ————————————————————————————————————————————————————
// Testes de shortenUrl (função de API)
// ————————————————————————————————————————————————————

describe('shortenUrl()', () => {
  afterEach(() => {
    restoreFetch();
  });

  it('retorna sucesso com short_url quando status 201', async () => {
    mockFetch(201, { short_url: 'http://short.ly/aB12x' });
    const result = await shortenUrl('https://exemplo.com/pagina-longa');
    expect(result.success).toBe(true);
    expect(result.shortUrl).toBe('http://short.ly/aB12x');
  });

  it('retorna erro de validação quando status 422', async () => {
    mockFetch(422, { detail: 'URL inválida' });
    const result = await shortenUrl('nao-e-url');
    expect(result.success).toBe(false);
    expect(result.type).toBe('validation');
    expect(result.message).toBeTruthy();
  });

  it('retorna erro de rate limit quando status 429', async () => {
    mockFetch(429, { detail: 'Too Many Requests' });
    const result = await shortenUrl('https://exemplo.com');
    expect(result.success).toBe(false);
    expect(result.type).toBe('rate_limit');
    expect(result.message).toBeTruthy();
  });

  it('retorna erro genérico para outros status', async () => {
    mockFetch(500, { detail: 'Internal Server Error' });
    const result = await shortenUrl('https://exemplo.com');
    expect(result.success).toBe(false);
    expect(result.type).toBe('generic');
    expect(result.message).toBeTruthy();
  });

  it('chama fetch com o endpoint correto', async () => {
    const spy = mockFetch(201, { short_url: 'http://short.ly/x' });
    await shortenUrl('https://exemplo.com');
    expect(spy).toHaveBeenCalledWith(
      expect.stringContaining('/api/shorten'),
      expect.objectContaining({ method: 'POST' })
    );
  });
});

// ————————————————————————————————————————————————————
// Testes de truncateUrl (função pura)
// ————————————————————————————————————————————————————

describe('truncateUrl()', () => {
  it('retorna a URL sem alteração se for menor que maxLength', () => {
    const url = 'https://curta.com';
    expect(truncateUrl(url, 50)).toBe(url);
  });

  it('retorna a URL sem alteração se for igual a maxLength', () => {
    const url = 'https://exemplo.com/1234'; // 24 chars
    expect(truncateUrl(url, 24)).toBe(url);
  });

  it('trunca a URL adicionando "..." se for maior que maxLength', () => {
    const url = 'https://exemplo.com/pagina-bem-longa-com-muitos-caracteres';
    const result = truncateUrl(url, 20);
    expect(result.length).toBe(23); // 20 + '...'
    expect(result.endsWith('...')).toBe(true);
  });
});

// ————————————————————————————————————————————————————
// Testes de copyWithFeedback (função DOM/Async)
// ————————————————————————————————————————————————————

describe('copyWithFeedback()', () => {
  afterEach(() => {
    resetDOMState();
    vi.restoreAllMocks();
  });

  it('copia o texto para o clipboard', async () => {
    const writeTextSpy = mockClipboard();
    const btn = document.createElement('button');
    btn.textContent = 'Copiar';

    await copyWithFeedback(btn, 'http://short.ly/test');
    expect(writeTextSpy).toHaveBeenCalledWith('http://short.ly/test');
  });

  it('altera o texto do botão para "Copiado! ✓" após cópia bem-sucedida', async () => {
    mockClipboard();
    const btn = document.createElement('button');
    btn.textContent = 'Copiar';

    await copyWithFeedback(btn, 'http://short.ly/test');
    expect(btn.textContent).toBe('Copiado! ✓');
  });

  it('adiciona classe "copied" ao botão após cópia bem-sucedida', async () => {
    mockClipboard();
    const btn = document.createElement('button');

    await copyWithFeedback(btn, 'http://short.ly/test');
    expect(btn.classList.contains('copied')).toBe(true);
  });

  it('exibe fallback quando clipboard não está disponível', async () => {
    // Substituir clipboard.writeText por um que rejeita
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: vi.fn().mockRejectedValue(new Error('Clipboard não disponível')),
      },
      writable: true,
      configurable: true,
    });

    const btn = document.createElement('button');
    btn.textContent = 'Copiar';

    await copyWithFeedback(btn, 'http://short.ly/test');
    expect(btn.textContent).toBe('Copie manualmente');
  });
});

// ————————————————————————————————————————————————————
// Testes de loadLinks (função API/Cache)
// ————————————————————————————————————————————————————

describe('loadLinks()', () => {
  beforeEach(() => {
    // Limpar sessionStorage antes de cada teste
    sessionStorage.clear();
  });

  afterEach(() => {
    restoreFetch();
    resetDOMState();
    sessionStorage.clear();
  });

  it('usa cache do sessionStorage quando disponível', async () => {
    const cachedLinks = [
      {
        short_code: 'abc',
        original_url: 'https://exemplo.com',
        short_url: 'http://short.ly/abc',
        click_count: 1,
      },
    ];
    sessionStorage.setItem('linksCache', JSON.stringify(cachedLinks));

    const fetchSpy = mockFetch(200, {});
    await loadLinks();

    // Não deve chamar fetch quando há cache
    expect(fetchSpy).not.toHaveBeenCalled();

    // Deve renderizar os links do cache
    const tbody = document.getElementById('links-tbody');
    expect(tbody.children.length).toBe(1);
  });

  it('faz GET /api/links quando não há cache', async () => {
    const spy = mockFetch(200, { links: [] });
    await loadLinks();

    expect(spy).toHaveBeenCalledWith(
      expect.stringContaining('/api/links'),
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('renderiza links da API quando status ok', async () => {
    const links = [
      {
        short_code: 'xyz',
        original_url: 'https://outro.com',
        short_url: 'http://short.ly/xyz',
        click_count: 3,
      },
    ];
    mockFetch(200, { links });

    await loadLinks();

    const panel = document.getElementById('links-panel');
    expect(panel.hidden).toBe(false);
    const tbody = document.getElementById('links-tbody');
    expect(tbody.children.length).toBe(1);
  });

  it('renderiza estado vazio quando API retorna erro', async () => {
    mockFetch(500, {});
    await loadLinks();

    const emptyState = document.getElementById('empty-state');
    expect(emptyState.classList.contains('hidden')).toBe(false);
  });

  it('renderiza estado vazio quando fetch falha com exceção', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

    await loadLinks();

    const emptyState = document.getElementById('empty-state');
    expect(emptyState.classList.contains('hidden')).toBe(false);
  });

  it('salva links no sessionStorage após chamada bem-sucedida à API', async () => {
    const links = [
      {
        short_code: 'abc',
        original_url: 'https://exemplo.com',
        short_url: 'http://short.ly/abc',
        click_count: 0,
      },
    ];
    mockFetch(200, { links });

    await loadLinks();

    const cached = JSON.parse(sessionStorage.getItem('linksCache'));
    expect(cached).toEqual(links);
  });
});

// ————————————————————————————————————————————————————
// Testes de renderLinks (função DOM)
// ————————————————————————————————————————————————————

describe('renderLinks()', () => {
  afterEach(() => {
    resetDOMState();
  });

  it('torna o links-panel visível', () => {
    renderLinks([]);
    const panel = document.getElementById('links-panel');
    expect(panel.hidden).toBe(false);
  });

  it('exibe empty-state quando lista está vazia', () => {
    renderLinks([]);
    const emptyState = document.getElementById('empty-state');
    expect(emptyState.classList.contains('hidden')).toBe(false);
  });

  it('esconde links-table-wrapper quando lista está vazia', () => {
    renderLinks([]);
    const tableWrapper = document.getElementById('links-table-wrapper');
    expect(tableWrapper.classList.contains('hidden')).toBe(true);
  });

  it('exibe a tabela quando há links', () => {
    renderLinks([
      {
        short_code: 'abc123',
        original_url: 'https://exemplo.com',
        short_url: 'http://short.ly/abc123',
        click_count: 5,
      },
    ]);
    const tableWrapper = document.getElementById('links-table-wrapper');
    expect(tableWrapper.classList.contains('hidden')).toBe(false);
  });

  it('esconde empty-state quando há links', () => {
    renderLinks([
      {
        short_code: 'abc123',
        original_url: 'https://exemplo.com',
        short_url: 'http://short.ly/abc123',
        click_count: 5,
      },
    ]);
    const emptyState = document.getElementById('empty-state');
    expect(emptyState.classList.contains('hidden')).toBe(true);
  });

  it('renderiza o número correto de linhas na tabela', () => {
    renderLinks([
      {
        short_code: 'abc123',
        original_url: 'https://exemplo.com',
        short_url: 'http://short.ly/abc123',
        click_count: 5,
      },
      {
        short_code: 'xyz789',
        original_url: 'https://outro.com',
        short_url: 'http://short.ly/xyz789',
        click_count: 0,
      },
    ]);
    const tbody = document.getElementById('links-tbody');
    expect(tbody.children.length).toBe(2);
  });

  it('exibe a contagem de cliques corretamente', () => {
    renderLinks([
      {
        short_code: 'abc123',
        original_url: 'https://exemplo.com',
        short_url: 'http://short.ly/abc123',
        click_count: 42,
      },
    ]);
    const tbody = document.getElementById('links-tbody');
    const row = tbody.children[0];
    expect(row.textContent).toContain('42');
  });

  it('trata null como lista vazia', () => {
    renderLinks(null);
    const emptyState = document.getElementById('empty-state');
    expect(emptyState.classList.contains('hidden')).toBe(false);
  });
});
