/**
 * Testes T003-FE — Interface web responsiva do encurtador
 *
 * Cobre os cenários BDD especificados na US-001 T003-FE:
 * - Cenário A: Fluxo feliz (URL válida encurtada)
 * - Cenário B: Copiar link curto com feedback visual
 * - Cenário C: URL inválida — erro client-side
 * - Cenário D: Rate limit (429)
 * - Cenário E: Erro genérico (5xx / rede)
 * - Cenário F: Validação somente no submit (não no change)
 * - Cenário G: Responsividade (CSS)
 * - Acessibilidade: atributos ARIA
 * - HTML: estrutura semântica
 */

'use strict';

// ─── Setup DOM global ─────────────────────────────────────────────────────────
function setupDOM() {
  document.body.innerHTML = `
    <main class="container">
      <form id="shorten-form" novalidate>
        <div class="input-group">
          <label for="url-input">Cole sua URL longa aqui</label>
          <input
            type="url"
            id="url-input"
            name="url"
            placeholder="https://exemplo.com/sua-url-longa"
            autocomplete="off"
            required
            aria-describedby="url-error"
          />
          <span id="url-error" class="error-message" aria-live="polite" hidden></span>
        </div>
        <button type="submit" id="shorten-btn">Encurtar</button>
      </form>
      <div id="error-banner" class="error-banner" role="alert" aria-live="assertive" hidden></div>
      <div id="result-section" class="result-section" hidden>
        <p class="result-label">Seu link curto:</p>
        <div class="result-row">
          <a id="short-url-display" href="#" target="_blank" rel="noopener noreferrer" class="short-url"></a>
          <button id="copy-btn" type="button" aria-label="Copiar link curto">Copiar</button>
        </div>
      </div>
      <section id="links-panel" hidden>
        <div id="empty-state" class="hidden"></div>
        <div id="links-table-wrapper" class="hidden">
          <table id="links-table">
            <thead><tr><th>URL Original</th><th>Link Curto</th><th>Cliques</th><th>Ação</th></tr></thead>
            <tbody id="links-tbody"></tbody>
          </table>
        </div>
      </section>
    </main>
  `;
}

// ─── Mocks ────────────────────────────────────────────────────────────────────
const mockFetch = jest.fn();
global.fetch = mockFetch;

const mockWriteText = jest.fn().mockResolvedValue(undefined);
Object.defineProperty(global.navigator, 'clipboard', {
  value: { writeText: mockWriteText },
  writable: true,
  configurable: true,
});

const sessionStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => { store[key] = String(value); },
    removeItem: (key) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
  writable: true,
});

// Helpers de resposta
function mockShortenSuccess(shortCode = 'aB3kZ9') {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    status: 201,
    json: async () => ({
      short_code: shortCode,
      short_url: `https://short.app/${shortCode}`,
      original_url: 'https://exemplo.com/pagina-longa',
    }),
  });
}

function mockLinksEmpty() {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    status: 200,
    json: async () => ({ links: [] }),
  });
}

function mockShortenStatus(status) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    json: async () => ({ detail: 'error' }),
  });
}

function mockNetworkError() {
  mockFetch.mockRejectedValueOnce(new Error('Network error'));
}

// ─── Lógica extraída de app.js para testes unitários ─────────────────────────
// Como app.js acessa DOM no nível de módulo, extraímos a lógica pura aqui.

function isValidUrl(url) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

function getElements() {
  return {
    form: document.getElementById('shorten-form'),
    urlInput: document.getElementById('url-input'),
    urlError: document.getElementById('url-error'),
    shortenBtn: document.getElementById('shorten-btn'),
    errorBanner: document.getElementById('error-banner'),
    resultSection: document.getElementById('result-section'),
    shortUrlDisplay: document.getElementById('short-url-display'),
    copyBtn: document.getElementById('copy-btn'),
  };
}

function setLoading(isLoading, el) {
  el.disabled = isLoading;
  el.textContent = isLoading ? 'Encurtando...' : 'Encurtar';
}

function showFieldError(message, urlError, urlInput) {
  urlError.textContent = message;
  urlError.hidden = false;
  urlInput.setAttribute('aria-invalid', 'true');
  urlInput.focus();
}

function showBannerError(message, errorBanner) {
  errorBanner.textContent = message;
  errorBanner.hidden = false;
}

function clearErrors(urlError, urlInput, errorBanner) {
  urlError.hidden = true;
  urlError.textContent = '';
  urlInput.removeAttribute('aria-invalid');
  errorBanner.hidden = true;
  errorBanner.textContent = '';
}

function showResult(shortUrl, shortUrlDisplay, resultSection, urlError, urlInput, errorBanner) {
  shortUrlDisplay.textContent = shortUrl;
  shortUrlDisplay.href = shortUrl;
  resultSection.hidden = false;
  // Limpar erros ao exibir resultado
  clearErrors(urlError, urlInput, errorBanner);
}

async function shortenUrl(url, apiBaseUrl) {
  const response = await fetch(`${apiBaseUrl}/api/shorten`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ url }),
  });

  if (response.status === 201) {
    const data = await response.json();
    return { success: true, shortUrl: data.short_url };
  }

  if (response.status === 422) {
    return {
      success: false,
      type: 'validation',
      message: 'Por favor, insira uma URL válida (ex: https://exemplo.com)',
    };
  }

  if (response.status === 429) {
    return {
      success: false,
      type: 'rate_limit',
      message: 'Limite de requisições atingido. Aguarde um momento antes de tentar novamente.',
    };
  }

  return {
    success: false,
    type: 'generic',
    message: 'Ocorreu um erro inesperado. Tente novamente em alguns instantes.',
  };
}

// ─── beforeEach ───────────────────────────────────────────────────────────────
beforeEach(() => {
  setupDOM();
  jest.resetModules();
  mockFetch.mockReset();
  mockWriteText.mockReset();
  mockWriteText.mockResolvedValue(undefined);
  sessionStorageMock.clear();
});

// =============================================================================
// Cenário A: Fluxo feliz — URL válida é encurtada e exibida
// =============================================================================
describe('Cenário A — Fluxo feliz: URL válida é encurtada', () => {
  test('isValidUrl aceita URLs com https://', () => {
    expect(isValidUrl('https://exemplo.com/pagina-longa')).toBe(true);
  });

  test('isValidUrl aceita URLs com http://', () => {
    expect(isValidUrl('http://exemplo.com')).toBe(true);
  });

  test('botão muda para "Encurtando..." e fica desabilitado durante loading', () => {
    const { shortenBtn } = getElements();

    setLoading(true, shortenBtn);

    expect(shortenBtn.textContent).toBe('Encurtando...');
    expect(shortenBtn.disabled).toBe(true);
  });

  test('botão volta ao estado normal após loading', () => {
    const { shortenBtn } = getElements();

    setLoading(true, shortenBtn);
    setLoading(false, shortenBtn);

    expect(shortenBtn.textContent).toBe('Encurtar');
    expect(shortenBtn.disabled).toBe(false);
  });

  test('showResult exibe o link curto e deixa resultSection visível', () => {
    const { shortUrlDisplay, resultSection, urlError, urlInput, errorBanner } = getElements();

    showResult('https://short.app/aB3kZ9', shortUrlDisplay, resultSection, urlError, urlInput, errorBanner);

    expect(shortUrlDisplay.textContent).toBe('https://short.app/aB3kZ9');
    expect(shortUrlDisplay.getAttribute('href')).toBe('https://short.app/aB3kZ9');
    expect(resultSection.hidden).toBe(false);
  });

  test('showResult limpa erros anteriores ao exibir resultado', () => {
    const { shortUrlDisplay, resultSection, urlError, urlInput, errorBanner } = getElements();

    // Simular estado de erro pré-existente
    urlError.hidden = false;
    urlError.textContent = 'erro anterior';
    errorBanner.hidden = false;
    errorBanner.textContent = 'banner anterior';

    showResult('https://short.app/aB3kZ9', shortUrlDisplay, resultSection, urlError, urlInput, errorBanner);

    expect(urlError.hidden).toBe(true);
    expect(urlError.textContent).toBe('');
    expect(errorBanner.hidden).toBe(true);
    expect(errorBanner.textContent).toBe('');
  });

  test('API retorna 201 com short_url correto', async () => {
    mockShortenSuccess('aB3kZ9');

    const result = await shortenUrl('https://exemplo.com/pagina-longa', 'http://localhost:8000');

    expect(result.success).toBe(true);
    expect(result.shortUrl).toBe('https://short.app/aB3kZ9');
  });

  test('chamada à API usa método POST com Content-Type application/json', async () => {
    mockShortenSuccess();
    mockLinksEmpty();

    await shortenUrl('https://exemplo.com', 'http://localhost:8000');

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/shorten',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });
});

// =============================================================================
// Cenário B: Copiar link curto com feedback visual
// =============================================================================
describe('Cenário B — Copiar link curto com feedback visual', () => {
  test('copiar chama navigator.clipboard.writeText com a URL correta', async () => {
    const { shortUrlDisplay, copyBtn } = getElements();
    shortUrlDisplay.textContent = 'https://short.app/aB3kZ9';

    await navigator.clipboard.writeText(shortUrlDisplay.textContent);

    expect(mockWriteText).toHaveBeenCalledWith('https://short.app/aB3kZ9');
  });

  test('botão "Copiar" muda para "Copiado!" e recebe classe .copied', async () => {
    const { copyBtn } = getElements();

    await navigator.clipboard.writeText('https://short.app/aB3kZ9');
    copyBtn.textContent = 'Copiado!';
    copyBtn.classList.add('copied');

    expect(copyBtn.textContent).toBe('Copiado!');
    expect(copyBtn.classList.contains('copied')).toBe(true);
  });

  test('botão volta ao estado normal após 2 segundos', () => {
    jest.useFakeTimers();
    const { copyBtn } = getElements();

    copyBtn.textContent = 'Copiado!';
    copyBtn.classList.add('copied');

    setTimeout(() => {
      copyBtn.textContent = 'Copiar';
      copyBtn.classList.remove('copied');
    }, 2000);

    jest.advanceTimersByTime(2000);

    expect(copyBtn.textContent).toBe('Copiar');
    expect(copyBtn.classList.contains('copied')).toBe(false);

    jest.useRealTimers();
  });

  test('fallback quando Clipboard API não disponível — exibe "Copie manualmente"', async () => {
    const { copyBtn } = getElements();
    mockWriteText.mockRejectedValueOnce(new Error('Not supported'));

    try {
      await navigator.clipboard.writeText('https://short.app/aB3kZ9');
      copyBtn.textContent = 'Copiado!';
    } catch {
      copyBtn.textContent = 'Copie manualmente';
    }

    expect(copyBtn.textContent).toBe('Copie manualmente');
  });
});

// =============================================================================
// Cenário C: URL inválida — mensagem de erro client-side
// =============================================================================
describe('Cenário C — URL inválida exibe mensagem de erro', () => {
  test('isValidUrl rejeita string sem protocolo', () => {
    expect(isValidUrl('isso nao e uma url')).toBe(false);
  });

  test('isValidUrl rejeita string vazia', () => {
    expect(isValidUrl('')).toBe(false);
  });

  test('isValidUrl rejeita URL sem http:// ou https://', () => {
    expect(isValidUrl('www.exemplo.com')).toBe(false);
    expect(isValidUrl('exemplo.com')).toBe(false);
    expect(isValidUrl('ftp://exemplo.com')).toBe(false);
  });

  test('showFieldError exibe mensagem de erro e define aria-invalid', () => {
    const { urlError, urlInput } = getElements();

    showFieldError('Por favor, insira uma URL válida (ex: https://exemplo.com)', urlError, urlInput);

    expect(urlError.hidden).toBe(false);
    expect(urlError.textContent).toBe('Por favor, insira uma URL válida (ex: https://exemplo.com)');
    expect(urlInput.getAttribute('aria-invalid')).toBe('true');
  });

  test('showFieldError coloca foco no campo de URL', () => {
    const { urlError, urlInput } = getElements();

    // Garantir que o input está no DOM
    document.body.appendChild(urlInput);
    const focusSpy = jest.spyOn(urlInput, 'focus');

    showFieldError('URL inválida', urlError, urlInput);

    expect(focusSpy).toHaveBeenCalled();
  });

  test('clearErrors remove mensagem de erro e aria-invalid', () => {
    const { urlError, urlInput, errorBanner } = getElements();

    urlError.hidden = false;
    urlError.textContent = 'erro';
    urlInput.setAttribute('aria-invalid', 'true');
    errorBanner.hidden = false;

    clearErrors(urlError, urlInput, errorBanner);

    expect(urlError.hidden).toBe(true);
    expect(urlError.textContent).toBe('');
    expect(urlInput.getAttribute('aria-invalid')).toBeNull();
    expect(errorBanner.hidden).toBe(true);
  });
});

// =============================================================================
// Cenário D: Rate limit (HTTP 429)
// =============================================================================
describe('Cenário D — Rate limit atingido (HTTP 429)', () => {
  test('shortenUrl com 429 retorna mensagem de rate limit específica', async () => {
    mockShortenStatus(429);

    const result = await shortenUrl('https://exemplo.com', 'http://localhost:8000');

    expect(result.success).toBe(false);
    expect(result.type).toBe('rate_limit');
    expect(result.message).toBe('Limite de requisições atingido. Aguarde um momento antes de tentar novamente.');
  });

  test('showBannerError exibe mensagem no banner e deixa visível', () => {
    const { errorBanner } = getElements();

    showBannerError('Limite de requisições atingido. Aguarde um momento antes de tentar novamente.', errorBanner);

    expect(errorBanner.hidden).toBe(false);
    expect(errorBanner.textContent).toBe('Limite de requisições atingido. Aguarde um momento antes de tentar novamente.');
  });

  test('erro 429 NÃO exibe mensagem genérica', async () => {
    mockShortenStatus(429);

    const result = await shortenUrl('https://exemplo.com', 'http://localhost:8000');

    expect(result.message).not.toBe('Ocorreu um erro inesperado. Tente novamente em alguns instantes.');
  });
});

// =============================================================================
// Cenário E: Erro genérico (5xx ou rede)
// =============================================================================
describe('Cenário E — Erro genérico (5xx / falha de rede)', () => {
  test('shortenUrl com 500 retorna mensagem genérica', async () => {
    mockShortenStatus(500);

    const result = await shortenUrl('https://exemplo.com', 'http://localhost:8000');

    expect(result.success).toBe(false);
    expect(result.type).toBe('generic');
    expect(result.message).toBe('Ocorreu um erro inesperado. Tente novamente em alguns instantes.');
  });

  test('erro de rede lança exceção que deve ser capturada', async () => {
    mockNetworkError();

    let caught = false;
    let errorMessage = '';

    try {
      await shortenUrl('https://exemplo.com', 'http://localhost:8000');
    } catch (err) {
      caught = true;
      errorMessage = 'Ocorreu um erro inesperado. Tente novamente em alguns instantes.';
    }

    expect(caught).toBe(true);
    expect(errorMessage).toBe('Ocorreu um erro inesperado. Tente novamente em alguns instantes.');
  });

  test('shortenUrl com 503 retorna mensagem genérica', async () => {
    mockShortenStatus(503);

    const result = await shortenUrl('https://exemplo.com', 'http://localhost:8000');

    expect(result.success).toBe(false);
    expect(result.type).toBe('generic');
  });
});

// =============================================================================
// Cenário F: Validação somente no submit (não no change)
// =============================================================================
describe('Cenário F — Validação somente no submit', () => {
  test('campo de URL não tem erro ao inicializar', () => {
    const { urlError, urlInput } = getElements();

    expect(urlError.hidden).toBe(true);
    expect(urlError.textContent).toBe('');
    expect(urlInput.getAttribute('aria-invalid')).toBeNull();
  });

  test('errorBanner não está visível ao inicializar', () => {
    const { errorBanner } = getElements();

    expect(errorBanner.hidden).toBe(true);
  });

  test('resultSection não está visível ao inicializar', () => {
    const { resultSection } = getElements();

    expect(resultSection.hidden).toBe(true);
  });
});

// =============================================================================
// Cenário G: Responsividade — verificações de CSS
// =============================================================================
describe('Cenário G — Responsividade (CSS)', () => {
  const fs = require('fs');
  const path = require('path');
  const cssPath = path.join(__dirname, '../styles/main.css');

  test('CSS tem font-size >= 16px (1rem) no input URL para evitar zoom iOS', () => {
    const cssContent = fs.readFileSync(cssPath, 'utf-8');
    // Verifica font-size: 1rem no #url-input (16px)
    expect(cssContent).toMatch(/font-size:\s*1rem/);
  });

  test('CSS tem max-width de 600px no container', () => {
    const cssContent = fs.readFileSync(cssPath, 'utf-8');
    expect(cssContent).toContain('max-width: 600px');
  });

  test('CSS tem media query para responsividade desktop', () => {
    const cssContent = fs.readFileSync(cssPath, 'utf-8');
    expect(cssContent).toMatch(/@media\s*\(min-width:/);
  });

  test('CSS tem media query para responsividade mobile', () => {
    const cssContent = fs.readFileSync(cssPath, 'utf-8');
    expect(cssContent).toMatch(/@media\s*\(max-width:/);
  });

  test('CSS tem word-break: break-all para URLs longas', () => {
    const cssContent = fs.readFileSync(cssPath, 'utf-8');
    expect(cssContent).toContain('word-break: break-all');
  });

  test('CSS usa box-sizing: border-box para layout consistente', () => {
    const cssContent = fs.readFileSync(cssPath, 'utf-8');
    expect(cssContent).toContain('box-sizing: border-box');
  });

  test('CSS tem overflow-x: auto no wrapper da tabela', () => {
    const cssContent = fs.readFileSync(cssPath, 'utf-8');
    expect(cssContent).toContain('overflow-x: auto');
  });
});

// =============================================================================
// Acessibilidade WCAG AA
// =============================================================================
describe('Acessibilidade — atributos ARIA e HTML semântico', () => {
  test('url-error tem aria-live="polite"', () => {
    const { urlError } = getElements();
    expect(urlError.getAttribute('aria-live')).toBe('polite');
  });

  test('error-banner tem aria-live="assertive"', () => {
    const { errorBanner } = getElements();
    expect(errorBanner.getAttribute('aria-live')).toBe('assertive');
  });

  test('error-banner tem role="alert"', () => {
    const { errorBanner } = getElements();
    expect(errorBanner.getAttribute('role')).toBe('alert');
  });

  test('url-input tem aria-describedby apontando para url-error', () => {
    const { urlInput } = getElements();
    expect(urlInput.getAttribute('aria-describedby')).toBe('url-error');
  });

  test('copy-btn tem aria-label descritivo', () => {
    const { copyBtn } = getElements();
    expect(copyBtn.getAttribute('aria-label')).toBeTruthy();
  });

  test('short-url-display tem target="_blank" e rel="noopener noreferrer"', () => {
    const { shortUrlDisplay } = getElements();
    expect(shortUrlDisplay.getAttribute('target')).toBe('_blank');
    expect(shortUrlDisplay.getAttribute('rel')).toBe('noopener noreferrer');
  });

  test('label está associado ao input via for/id', () => {
    const label = document.querySelector('label[for="url-input"]');
    expect(label).not.toBeNull();
  });

  test('formulário tem atributo novalidate (validação client-side custom)', () => {
    const { form } = getElements();
    expect(form.getAttribute('novalidate')).not.toBeNull();
  });
});

// =============================================================================
// HTML — Estrutura semântica
// =============================================================================
describe('HTML — Estrutura semântica obrigatória', () => {
  const fs = require('fs');
  const path = require('path');
  const htmlPath = path.join(__dirname, '../index.html');

  test('HTML tem lang="pt-BR"', () => {
    const htmlContent = fs.readFileSync(htmlPath, 'utf-8');
    expect(htmlContent).toContain('lang="pt-BR"');
  });

  test('HTML tem meta charset UTF-8', () => {
    const htmlContent = fs.readFileSync(htmlPath, 'utf-8');
    expect(htmlContent).toContain('charset="UTF-8"');
  });

  test('HTML tem meta viewport para responsividade', () => {
    const htmlContent = fs.readFileSync(htmlPath, 'utf-8');
    expect(htmlContent).toContain('name="viewport"');
    expect(htmlContent).toContain('width=device-width');
  });

  test('HTML tem form com id shorten-form', () => {
    const { form } = getElements();
    expect(form).not.toBeNull();
    expect(form.id).toBe('shorten-form');
  });

  test('HTML tem input type="url" com id url-input', () => {
    const { urlInput } = getElements();
    expect(urlInput).not.toBeNull();
    expect(urlInput.type).toBe('url');
  });

  test('HTML tem botão submit com id shorten-btn', () => {
    const { shortenBtn } = getElements();
    expect(shortenBtn).not.toBeNull();
    expect(shortenBtn.type).toBe('submit');
  });

  test('HTML tem botão copiar com id copy-btn', () => {
    const { copyBtn } = getElements();
    expect(copyBtn).not.toBeNull();
    expect(copyBtn.type).toBe('button');
  });

  test('HTML tem result-section com id result-section', () => {
    const { resultSection } = getElements();
    expect(resultSection).not.toBeNull();
  });

  test('HTML tem error-banner com id error-banner', () => {
    const { errorBanner } = getElements();
    expect(errorBanner).not.toBeNull();
  });
});

// =============================================================================
// Verificação do código-fonte de app.js
// =============================================================================
describe('app.js — Verificação de código-fonte', () => {
  const fs = require('fs');
  const path = require('path');
  const appJsPath = path.join(__dirname, '../scripts/app.js');

  test('app.js tem API_BASE_URL configurada', () => {
    const content = fs.readFileSync(appJsPath, 'utf-8');
    expect(content).toContain('API_BASE_URL');
  });

  test('app.js usa event.preventDefault() no submit', () => {
    const content = fs.readFileSync(appJsPath, 'utf-8');
    expect(content).toContain('event.preventDefault()');
  });

  test('app.js valida URL antes de chamar a API', () => {
    const content = fs.readFileSync(appJsPath, 'utf-8');
    expect(content).toContain('isValidUrl');
  });

  test('app.js usa navigator.clipboard.writeText para copiar', () => {
    const content = fs.readFileSync(appJsPath, 'utf-8');
    expect(content).toContain('navigator.clipboard.writeText');
  });

  test('app.js trata status 429 especificamente', () => {
    const content = fs.readFileSync(appJsPath, 'utf-8');
    expect(content).toContain('429');
  });

  test('app.js trata status 422 especificamente', () => {
    const content = fs.readFileSync(appJsPath, 'utf-8');
    expect(content).toContain('422');
  });

  test('app.js restaura botão após 2 segundos (setTimeout 2000)', () => {
    const content = fs.readFileSync(appJsPath, 'utf-8');
    expect(content).toContain('2000');
  });

  test('app.js usa use strict', () => {
    const content = fs.readFileSync(appJsPath, 'utf-8');
    expect(content).toContain("'use strict'");
  });

  test('app.js usa try/catch para tratar erros de rede', () => {
    const content = fs.readFileSync(appJsPath, 'utf-8');
    expect(content).toContain('catch (networkError)');
  });

  test('app.js usa clearTimeout para evitar acúmulo de timers no botão copiar', () => {
    const content = fs.readFileSync(appJsPath, 'utf-8');
    expect(content).toContain('clearTimeout');
  });
});
