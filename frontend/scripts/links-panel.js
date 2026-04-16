/**
 * Módulo do painel de links — carregado via import() dinâmico (lazy loading).
 * Responsável por buscar, renderizar e gerenciar o estado do painel de links da sessão.
 *
 * Segurança: todos os dados da API são inseridos via textContent (nunca innerHTML).
 * Cache: sessionStorage validado estruturalmente antes de uso.
 * Resiliência: erros de rede não destroem links já exibidos na tabela.
 */

"use strict";

// Configuração da URL base da API
const API_BASE_URL = window.ENV_API_BASE_URL || "http://localhost:8000";

// Chave do cache sessionStorage para os links
const LINKS_CACHE_KEY = "linksCache";

// Tempo máximo de validade do cache em milissegundos (60 segundos)
const CACHE_TTL_MS = 60_000;

// ————————————————————————————————————————————————————
// Funções utilitárias
// ————————————————————————————————————————————————————

/**
 * Sanitiza um href antes de inserir no DOM — garante esquema http/https.
 * Previne XSS via javascript: ou data: URLs.
 * @param {string} url
 * @returns {{ safe: boolean, href: string }}
 */
function sanitizeHref(url) {
  if (typeof url !== "string") return { safe: false, href: "#" };
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed)) {
    return { safe: true, href: trimmed };
  }
  return { safe: false, href: "#" };
}

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

// ————————————————————————————————————————————————————
// Funções de estado do banner de erro do painel
// ————————————————————————————————————————————————————

/**
 * Exibe o banner de erro do painel de links sem destruir o conteúdo da tabela.
 * @param {string} message
 */
function showLinkError(message) {
  const banner = document.getElementById("links-error-banner");
  if (banner) {
    banner.textContent = message; // textContent — seguro, sem XSS
    banner.hidden = false;
  }
}

/**
 * Oculta o banner de erro do painel de links.
 */
function hideLinkError() {
  const banner = document.getElementById("links-error-banner");
  if (banner) {
    banner.hidden = true;
    banner.textContent = "";
  }
}

// ————————————————————————————————————————————————————
// Cache do sessionStorage
// ————————————————————————————————————————————————————

/**
 * Recupera e valida o cache de links do sessionStorage.
 * Retorna null se o cache não existir, estiver expirado, corrompido ou com estrutura inválida.
 *
 * Segurança: valida estrutura antes de usar para evitar injeção via cache corrompido.
 *
 * @returns {Array|null} Array de links válidos ou null
 */
function getLinksFromCache() {
  try {
    const raw = sessionStorage.getItem(LINKS_CACHE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw);

    // Validar estrutura mínima esperada
    if (!Array.isArray(parsed?.links)) return null;

    // Validar TTL do cache
    if (typeof parsed.cached_at === "number") {
      if (Date.now() - parsed.cached_at > CACHE_TTL_MS) {
        sessionStorage.removeItem(LINKS_CACHE_KEY);
        return null;
      }
    }

    // Validar estrutura de cada item — garantir que são primitivos (não objetos aninhados maliciosos)
    const valid = parsed.links.every(
      (item) =>
        item !== null &&
        typeof item === "object" &&
        typeof item.short_code === "string" &&
        typeof item.original_url === "string" &&
        typeof item.click_count === "number" &&
        typeof item.short_url === "string",
    );

    if (!valid) {
      sessionStorage.removeItem(LINKS_CACHE_KEY);
      return null;
    }

    return parsed.links;
  } catch {
    // JSON malformado ou dados corrompidos — descartar cache
    sessionStorage.removeItem(LINKS_CACHE_KEY);
    return null;
  }
}

/**
 * Salva links no cache do sessionStorage com timestamp.
 * @param {Array} links
 */
function saveLinksToCache(links) {
  try {
    const cacheData = {
      links,
      cached_at: Date.now(),
    };
    sessionStorage.setItem(LINKS_CACHE_KEY, JSON.stringify(cacheData));
  } catch {
    // sessionStorage pode estar cheio ou indisponível — ignorar silenciosamente
    console.warn("[links-panel] Não foi possível salvar cache no sessionStorage");
  }
}

// ————————————————————————————————————————————————————
// Renderização do painel
// ————————————————————————————————————————————————————

/**
 * Renderiza a tabela de links ou o estado vazio.
 * Todos os dados são inseridos via textContent ou createElement (nunca innerHTML com dados).
 *
 * @param {Array<{short_code: string, original_url: string, short_url: string, click_count: number}>} links
 */
export function renderLinks(links) {
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

  // Limpar linhas anteriores — tbody.innerHTML = "" é seguro pois não insere dados do usuário
  tbody.innerHTML = "";

  links.forEach((link) => {
    const tr = document.createElement("tr");

    // Coluna: URL Original
    const tdOriginal = document.createElement("td");
    tdOriginal.className = "links-table__original-url";
    tdOriginal.setAttribute("title", link.original_url); // título é atributo, não HTML

    if (link.original_url) {
      const aOriginal = document.createElement("a");
      aOriginal.href = sanitizeHref(link.original_url).href; // sanitizado — previne XSS
      aOriginal.target = "_blank";
      aOriginal.rel = "noopener noreferrer";
      aOriginal.textContent = truncateUrl(link.original_url, 50); // textContent — seguro
      // Acessibilidade: aria-label descritivo para leitores de tela
      aOriginal.setAttribute(
        "aria-label",
        `Abrir URL original: ${link.original_url}`,
      );
      tdOriginal.appendChild(aOriginal);
    } else {
      // URL sanitizada pelo backend (vazia) — exibir placeholder
      const span = document.createElement("span");
      span.textContent = "URL indisponível";
      span.className = "links-table__url-unavailable";
      tdOriginal.appendChild(span);
    }

    // Coluna: Link Curto
    const tdShort = document.createElement("td");
    tdShort.className = "links-table__short-url";
    const aShort = document.createElement("a");
    aShort.href = sanitizeHref(link.short_url).href; // sanitizado — previne XSS
    aShort.target = "_blank";
    aShort.rel = "noopener noreferrer";
    aShort.textContent = link.short_url; // textContent — seguro
    aShort.setAttribute("aria-label", `Abrir link curto: ${link.short_url}`);
    tdShort.appendChild(aShort);

    // Coluna: Cliques
    const tdClicks = document.createElement("td");
    tdClicks.className = "links-table__clicks";
    tdClicks.textContent = link.click_count; // textContent — seguro (número)

    // Coluna: Ação
    const tdAction = document.createElement("td");
    tdAction.className = "links-table__action";
    const btnCopy = document.createElement("button");
    btnCopy.type = "button";
    btnCopy.className = "btn-copy";
    btnCopy.textContent = "Copiar"; // textContent — seguro
    // Acessibilidade: aria-label único e descritivo por item
    btnCopy.setAttribute("aria-label", `Copiar link curto ${link.short_code}`);
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

// ————————————————————————————————————————————————————
// Carregamento de dados
// ————————————————————————————————————————————————————

/**
 * Busca links da sessão atual via GET /api/links.
 * Utiliza sessionStorage como cache (com validação estrutural).
 *
 * Resiliência: em caso de erro, mantém links já exibidos na tabela —
 * exibe banner de erro sem destruir o estado atual.
 */
export async function loadLinks() {
  // Tentar cache do sessionStorage primeiro (com validação de estrutura e TTL)
  const cached = getLinksFromCache();
  if (cached !== null) {
    renderLinks(cached);
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/links`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      // Erro HTTP — exibir banner sem destruir estado atual da tabela
      console.error("[links-panel] Erro na API:", response.status);
      showLinkError(
        "Não foi possível carregar os links. Tente novamente mais tarde.",
      );
      return;
    }

    const data = await response.json();

    // Esconder banner de erro anterior (recuperação bem-sucedida)
    hideLinkError();

    // Salvar no cache com TTL
    saveLinksToCache(data.links);

    renderLinks(data.links);
  } catch (err) {
    // Erro de rede (offline, timeout, etc.) — exibir banner sem destruir estado
    console.error("[links-panel] Falha ao carregar links:", err);
    showLinkError("Verifique sua conexão e tente novamente.");
  }
}

// ————————————————————————————————————————————————————
// Inicialização do módulo
// ————————————————————————————————————————————————————

/**
 * Inicializa o painel de links — ponto de entrada do módulo.
 * Chamado após lazy loading via IntersectionObserver ou trigger manual.
 */
export function initLinksPanel() {
  loadLinks();
}
