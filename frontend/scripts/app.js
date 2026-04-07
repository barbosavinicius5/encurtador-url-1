/**
 * Encurtador de URL — Lógica JavaScript
 * Vanilla JS, sem dependências externas.
 */

'use strict';

// Configuração da URL base da API
// Em produção, substituir por injeção via servidor ou variável de ambiente
const API_BASE_URL = window.ENV_API_BASE_URL || 'http://localhost:8000';

// Chave do cache sessionStorage para os links
const LINKS_CACHE_KEY = 'linksCache';

// Referências aos elementos do DOM
const form = document.getElementById('shorten-form');
const urlInput = document.getElementById('url-input');
const urlError = document.getElementById('url-error');
const shortenBtn = document.getElementById('shorten-btn');
const errorBanner = document.getElementById('error-banner');
const resultSection = document.getElementById('result-section');
const shortUrlDisplay = document.getElementById('short-url-display');
const copyBtn = document.getElementById('copy-btn');

// ————————————————————————————————————————————————————
// Funções de validação
// ————————————————————————————————————————————————————

/**
 * Valida se a string é uma URL válida com protocolo http ou https.
 * @param {string} url
 * @returns {boolean}
 */
function isValidUrl(url) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

// ————————————————————————————————————————————————————
// Funções de estado da UI
// ————————————————————————————————————————————————————

/**
 * Ativa/desativa o estado de loading do botão.
 * @param {boolean} isLoading
 */
function setLoading(isLoading) {
  shortenBtn.disabled = isLoading;
  shortenBtn.textContent = isLoading ? 'Encurtando...' : 'Encurtar';
}

/**
 * Exibe um erro inline no campo de URL.
 * @param {string} message
 */
function showFieldError(message) {
  urlError.textContent = message;
  urlError.hidden = false;
  urlInput.setAttribute('aria-invalid', 'true');
  urlInput.focus();
}

/**
 * Exibe uma mensagem de erro no banner global.
 * @param {string} message
 */
function showBannerError(message) {
  errorBanner.textContent = message;
  errorBanner.hidden = false;
}

/**
 * Limpa todos os estados de erro.
 */
function clearErrors() {
  urlError.hidden = true;
  urlError.textContent = '';
  urlInput.removeAttribute('aria-invalid');
  errorBanner.hidden = true;
  errorBanner.textContent = '';
}

/**
 * Exibe o resultado com o link curto gerado.
 * Limpa erros anteriores ao exibir o resultado (critério de aceite A).
 * @param {string} shortUrl
 */
function showResult(shortUrl) {
  shortUrlDisplay.textContent = shortUrl;
  shortUrlDisplay.href = shortUrl;
  resultSection.hidden = false;
  // Ocultar área de erro quando há resultado bem-sucedido
  clearErrors();
}

// ————————————————————————————————————————————————————
// Chamada à API
// ————————————————————————————————————————————————————

/**
 * Chama a API para encurtar a URL.
 * @param {string} url
 * @returns {Promise<{success: boolean, shortUrl?: string, type?: string, message?: string}>}
 */
async function shortenUrl(url) {
  const response = await fetch(`${API_BASE_URL}/api/shorten`, {
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

// ————————————————————————————————————————————————————
// Event Listeners
// ————————————————————————————————————————————————————

/**
 * Submit do formulário — valida e chama a API.
 */
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearErrors();

  const url = urlInput.value.trim();

  // Validação client-side (somente no submit)
  if (!isValidUrl(url)) {
    showFieldError('Por favor, insira uma URL válida (ex: https://exemplo.com)');
    return;
  }

  setLoading(true);

  try {
    const result = await shortenUrl(url);

    if (result.success) {
      showResult(result.shortUrl);
      // Invalida cache e recarrega painel de links
      sessionStorage.removeItem(LINKS_CACHE_KEY);
      await loadLinks();
    } else {
      showBannerError(result.message);
    }
  } catch (networkError) {
    console.error('Erro de rede:', networkError);
    showBannerError('Ocorreu um erro inesperado. Tente novamente em alguns instantes.');
  } finally {
    setLoading(false);
  }
});

/**
 * Copiar link curto para a área de transferência.
 */
let copyResetTimer = null;

copyBtn.addEventListener('click', async () => {
  const shortUrl = shortUrlDisplay.textContent;

  // Cancelar timer anterior para evitar acúmulo em cliques rápidos
  if (copyResetTimer) {
    clearTimeout(copyResetTimer);
    copyResetTimer = null;
  }

  try {
    await navigator.clipboard.writeText(shortUrl);
    copyBtn.textContent = 'Copiado!';
    copyBtn.classList.add('copied');
  } catch {
    // Fallback para navegadores sem suporte à Clipboard API
    copyBtn.textContent = 'Copie manualmente';
  }

  // Restaura estado original após 2 segundos
  copyResetTimer = setTimeout(() => {
    copyBtn.textContent = 'Copiar';
    copyBtn.classList.remove('copied');
    copyResetTimer = null;
  }, 2000);
});

// ————————————————————————————————————————————————————
// Painel de links da sessão
// ————————————————————————————————————————————————————

/**
 * Trunca uma URL longa para exibição.
 * @param {string} url
 * @param {number} maxLength
 * @returns {string}
 */
function truncateUrl(url, maxLength) {
  if (url.length <= maxLength) return url;
  return url.substring(0, maxLength) + '...';
}

/**
 * Copia um texto para a área de transferência com feedback visual no botão.
 * @param {HTMLButtonElement} btn
 * @param {string} text
 */
async function copyWithFeedback(btn, text) {
  try {
    await navigator.clipboard.writeText(text);
    btn.textContent = 'Copiado! ✓';
    btn.classList.add('copied');
  } catch {
    // Fallback silencioso: Clipboard API pode não estar disponível em HTTP
    console.error('Clipboard API não disponível');
    btn.textContent = 'Copie manualmente';
  }

  setTimeout(() => {
    btn.textContent = 'Copiar';
    btn.classList.remove('copied');
  }, 2000);
}

/**
 * Renderiza a tabela de links ou o estado vazio.
 * @param {Array<{short_code: string, original_url: string, short_url: string, click_count: number}>} links
 */
function renderLinks(links) {
  const panel = document.getElementById('links-panel');
  const emptyState = document.getElementById('empty-state');
  const tableWrapper = document.getElementById('links-table-wrapper');
  const tbody = document.getElementById('links-tbody');

  // Exibir o painel
  panel.hidden = false;

  if (!links || links.length === 0) {
    emptyState.classList.remove('hidden');
    tableWrapper.classList.add('hidden');
    return;
  }

  emptyState.classList.add('hidden');
  tableWrapper.classList.remove('hidden');

  // Limpar linhas anteriores
  tbody.innerHTML = '';

  links.forEach((link) => {
    const tr = document.createElement('tr');

    // Coluna: URL Original
    const tdOriginal = document.createElement('td');
    tdOriginal.className = 'links-table__original-url';
    tdOriginal.setAttribute('title', link.original_url);
    const aOriginal = document.createElement('a');
    aOriginal.href = link.original_url;
    aOriginal.target = '_blank';
    aOriginal.rel = 'noopener noreferrer';
    aOriginal.textContent = truncateUrl(link.original_url, 50);
    tdOriginal.appendChild(aOriginal);

    // Coluna: Link Curto
    const tdShort = document.createElement('td');
    tdShort.className = 'links-table__short-url';
    const aShort = document.createElement('a');
    aShort.href = link.short_url;
    aShort.target = '_blank';
    aShort.rel = 'noopener noreferrer';
    aShort.textContent = link.short_url;
    tdShort.appendChild(aShort);

    // Coluna: Cliques
    const tdClicks = document.createElement('td');
    tdClicks.className = 'links-table__clicks';
    tdClicks.textContent = link.click_count;

    // Coluna: Ação
    const tdAction = document.createElement('td');
    tdAction.className = 'links-table__action';
    const btnCopy = document.createElement('button');
    btnCopy.type = 'button';
    btnCopy.className = 'btn-copy';
    btnCopy.textContent = 'Copiar';
    btnCopy.setAttribute('aria-label', `Copiar link curto ${link.short_url}`);
    btnCopy.addEventListener('click', () => copyWithFeedback(btnCopy, link.short_url));
    tdAction.appendChild(btnCopy);

    tr.appendChild(tdOriginal);
    tr.appendChild(tdShort);
    tr.appendChild(tdClicks);
    tr.appendChild(tdAction);
    tbody.appendChild(tr);
  });
}

/**
 * Busca links da sessão atual via GET /api/links.
 * Utiliza sessionStorage como cache para evitar chamadas redundantes.
 */
async function loadLinks() {
  // Tentar cache do sessionStorage primeiro
  try {
    const cached = sessionStorage.getItem(LINKS_CACHE_KEY);
    if (cached) {
      renderLinks(JSON.parse(cached));
      return;
    }
  } catch {
    // Ignorar erros de parse do cache
    sessionStorage.removeItem(LINKS_CACHE_KEY);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/links`, {
      method: 'GET',
      credentials: 'include',
    });

    if (!response.ok) {
      console.error('[loadLinks] Erro na API:', response.status);
      // Exibir estado vazio sem lançar erro
      renderLinks([]);
      return;
    }

    const data = await response.json();
    // Salvar no cache
    sessionStorage.setItem(LINKS_CACHE_KEY, JSON.stringify(data.links));
    renderLinks(data.links);
  } catch (err) {
    console.error('[loadLinks] Falha ao carregar links:', err);
    // Exibir estado vazio sem lançar exceção
    renderLinks([]);
  }
}

// Carregar links ao inicializar a página
document.addEventListener('DOMContentLoaded', () => {
  loadLinks();
});
