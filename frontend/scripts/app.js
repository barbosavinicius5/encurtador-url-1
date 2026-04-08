/**
 * Encurtador de URL — Lógica JavaScript
 * Vanilla JS, sem dependências externas.
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
      message: "Por favor, informe uma URL para encurtar.",
    };
  }

  // AC3: formato inválido — deve mencionar http:// ou https://
  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return {
        valid: false,
        type: "format",
        message:
          "URL inválida. Certifique-se de que começa com http:// ou https://",
      };
    }
  } catch {
    return {
      valid: false,
      type: "format",
      message:
        "URL inválida. Certifique-se de que começa com http:// ou https://",
    };
  }

  return { valid: true };
}

/**
 * Sanitiza um href antes de inserir no DOM — garante esquema http/https.
 * Previne XSS via javascript: ou data: URLs (RN5).
 * @param {string} url
 * @returns {string} URL segura ou '#' como fallback
 */
function sanitizeHref(url) {
  if (typeof url !== "string") return "#";
  const trimmed = url.trim();
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  return "#";
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
  shortenBtn.textContent = isLoading ? "Encurtando..." : "Encurtar";
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
 * @param {string} shortUrl
 */
function showResult(shortUrl) {
  const safeHref = sanitizeHref(shortUrl);
  shortUrlDisplay.textContent = shortUrl; // textContent — seguro contra XSS
  shortUrlDisplay.href = safeHref; // href validado — previne javascript:/data:
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
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (response.status === 201) {
    const data = await response.json();
    return { success: true, shortUrl: data.short_url };
  }

  if (response.status === 422) {
    // Usar a mensagem orientativa do backend (RN4) quando disponível
    let detail =
      "URL inválida. Verifique se começa com http:// ou https:// e tente novamente.";
    try {
      const data = await response.json();
      if (data && typeof data.detail === "string" && data.detail.length > 0) {
        detail = data.detail;
      }
    } catch {
      // Ignorar erros de parse — usar mensagem padrão
    }
    return {
      success: false,
      type: "validation",
      message: detail,
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

  // Erro 500 ou outro erro de servidor
  return {
    success: false,
    type: "server",
    message: "Ocorreu um erro no servidor. Tente novamente em instantes.",
  };
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
      sessionStorage.removeItem(LINKS_CACHE_KEY);
      await loadLinks();
    } else if (result.type === "validation") {
      // Erro de validação do backend — exibir no campo (AC7/RN4)
      showFieldError(result.message);
    } else {
      // Erros de servidor ou rate limit — exibir no banner (AC7)
      showBannerError(result.message);
    }
  } catch (networkError) {
    // Erro de rede — mensagem específica sobre conexão (AC7/RN4)
    console.error("Erro de rede:", networkError);
    showBannerError(
      "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.",
    );
  } finally {
    setLoading(false);
  }
});

/**
 * Copiar link curto para a área de transferência com feedback temporal (AC6/RN3).
 * Feedback "Copiado!" por COPY_FEEDBACK_DURATION ms, depois retorna a "Copiar".
 */
let copyTimeout = null;
copyBtn.addEventListener("click", async () => {
  const shortUrl = shortUrlDisplay.textContent;

  try {
    await navigator.clipboard.writeText(shortUrl);
    copyBtn.textContent = "Copiado!";
    copyBtn.classList.add("copied");
  } catch {
    // Fallback para navegadores sem suporte à Clipboard API (contexto não-seguro)
    // Tenta selecionar o texto do link como alternativa
    try {
      const range = document.createRange();
      range.selectNode(shortUrlDisplay);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);
    } catch {
      // Silencioso — clipboard e seleção indisponíveis
    }
    copyBtn.textContent = "Copie manualmente";
    copyBtn.classList.add("copied");
  }

  // Restaura estado original após COPY_FEEDBACK_DURATION ms (RN3)
  clearTimeout(copyTimeout);
  copyTimeout = setTimeout(() => {
    copyBtn.textContent = "Copiar";
    copyBtn.classList.remove("copied");
  }, COPY_FEEDBACK_DURATION);
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
  return url.substring(0, maxLength) + "...";
}

/**
 * Copia um texto para a área de transferência com feedback visual no botão.
 * @param {HTMLButtonElement} btn
 * @param {string} text
 */
async function copyWithFeedback(btn, text) {
  try {
    await navigator.clipboard.writeText(text);
    btn.textContent = "Copiado! ✓";
    btn.classList.add("copied");
  } catch {
    // Fallback silencioso: Clipboard API pode não estar disponível em HTTP
    console.error("Clipboard API não disponível");
    btn.textContent = "Copie manualmente";
  }

  setTimeout(() => {
    btn.textContent = "Copiar";
    btn.classList.remove("copied");
  }, 2000);
}

/**
 * Renderiza a tabela de links ou o estado vazio.
 * @param {Array<{short_code: string, original_url: string, short_url: string, click_count: number}>} links
 */
function renderLinks(links) {
  const panel = document.getElementById("links-panel");
  const emptyState = document.getElementById("empty-state");
  const tableWrapper = document.getElementById("links-table-wrapper");
  const tbody = document.getElementById("links-tbody");

  // Exibir o painel
  panel.hidden = false;

  if (!links || links.length === 0) {
    emptyState.classList.remove("hidden");
    tableWrapper.classList.add("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  tableWrapper.classList.remove("hidden");

  // Limpar linhas anteriores
  tbody.innerHTML = "";

  links.forEach((link) => {
    const tr = document.createElement("tr");

    // Coluna: URL Original
    const tdOriginal = document.createElement("td");
    tdOriginal.className = "links-table__original-url";
    tdOriginal.setAttribute("title", link.original_url);
    const aOriginal = document.createElement("a");
    aOriginal.href = sanitizeHref(link.original_url); // sanitizado — previne XSS (RN5)
    aOriginal.target = "_blank";
    aOriginal.rel = "noopener noreferrer";
    aOriginal.textContent = truncateUrl(link.original_url, 50);
    tdOriginal.appendChild(aOriginal);

    // Coluna: Link Curto
    const tdShort = document.createElement("td");
    tdShort.className = "links-table__short-url";
    const aShort = document.createElement("a");
    aShort.href = sanitizeHref(link.short_url); // sanitizado — previne XSS (RN5)
    aShort.target = "_blank";
    aShort.rel = "noopener noreferrer";
    aShort.textContent = link.short_url;
    tdShort.appendChild(aShort);

    // Coluna: Cliques
    const tdClicks = document.createElement("td");
    tdClicks.className = "links-table__clicks";
    tdClicks.textContent = link.click_count;

    // Coluna: Ação
    const tdAction = document.createElement("td");
    tdAction.className = "links-table__action";
    const btnCopy = document.createElement("button");
    btnCopy.type = "button";
    btnCopy.className = "btn-copy";
    btnCopy.textContent = "Copiar";
    btnCopy.setAttribute("aria-label", `Copiar link curto ${link.short_url}`);
    btnCopy.addEventListener("click", () =>
      copyWithFeedback(btnCopy, link.short_url),
    );
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
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      console.error("[loadLinks] Erro na API:", response.status);
      // Exibir estado vazio sem lançar erro
      renderLinks([]);
      return;
    }

    const data = await response.json();
    // Salvar no cache
    sessionStorage.setItem(LINKS_CACHE_KEY, JSON.stringify(data.links));
    renderLinks(data.links);
  } catch (err) {
    console.error("[loadLinks] Falha ao carregar links:", err);
    // Exibir estado vazio sem lançar exceção
    renderLinks([]);
  }
}

// Carregar links ao inicializar a página
document.addEventListener("DOMContentLoaded", () => {
  loadLinks();
});
