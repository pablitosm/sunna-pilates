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
  // El CSS va dentro de cada página: el navegador no espera a otros archivos para pintar
  build: { inlineStylesheets: 'always' },
  // El sitemap deja fuera el acceso y las páginas legales (que no se indexan)
  integrations: [
    vue(),
    ...(site
      ? [
          sitemap({
            // Las páginas legales de los cuatro idiomas (src/lib/content.ts → rutasLegales)
            filter: (url) =>
              !/\/(login|aviso-legal|privacidad|cookies|condiciones-membresia|legal-notice|privacy|membership-terms|impressum|datenschutz|mitgliedschaftsbedingungen|mentions-legales|confidentialite|conditions-abonnement)\/?$/.test(url),
          }),
        ]
      : []),
  ],
  i18n: {
    // Castellano en la raíz (/); inglés, alemán y francés en /en/, /de/ y /fr/.
    // Los textos de cada idioma viven en src/content/<idioma>/home.yaml.
    defaultLocale: 'es',
    locales: ['es', 'en', 'de', 'fr'],
    routing: { prefixDefaultLocale: false },
  },
});
