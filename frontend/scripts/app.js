/**
 * Encurtador de URL — Lógica JavaScript
 * Vanilla JS, sem dependências externas.
 *
 * Lazy loading: o módulo links-panel.js é carregado dinamicamente via IntersectionObserver
 * apenas quando a seção #links-panel se torna visível no viewport (AC9).
 */

"use strict";

// Configuração da URL base da API
// Em produção, substituir por injeção via servidor ou variável de ambiente
const API_BASE_URL = window.ENV_API_BASE_URL || "http://localhost:8000";

// Chave do cache sessionStorage para os links
const LINKS_CACHE_KEY = "linksCache";

// Tempo (ms) que o feedback "Copiado!" permanece visível (RN3)
const COPY_FEEDBACK_DURATION = 2000;

// Referências aos elementos do DOM
const form = document.getElementById("shorten-form");
const urlInput = document.getElementById("url-input");
const urlError = document.getElementById("url-error");
const shortenBtn = document.getElementById("shorten-btn");
const errorBanner = document.getElementById("error-banner");
const resultSection = document.getElementById("result-section");
const shortUrlDisplay = document.getElementById("short-url-display");
const copyBtn = document.getElementById("copy-btn");

// ————————————————————————————————————————————————————
// Funções de validação client-side (bifurcada — AC2/AC3)
// ————————————————————————————————————————————————————

/**
 * Valida a URL com bifurcação entre campo vazio e formato inválido.
 * @param {string} rawValue - Valor bruto do campo (sem trim)
 * @returns {{ valid: boolean, type?: 'empty'|'format', message?: string }}
 */
function validateUrlClientSide(rawValue) {
  const trimmed = rawValue.trim();

  // AC2: campo vazio — não dispara requisição e exibe mensagem de obrigatoriedade
  if (!trimmed) {
    return {
      valid: false,
      type: "empty",
      message: "O campo é obrigatório",
    };
  }

  // AC3: formato inválido — URL deve ser parseável e ter protocolo http/https
  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return {
        valid: false,
        type: "format",
        message:
          "Por favor, insira uma URL válida (ex: https://exemplo.com)",
      };
    }
  } catch {
    return {
      valid: false,
      type: "format",
      message:
        "Por favor, insira uma URL válida (ex: https://exemplo.com)",
    };
  }

  return { valid: true };
}

/**
 * Sanitiza um href antes de inserir no DOM — garante esquema http/https.
 * Previne XSS via javascript: ou data: URLs (RN5).
 * @param {string} url
 * @returns {{ safe: boolean, href: string }} href seguro ou '#' como fallback
 */
function sanitizeHref(url) {
  if (typeof url !== "string") return { safe: false, href: "#" };
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed)) {
    return { safe: true, href: trimmed };
  }
  return { safe: false, href: "#" };
}

// ————————————————————————————————————————————————————
// Funções de estado da UI
// ————————————————————————————————————————————————————

/**
 * Ativa/desativa o estado de loading do botão e campo (AC4).
 * Desabilita também o input para evitar edição concorrente.
 * @param {boolean} isLoading
 */
function setLoading(isLoading) {
  shortenBtn.disabled = isLoading;
  urlInput.disabled = isLoading;
  shortenBtn.textContent = isLoading ? "Encurtando..." : "Encurtar URL";
  if (isLoading) {
    shortenBtn.setAttribute("aria-busy", "true");
  } else {
    shortenBtn.removeAttribute("aria-busy");
  }
}

/**
 * Exibe um erro inline no campo de URL (AC2/AC3).
 * O foco retorna ao campo para facilitar correção.
 * @param {string} message
 */
function showFieldError(message) {
  urlError.textContent = message;
  urlError.hidden = false;
  urlInput.setAttribute("aria-invalid", "true");
  urlInput.focus();
}

/**
 * Exibe uma mensagem de erro no banner global (AC7).
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
  urlError.textContent = "";
  urlInput.removeAttribute("aria-invalid");
  errorBanner.hidden = true;
  errorBanner.textContent = "";
}

/**
 * Exibe o resultado com o link curto gerado (AC5).
 * Usa textContent para textos (seguro contra XSS) e sanitizeHref para o href (RN5).
 * Se a URL retornada pelo backend não começar com http:// ou https://, exibe erro.
 * @param {string} shortUrl
 */
function showResult(shortUrl) {
  const { safe, href } = sanitizeHref(shortUrl);

  // Cenário C: URL retornada com esquema inválido (ex: javascript:, data:) — não atribuir ao href
  if (!safe) {
    showBannerError(
      "A URL retornada é inválida. Entre em contato com o suporte.",
    );
    return;
  }

  shortUrlDisplay.textContent = shortUrl; // textContent — seguro contra XSS
  shortUrlDisplay.href = href; // href validado — previne javascript:/data:
  resultSection.hidden = false;
  // Anunciar resultado ao leitor de tela via aria-live no wrapper
  const liveRegion = document.getElementById("result-live-region");
  if (liveRegion) {
    liveRegion.textContent = ""; // reset para forçar novo anúncio
    setTimeout(() => {
      liveRegion.textContent = `Link encurtado gerado: ${shortUrl}`;
    }, 50);
  }
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
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (response.status === 201) {
    const data = await response.json();
    return { success: true, shortUrl: data.short_url };
  }

  if (response.status === 422) {
    return {
      success: false,
      type: "validation",
      message: "A URL informada não é válida. Verifique e tente novamente.",
    };
  }

  if (response.status === 429) {
    return {
      success: false,
      type: "rate_limit",
      message:
        "Limite de requisições atingido. Aguarde um momento antes de tentar novamente.",
    };
  }

  // Erro 500 ou outro erro de servidor — Cenário B
  if (response.status >= 500) {
    return {
      success: false,
      type: "server",
      message:
        "O serviço está temporariamente indisponível. Tente em alguns minutos.",
    };
  }

  // Outros erros HTTP não mapeados
  return {
    success: false,
    type: "server",
    message: "Ocorreu um problema. Tente novamente.",
  };
}

// ————————————————————————————————————————————————————
// Lazy Loading do painel de links (AC9)
// ————————————————————————————————————————————————————

/**
 * Módulo de links carregado dinamicamente (referência após import()).
 * null antes do carregamento, objeto com as funções exportadas após.
 */
let linksPanelModule = null;

/**
 * Carrega o módulo do painel de links dinamicamente e o inicializa.
 * Garante que o módulo é carregado apenas uma vez (idempotente).
 * @returns {Promise<void>}
 */
async function ensureLinksPanelLoaded() {
  if (!linksPanelModule) {
    try {
      // import() dinâmico — não está no bundle inicial (AC9)
      linksPanelModule = await import("./links-panel.js");
    } catch (err) {
      console.error("[app] Falha ao carregar módulo de links:", err);
      return;
    }
  }
  return linksPanelModule;
}

/**
 * Inicializa o painel de links carregando o módulo dinamicamente.
 * Delegação para initLinksPanel() do módulo.
 */
async function initLinksPanelLazy() {
  const module = await ensureLinksPanelLoaded();
  if (module) {
    module.initLinksPanel();
  }
}

/**
 * Recarrega os links (invalida cache e dispara nova requisição).
 * Usado após encurtar URL com sucesso.
 */
async function reloadLinks() {
  sessionStorage.removeItem(LINKS_CACHE_KEY);
  const module = await ensureLinksPanelLoaded();
  if (module) {
    await module.loadLinks();
  }
}

// ————————————————————————————————————————————————————
// Event Listeners
// ————————————————————————————————————————————————————

/**
 * Submit do formulário — validação bifurcada e chamada à API (AC2/AC3/AC4).
 */
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearErrors();

  // Validação client-side bifurcada (AC2: vazio / AC3: formato inválido)
  const validation = validateUrlClientSide(urlInput.value);
  if (!validation.valid) {
    showFieldError(validation.message);
    return; // Não dispara requisição (AC2/AC3)
  }

  const url = urlInput.value.trim();

  // Loading state: desabilita botão e campo (AC4)
  setLoading(true);
  resultSection.hidden = true;

  try {
    const result = await shortenUrl(url);

    if (result.success) {
      showResult(result.shortUrl);
      // Invalida cache e recarrega painel de links
      await reloadLinks();
    } else if (result.type === "validation") {
      // Erro de validação do backend — exibir no campo (AC7/RN4)
      showFieldError(result.message);
    } else {
      // Erros de servidor ou rate limit — exibir no banner (AC7)
      showBannerError(result.message);
    }
  } catch (networkError) {
    // Erro de rede — TypeError indica offline/timeout (AC7/RN4)
    console.error("Erro de rede:", networkError);
    if (networkError instanceof TypeError) {
      showBannerError("Verifique sua conexão e tente novamente.");
    } else {
      showBannerError("Ocorreu um problema inesperado. Tente novamente.");
    }
  } finally {
    setLoading(false);
  }
});

/**
 * Copiar link curto para a área de transferência com feedback temporal (AC6/RN3).
 * Feedback "Copiado!" por COPY_FEEDBACK_DURATION ms, depois retorna a "Copiar".
 * aria-label atualizado dinamicamente para leitores de tela (Cenário D/E).
 */
let copyTimeout = null;
copyBtn.addEventListener("click", async () => {
  const shortUrl = shortUrlDisplay.textContent;

  try {
    await navigator.clipboard.writeText(shortUrl);
    copyBtn.textContent = "Copiado!";
    copyBtn.classList.add("copied");
    copyBtn.setAttribute("aria-label", "Link copiado, aguarde");
    copyBtn.disabled = true;
  } catch {
    // Fallback para navegadores sem suporte à Clipboard API (contexto não-seguro)
    // Tenta selecionar o texto do link como alternativa
    try {
      const range = document.createRange();
      range.selectNode(shortUrlDisplay);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);
      copyBtn.textContent = "Copiado!";
      copyBtn.classList.add("copied");
      copyBtn.setAttribute("aria-label", "Link copiado, aguarde");
      copyBtn.disabled = true;
    } catch {
      // Clipboard e seleção indisponíveis — informar ao usuário
      showBannerError(
        "Não foi possível copiar automaticamente. Copie a URL manualmente.",
      );
    }
  }

  // Restaura estado original após COPY_FEEDBACK_DURATION ms (RN3)
  clearTimeout(copyTimeout);
  copyTimeout = setTimeout(() => {
    copyBtn.textContent = "Copiar";
    copyBtn.classList.remove("copied");
    copyBtn.setAttribute("aria-label", "Copiar link encurtado");
    copyBtn.disabled = false;
  }, COPY_FEEDBACK_DURATION);
});

// ————————————————————————————————————————————————————
// Inicialização: lazy loading do painel de links via IntersectionObserver
// ————————————————————————————————————————————————————

/**
 * Inicializa o IntersectionObserver para carregar o módulo de links
 * apenas quando a seção #links-panel se torna visível (AC9 — lazy loading).
 *
 * O módulo links-panel.js não é baixado no carregamento inicial da página.
 */
document.addEventListener("DOMContentLoaded", () => {
  const linksPanel = document.getElementById("links-panel");

  if (!linksPanel) return;

  // Usar IntersectionObserver para carregar o módulo quando o painel ficar visível
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          // Painel visível — carregar módulo e inicializar
          initLinksPanelLazy();
          observer.disconnect(); // Carregar apenas uma vez
        }
      },
      { threshold: 0.1 }, // 10% do painel visível é suficiente para disparar
    );
    observer.observe(linksPanel);
  } else {
    // Fallback para browsers sem suporte a IntersectionObserver
    initLinksPanelLazy();
  }
});
