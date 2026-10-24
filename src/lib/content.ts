import { getEntry, type CollectionEntry } from 'astro:content';

export const idiomas = ['es', 'en', 'de', 'fr'] as const;
export type Lang = (typeof idiomas)[number];

/** Nombre de cada idioma en su propia lengua (selector de idioma). */
export const nombresIdioma: Record<Lang, string> = {
  es: 'Castellano',
  en: 'English',
  de: 'Deutsch',
  fr: 'Français',
};

/** Portada de cada idioma: castellano en la raíz, el resto en /en/, /de/, /fr/. */
export const raizIdioma = (lang: Lang) => (lang === 'es' ? '/' : `/${lang}/`);

/** Páginas propias además de la portada: la primera sesión, los precios y cada espacio. */
export const paginas = ['primera-sesion', 'precios', 'reformer', 'luz-roja', 'sauna'] as const;
export type Pagina = (typeof paginas)[number];

/** Dirección de cada página en cada idioma (sin el prefijo del idioma). */
export const rutas: Record<Lang, Record<Pagina, string>> = {
  es: { 'primera-sesion': 'primera-sesion', precios: 'precios', reformer: 'reformer', 'luz-roja': 'luz-roja', sauna: 'sauna' },
  en: { 'primera-sesion': 'first-session', precios: 'pricing', reformer: 'reformer', 'luz-roja': 'red-light', sauna: 'sauna' },
  de: { 'primera-sesion': 'erste-session', precios: 'preise', reformer: 'reformer', 'luz-roja': 'rotlicht', sauna: 'sauna' },
  fr: { 'primera-sesion': 'premiere-seance', precios: 'tarifs', reformer: 'reformer', 'luz-roja': 'lumiere-rouge', sauna: 'sauna' },
};

/** Enlace a una página en un idioma; sin página, la portada de ese idioma. */
export const urlPagina = (lang: Lang, pagina?: Pagina) =>
  pagina ? `${raizIdioma(lang)}${rutas[lang][pagina]}/` : raizIdioma(lang);

/** Idioma de la página que se está generando (Astro.currentLocale). */
export const idiomaDe = (locale: string | undefined): Lang =>
  (idiomas as readonly string[]).includes(locale ?? '') ? (locale as Lang) : 'es';

export const localeOg: Record<Lang, string> = { es: 'es_ES', en: 'en_GB', de: 'de_DE', fr: 'fr_FR' };
export type Ajustes = CollectionEntry<'ajustes'>['data'];

// Color del navegador en móvil (theme-color): el fondo crema de cada paleta
export const colorTema: Record<Ajustes['paleta'], string> = { naranja: '#fdf6ee', salvia: '#f6f2ea', arena: '#f7f3ec', oliva: '#f7f4ec', cacao: '#f8f3ec' };
export type Home = CollectionEntry<'home'>['data'];
export type Estado = Ajustes['estado'];

let avisado = false;

export async function getSite(lang: Lang = 'es') {
  // Los ajustes (estado, dirección, enlaces…) son los mismos en todos los idiomas.
  const ajustes = await getEntry('ajustes', 'es/ajustes');
  const home = await getEntry('home', `${lang}/home`);
  if (!ajustes || !home) {
    throw new Error(
      `No se ha podido leer el contenido de "${lang}" (src/content/es/ajustes.yaml y src/content/${lang}/home.yaml). ` +
        'Suele ser un campo que falta o mal escrito: el detalle aparece justo encima en la terminal. ' +
        'Si ya lo has corregido, reinicia el servidor (npx astro dev stop y npm run dev).',
    );
  }
  if (!avisado && ajustes.data.estado === 'preapertura' && !ajustes.data.formulario.endpoint) {
    avisado = true;
    console.warn(
      '\n[SUNNA] Antes de publicar: el formulario de preapertura no tiene endpoint (ajustes.yaml → formulario.endpoint). Las inscripciones no se guardarán.\n',
    );
  }
  return { ajustes: ajustes.data, home: home.data, lang };
}

export function whatsappUrl(numero: string, mensaje = '') {
  const digitos = numero.replace(/\D/g, '');
  if (!digitos) return '';
  return `https://wa.me/${digitos}${mensaje ? `?text=${encodeURIComponent(mensaje)}` : ''}`;
}

export function direccionCompleta(a: Ajustes) {
  const d = a.direccion;
  return `${d.calle}, ${d.codigoPostal} ${d.ciudad}`;
}

export function mapsUrl(a: Ajustes) {
  return (
    a.contacto.googleBusiness ||
    `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`SUNNA Pilates, ${direccionCompleta(a)}`)}`
  );
}

/** Plazas de socio fundador libres (nunca más que las totales). */
export function plazasFundador(a: Ajustes) {
  return Math.min(a.fundadores.plazasLibres, a.fundadores.plazasTotales);
}

/** Quedan plazas de socio fundador y la oferta está a la vista (ajustes.yaml → fundadores). */
export function hayPlazasFundador(a: Ajustes) {
  return a.fundadores.mostrar && plazasFundador(a) > 0;
}

/** Botón principal abierto: mientras quedan plazas de fundador, lleva a la oferta de fundadores. */
export function ctaEsFundador(a: Ajustes) {
  return a.estado === 'abierto' && hayPlazasFundador(a);
}

/**
 * Destino del botón principal. Abierto: la página de la primera sesión gratis,
 * que explica la sesión y lleva a la app, a bsport o a WhatsApp. Preapertura:
 * abre el panel de lista de espera (sin JavaScript, el bloque de fundadores).
 */
export function ctaHref(a: Ajustes, lang: Lang = 'es') {
  if (ctaEsFundador(a)) return `${urlPagina(lang, 'precios')}#fundadores`;
  if (a.estado === 'abierto') return urlPagina(lang, 'primera-sesion');
  return a.fundadores.mostrar ? `${urlPagina(lang, 'precios')}#fundadores` : '#cierre';
}
