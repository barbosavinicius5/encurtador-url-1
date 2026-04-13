/**
 * Helper para configurar o DOM mínimo necessário para testar app.js
 *
 * Deve ser chamado no beforeEach de cada suite que testa funções DOM.
 */

/**
 * Configura o document.body com os elementos mínimos que app.js espera encontrar.
 */
export function setupDOM() {
  document.body.innerHTML = `
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

    <section id="links-panel" class="links-panel" hidden>
      <div id="empty-state" class="empty-state hidden">
        <p>Você ainda não tem links encurtados.</p>
      </div>
      <div id="links-table-wrapper" class="hidden">
        <table>
          <tbody id="links-tbody"></tbody>
        </table>
      </div>
    </section>
  `;
}

/**
 * Limpa o document.body após os testes.
 */
export function teardownDOM() {
  document.body.innerHTML = '';
}
