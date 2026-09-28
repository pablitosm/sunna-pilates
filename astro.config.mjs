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
    // Castellano en la raíz (/); inglés, alemán y francés en /en/, /de/ y /fr/.
    // Los textos de cada idioma viven en src/content/<idioma>/home.yaml.
    defaultLocale: 'es',
    locales: ['es', 'en', 'de', 'fr'],
    routing: { prefixDefaultLocale: false },
  },
});
