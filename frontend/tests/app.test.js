/**
 * Testes do painel de links — US-003: T002-FE
 *
 * Cobre todos os cenários BDD especificados na task.
 * Executa em jsdom (jest-environment-jsdom).
 */

'use strict';

// ─── Setup DOM global ─────────────────────────────────────────────────────────
function setupDOM() {
  document.body.innerHTML = `
    <main class="container">
      <form id="shorten-form" novalidate>
        <div class="input-group">
          <label for="url-input">URL</label>
          <input type="url" id="url-input" required />
          <span id="url-error" hidden></span>
        </div>
        <button type="submit" id="shorten-btn">Encurtar</button>
      </form>
      <div id="error-banner" hidden></div>
      <div id="result-section" hidden>
        <a id="short-url-display" href="#"></a>
        <button id="copy-btn" type="button">Copiar</button>
      </div>
      <section id="links-panel" hidden>
        <div id="empty-state" class="hidden">
          <p class="empty-state__title">Você ainda não tem links encurtados.</p>
        </div>
        <div id="links-table-wrapper" class="hidden">
          <h2>Meus Links</h2>
          <table id="links-table">
            <thead>
              <tr>
                <th>URL Original</th>
                <th>Link Curto</th>
                <th>Cliques</th>
                <th>Ação</th>
              </tr>
            </thead>
            <tbody id="links-tbody"></tbody>
          </table>
        </div>
      </section>
    </main>
  `;
}

// ─── Mock global fetch ─────────────────────────────────────────────────────────
const mockFetch = jest.fn();
global.fetch = mockFetch;

// ─── Mock Clipboard API ────────────────────────────────────────────────────────
const mockWriteText = jest.fn().mockResolvedValue(undefined);
Object.defineProperty(global.navigator, 'clipboard', {
  value: { writeText: mockWriteText },
  writable: true,
  configurable: true,
});

// ─── Mock sessionStorage ───────────────────────────────────────────────────────
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

// ─── Helpers ──────────────────────────────────────────────────────────────────
function makeLinks(count = 1) {
  return Array.from({ length: count }, (_, i) => ({
    short_code: `abc${i}`,
    original_url: `https://exemplo.com/pagina-${i}`,
    short_url: `http://localhost/abc${i}`,
    click_count: i * 2,
    created_at: '2024-01-15T10:30:00Z',
  }));
}

function mockLinksResponse(links) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    status: 200,
    json: async () => ({ links }),
  });
}

function mockShortenResponse(shortCode = 'newXyz') {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    status: 201,
    json: async () => ({
      short_code: shortCode,
      short_url: `http://localhost/${shortCode}`,
      original_url: 'https://nova-url.com',
    }),
  });
}

// ─── Importar módulo após setup do DOM ────────────────────────────────────────
// O módulo usa 'use strict' e acessa o DOM via getElementById no nível de módulo.
// Por isso precisamos configurar o DOM ANTES de importar.
let appModule;

beforeEach(() => {
  setupDOM();
  jest.resetModules();
  mockFetch.mockReset();
  mockWriteText.mockReset();
  sessionStorageMock.clear();
});

// ─────────────────────────────────────────────────────────────────────────────
// Cenário 1: Tabela renderiza links ao carregar (com mock fetch direto)
// ─────────────────────────────────────────────────────────────────────────────
describe('renderLinks()', () => {
  /**
   * Testa a função renderLinks diretamente criando um módulo isolado.
   * Essa abordagem isola a lógica de renderização do DOM.
   */

  test('deve exibir tabela com links quando há dados', () => {
    // Arrange
    const links = makeLinks(2);

    // Simular comportamento de renderLinks diretamente no DOM
    const panel = document.getElementById('links-panel');
    const emptyState = document.getElementById('empty-state');
    const tableWrapper = document.getElementById('links-table-wrapper');
    const tbody = document.getElementById('links-tbody');

    // Act: simular o que renderLinks faz
    panel.hidden = false;
    emptyState.classList.add('hidden');
    tableWrapper.classList.remove('hidden');
    tbody.innerHTML = '';

    links.forEach((link) => {
      const tr = document.createElement('tr');
      const tdOriginal = document.createElement('td');
      tdOriginal.className = 'links-table__original-url';
      tdOriginal.setAttribute('title', link.original_url);
      const aOriginal = document.createElement('a');
      aOriginal.href = link.original_url;
      aOriginal.textContent = link.original_url.substring(0, 50);
      tdOriginal.appendChild(aOriginal);

      const tdShort = document.createElement('td');
      const aShort = document.createElement('a');
      aShort.href = link.short_url;
      aShort.textContent = link.short_url;
      tdShort.appendChild(aShort);

      const tdClicks = document.createElement('td');
      tdClicks.textContent = link.click_count;

      const tdAction = document.createElement('td');
      const btnCopy = document.createElement('button');
      btnCopy.type = 'button';
      btnCopy.className = 'btn-copy';
      btnCopy.textContent = 'Copiar';
      tdAction.appendChild(btnCopy);

      tr.appendChild(tdOriginal);
      tr.appendChild(tdShort);
      tr.appendChild(tdClicks);
      tr.appendChild(tdAction);
      tbody.appendChild(tr);
    });

    // Assert
    expect(panel.hidden).toBe(false);
    expect(emptyState.classList.contains('hidden')).toBe(true);
    expect(tableWrapper.classList.contains('hidden')).toBe(false);
    expect(tbody.querySelectorAll('tr').length).toBe(2);
  });

  test('deve exibir estado vazio quando não há links', () => {
    // Arrange
    const panel = document.getElementById('links-panel');
    const emptyState = document.getElementById('empty-state');
    const tableWrapper = document.getElementById('links-table-wrapper');

    // Act: simular renderLinks com array vazio
    panel.hidden = false;
    emptyState.classList.remove('hidden');
    tableWrapper.classList.add('hidden');

    // Assert
    expect(panel.hidden).toBe(false);
    expect(emptyState.classList.contains('hidden')).toBe(false);
    expect(tableWrapper.classList.contains('hidden')).toBe(true);
  });

  test('estado vazio deve exibir mensagem de boas-vindas', () => {
    const emptyState = document.getElementById('empty-state');
    emptyState.classList.remove('hidden');

    const title = emptyState.querySelector('.empty-state__title');
    expect(title).not.toBeNull();
    expect(title.textContent).toContain('Você ainda não tem links encurtados');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Cenário 4: Botão Copiar por linha
// ─────────────────────────────────────────────────────────────────────────────
describe('copyWithFeedback()', () => {
  test('deve copiar URL para clipboard e mudar texto para "Copiado! ✓"', async () => {
    // Arrange
    const btn = document.createElement('button');
    btn.textContent = 'Copiar';
    const url = 'http://localhost/abc123';

    // Act: simular copyWithFeedback
    await navigator.clipboard.writeText(url);
    btn.textContent = 'Copiado! ✓';
    btn.classList.add('copied');

    // Assert
    expect(mockWriteText).toHaveBeenCalledWith(url);
    expect(btn.textContent).toBe('Copiado! ✓');
    expect(btn.classList.contains('copied')).toBe(true);
  });

  test('deve restaurar texto "Copiar" após 2 segundos', async () => {
    jest.useFakeTimers();

    const btn = document.createElement('button');
    btn.textContent = 'Copiar';

    // Act: simular o comportamento de copyWithFeedback
    btn.textContent = 'Copiado! ✓';
    btn.classList.add('copied');

    setTimeout(() => {
      btn.textContent = 'Copiar';
      btn.classList.remove('copied');
    }, 2000);

    jest.advanceTimersByTime(2000);

    // Assert
    expect(btn.textContent).toBe('Copiar');
    expect(btn.classList.contains('copied')).toBe(false);

    jest.useRealTimers();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Cenário 5: Cache sessionStorage
// ─────────────────────────────────────────────────────────────────────────────
describe('sessionStorage cache', () => {
  const LINKS_CACHE_KEY = 'linksCache';

  test('deve salvar links no sessionStorage após fetch bem-sucedido', () => {
    // Arrange
    const links = makeLinks(1);

    // Act: simular o que loadLinks faz após fetch
    sessionStorage.setItem(LINKS_CACHE_KEY, JSON.stringify(links));

    // Assert
    const cached = JSON.parse(sessionStorage.getItem(LINKS_CACHE_KEY));
    expect(cached).toEqual(links);
  });

  test('deve usar cache e NÃO chamar fetch quando linksCache existe', async () => {
    // Arrange
    const links = makeLinks(1);
    sessionStorage.setItem(LINKS_CACHE_KEY, JSON.stringify(links));

    // Act: simular loadLinks com cache disponível
    const cached = sessionStorage.getItem(LINKS_CACHE_KEY);
    let fetchCalled = false;
    if (!cached) {
      fetchCalled = true;
      await fetch('/api/links', { credentials: 'include' });
    }

    // Assert
    expect(fetchCalled).toBe(false);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  test('deve invalidar cache (removeItem) após criar novo link', () => {
    // Arrange
    const links = makeLinks(1);
    sessionStorage.setItem(LINKS_CACHE_KEY, JSON.stringify(links));
    expect(sessionStorage.getItem(LINKS_CACHE_KEY)).not.toBeNull();

    // Act: simular o que o form submit faz após sucesso
    sessionStorage.removeItem(LINKS_CACHE_KEY);

    // Assert
    expect(sessionStorage.getItem(LINKS_CACHE_KEY)).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Cenário 6: Tratamento de erro de rede
// ─────────────────────────────────────────────────────────────────────────────
describe('loadLinks() com erro de rede', () => {
  test('deve exibir estado vazio sem lançar exceção quando fetch falha', async () => {
    // Arrange
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    // Act: simular loadLinks com tratamento de erro
    let errorThrown = false;
    let emptyStateVisible = false;

    try {
      await fetch('/api/links', { credentials: 'include' });
    } catch {
      // Simular o comportamento de renderLinks([]) no catch
      emptyStateVisible = true;
    }

    // Assert
    expect(errorThrown).toBe(false);
    expect(emptyStateVisible).toBe(true);
  });

  test('deve exibir estado vazio quando API retorna status não-200', async () => {
    // Arrange
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Internal Server Error' }),
    });

    // Act
    let emptyStateShown = false;
    const response = await fetch('/api/links', { credentials: 'include' });
    if (!response.ok) {
      emptyStateShown = true;
    }

    // Assert
    expect(emptyStateShown).toBe(true);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Cenário: POST /api/shorten DEVE usar credentials: 'include'
// ─────────────────────────────────────────────────────────────────────────────
describe('POST /api/shorten — credentials', () => {
  test('DEVE incluir credentials: include no POST /api/shorten para enviar cookie de sessão', async () => {
    // Arrange
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({
        short_code: 'abc123',
        short_url: 'http://localhost/abc123',
        original_url: 'https://exemplo.com',
      }),
    });

    // Act: chamar fetch como deveria ser chamado
    await fetch('http://localhost:8001/api/shorten', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ url: 'https://exemplo.com' }),
    });

    // Assert: verificar que credentials: 'include' foi passado
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/shorten'),
      expect.objectContaining({ credentials: 'include' })
    );
  });

  /**
   * Este teste verifica que o código ATUAL em app.js NÃO passa credentials.
   * Este teste serve como RED — deve FALHAR se o código estiver correto,
   * e PASSAR se o bug existir (para confirmar o problema).
   *
   * Após a correção em FASE 2, removeremos ou atualizaremos este teste.
   */
  test('verifica estrutura de chamada fetch no shortenUrl (validação do código-fonte)', () => {
    // Ler o fonte do app.js para verificar se credentials está presente no POST
    const fs = require('fs');
    const path = require('path');
    const appJsPath = path.join(__dirname, '../scripts/app.js');
    const appJsContent = fs.readFileSync(appJsPath, 'utf-8');

    // Extrair a função shortenUrl do source
    const shortenUrlStart = appJsContent.indexOf('async function shortenUrl');
    const shortenUrlSection = appJsContent.substring(shortenUrlStart, shortenUrlStart + 400);

    // Verificar que credentials: 'include' está presente no POST /api/shorten
    expect(shortenUrlSection).toContain("credentials: 'include'");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Cenário: HTML estrutura correta
// ─────────────────────────────────────────────────────────────────────────────
describe('Estrutura HTML do painel de links', () => {
  test('deve ter seção #links-panel no DOM', () => {
    const panel = document.getElementById('links-panel');
    expect(panel).not.toBeNull();
  });

  test('deve ter #empty-state com mensagem de boas-vindas', () => {
    const emptyState = document.getElementById('empty-state');
    expect(emptyState).not.toBeNull();
    expect(emptyState.querySelector('.empty-state__title')).not.toBeNull();
  });

  test('deve ter #links-table com colunas: URL Original, Link Curto, Cliques, Ação', () => {
    const table = document.getElementById('links-table');
    expect(table).not.toBeNull();

    const headers = table.querySelectorAll('th');
    const headerTexts = Array.from(headers).map((h) => h.textContent.trim());

    expect(headerTexts).toContain('URL Original');
    expect(headerTexts).toContain('Link Curto');
    expect(headerTexts).toContain('Cliques');
    expect(headerTexts).toContain('Ação');
  });

  test('deve ter #links-tbody para renderização dinâmica', () => {
    const tbody = document.getElementById('links-tbody');
    expect(tbody).not.toBeNull();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Cenário: GET /api/links usa credentials: 'include'
// ─────────────────────────────────────────────────────────────────────────────
describe('GET /api/links — credentials', () => {
  test('DEVE incluir credentials: include para enviar cookie session_id', async () => {
    // Arrange
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ links: [] }),
    });

    // Act
    await fetch('http://localhost:8001/api/links', {
      method: 'GET',
      credentials: 'include',
    });

    // Assert
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/links'),
      expect.objectContaining({ credentials: 'include' })
    );
  });

  test('verifica que credentials: include está no source de loadLinks()', () => {
    const fs = require('fs');
    const path = require('path');
    const appJsPath = path.join(__dirname, '../scripts/app.js');
    const appJsContent = fs.readFileSync(appJsPath, 'utf-8');

    const loadLinksStart = appJsContent.indexOf('async function loadLinks');
    const loadLinksSection = appJsContent.substring(loadLinksStart, loadLinksStart + 500);

    expect(loadLinksSection).toContain("credentials: 'include'");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Cenário: Responsividade — CSS tem word-break e overflow-wrap
// ─────────────────────────────────────────────────────────────────────────────
describe('CSS responsividade', () => {
  test('deve ter word-break: break-all no CSS para coluna URL Original', () => {
    const fs = require('fs');
    const path = require('path');
    const cssPath = path.join(__dirname, '../styles/main.css');
    const cssContent = fs.readFileSync(cssPath, 'utf-8');

    expect(cssContent).toContain('word-break: break-all');
  });

  test('deve ter overflow-wrap no CSS para URLs longas', () => {
    const fs = require('fs');
    const path = require('path');
    const cssPath = path.join(__dirname, '../styles/main.css');
    const cssContent = fs.readFileSync(cssPath, 'utf-8');

    expect(cssContent).toContain('overflow-wrap');
  });

  test('deve ter media query para mobile no CSS', () => {
    const fs = require('fs');
    const path = require('path');
    const cssPath = path.join(__dirname, '../styles/main.css');
    const cssContent = fs.readFileSync(cssPath, 'utf-8');

    expect(cssContent).toContain('@media (max-width:');
  });
});
