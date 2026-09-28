// @ts-check
import { defineConfig } from 'astro/config';
import vue from '@astrojs/vue';
import sitemap from '@astrojs/sitemap';

// Dominio final de la web (p. ej. https://sunnapilates.com).
// Se usa para las URL canónicas, Open Graph y el sitemap.
// Defínelo al desplegar: SITE_URL=https://tudominio.com npm run build
const site = process.env.SITE_URL;

export default defineConfig({
  site,
  output: 'static',
  integrations: [vue(), ...(site ? [sitemap({ filter: (url) => !url.includes('/login') })] : [])],
  i18n: {
    // Castellano en la apertura. Para añadir inglés: crea src/content/en/
    // (copiando src/content/es/) y la página src/pages/en/index.astro.
    defaultLocale: 'es',
    locales: ['es', 'en'],
    routing: { prefixDefaultLocale: false },
  },
});
