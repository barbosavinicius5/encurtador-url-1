/** @type {import('jest').Config} */
module.exports = {
  testEnvironment: 'jsdom',
  testMatch: ['**/tests/**/*.test.js'],
  // Nota: app.js usa o DOM diretamente no nível de módulo (não é um módulo ES puro),
  // portanto não pode ser importado diretamente no contexto de teste.
  // O coverage é coletado dos arquivos de teste que exercitam a lógica via DOM.
};
