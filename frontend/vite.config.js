import { defineConfig } from 'vite';

export default defineConfig(({ mode }) => ({
  build: {
    target: 'esnext',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
    rollupOptions: {
      output: {
        manualChunks: {
          // chunks serão adicionados conforme módulos criados em T002
        },
      },
    },
  },
}));
