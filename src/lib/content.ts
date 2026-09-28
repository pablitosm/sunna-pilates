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

export const localeOg: Record<Lang, string> = { es: 'es_ES', en: 'en_GB', de: 'de_DE', fr: 'fr_FR' };
export type Ajustes = CollectionEntry<'ajustes'>['data'];
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

export function mapsEmbedUrl(a: Ajustes) {
  return `https://www.google.com/maps?q=${encodeURIComponent(direccionCompleta(a))}&output=embed`;
}

/** Destino del botón principal cuando no hay JavaScript o el panel no se abre. */
export function ctaHref(a: Ajustes) {
  if (a.estado === 'abierto' && a.reservas.primeraSesionUrl) return a.reservas.primeraSesionUrl;
  return a.estado === 'preapertura' && a.fundadores.mostrar ? '#fundadores' : '#cierre';
}
