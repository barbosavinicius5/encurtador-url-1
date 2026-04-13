# Componentes Críticos do Frontend — Lista Aprovada

> **Status:** Aprovado para implementação em T004
> **Arquivo de origem:** `scripts/app.js`

## Funções e Handlers Críticos

| Função/Handler           | Arquivo        | Tipo       | Responsabilidade                                                  |
|--------------------------|----------------|------------|-------------------------------------------------------------------|
| `isValidUrl`             | `scripts/app.js` | Pura       | Valida se a string é uma URL válida com protocolo http ou https   |
| `setLoading`             | `scripts/app.js` | DOM        | Ativa/desativa o estado de loading do botão de submit             |
| `showFieldError`         | `scripts/app.js` | DOM        | Exibe erro inline abaixo do input de URL                          |
| `showBannerError`        | `scripts/app.js` | DOM        | Exibe mensagem de erro no banner global                           |
| `clearErrors`            | `scripts/app.js` | DOM        | Limpa todos os estados de erro (field error + banner)             |
| `showResult`             | `scripts/app.js` | DOM        | Exibe a URL encurtada e ativa o botão de cópia                    |
| `shortenUrl`             | `scripts/app.js` | API        | Faz POST /api/shorten e retorna resultado (success/error)         |
| `truncateUrl`            | `scripts/app.js` | Pura       | Trunca URL longa para exibição na tabela de links                 |
| `copyWithFeedback`       | `scripts/app.js` | DOM/Async  | Copia URL para clipboard com feedback visual no botão da tabela   |
| `renderLinks`            | `scripts/app.js` | DOM        | Renderiza a tabela de links ou estado vazio no painel              |
| `loadLinks`              | `scripts/app.js` | API/Cache  | Busca links via GET /api/links com cache sessionStorage           |
| `copyBtn click handler`  | `scripts/app.js` | DOM/Async  | Copia URL encurtada para clipboard via navigator.clipboard        |
| `form submit handler`    | `scripts/app.js` | Integração | Coordena validação → loading → chamada API → exibição de resultado |
| `DOMContentLoaded handler` | `scripts/app.js` | Integração | Inicializa a página carregando links da sessão                    |

## Mapeamento de Elementos DOM

| ID do Elemento        | Tag         | Usado por                                                         |
|-----------------------|-------------|-------------------------------------------------------------------|
| `#shorten-form`       | `<form>`    | `form submit handler`                                             |
| `#url-input`          | `<input>`   | `isValidUrl`, `showFieldError`, `setLoading`, submit handler      |
| `#url-error`          | `<span>`    | `showFieldError`, `clearErrors`                                   |
| `#shorten-btn`        | `<button>`  | `setLoading`                                                      |
| `#error-banner`       | `<div>`     | `showBannerError`, `clearErrors`                                  |
| `#result-section`     | `<div>`     | `showResult`, `clearErrors`                                       |
| `#short-url-display`  | `<a>`       | `showResult`, `copyBtn click handler`                             |
| `#copy-btn`           | `<button>`  | `copyBtn click handler`, `showResult`                             |
| `#links-panel`        | `<section>` | `renderLinks`                                                     |
| `#empty-state`        | `<div>`     | `renderLinks`                                                     |
| `#links-table-wrapper`| `<div>`     | `renderLinks`                                                     |
| `#links-tbody`        | `<tbody>`   | `renderLinks`                                                     |

## Cenários de Teste por Tipo

### Funções Puras (sem DOM)
- `isValidUrl`: URL válida http, URL válida https, URL sem protocolo, string vazia, URL ftp
- `truncateUrl`: URL curta (sem truncar), URL longa (com truncar), exatamente no limite

### Funções DOM (dependem de elementos do HTML)
- `setLoading(true)`: botão desabilitado, texto alterado
- `setLoading(false)`: botão habilitado, texto restaurado
- `showFieldError`: texto visível, aria-invalid definido, foco no input
- `showBannerError`: texto visível no banner
- `clearErrors`: erros limpos, banner escondido
- `showResult`: URL exibida, seção visível

### Funções API (dependem de fetch)
- `shortenUrl`: status 201 → sucesso com short_url, status 422 → erro de validação, status 429 → rate limit, status 500 → erro genérico

### Handlers de Integração
- `form submit handler`: URL inválida → showFieldError, URL válida → loading → API → showResult
- `copyBtn click handler`: sucesso → texto copiado, falha clipboard → fallback
