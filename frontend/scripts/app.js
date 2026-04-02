/**
 * Encurtador de URL — Lógica JavaScript
 * Vanilla JS, sem dependências externas.
 */

'use strict';

// Configuração da URL base da API
// Em produção, substituir por injeção via servidor ou variável de ambiente
const API_BASE_URL = window.ENV_API_BASE_URL || 'http://localhost:8000';

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
 * @param {string} shortUrl
 */
function showResult(shortUrl) {
  shortUrlDisplay.textContent = shortUrl;
  shortUrlDisplay.href = shortUrl;
  resultSection.hidden = false;
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
copyBtn.addEventListener('click', async () => {
  const shortUrl = shortUrlDisplay.textContent;

  try {
    await navigator.clipboard.writeText(shortUrl);
    copyBtn.textContent = 'Copiado!';
    copyBtn.classList.add('copied');
  } catch {
    // Fallback para navegadores sem suporte à Clipboard API
    copyBtn.textContent = 'Copie manualmente';
  }

  // Restaura estado original após 2 segundos
  setTimeout(() => {
    copyBtn.textContent = 'Copiar';
    copyBtn.classList.remove('copied');
  }, 2000);
});
