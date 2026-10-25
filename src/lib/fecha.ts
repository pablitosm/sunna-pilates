import type { Lang } from './content';

// Formato regional de cada idioma (en-GB: «15 November», no «November 15»)
const regiones: Record<Lang, string> = { es: 'es-ES', en: 'en-GB', de: 'de-DE', fr: 'fr-FR' };

/** Fecha ISO de ajustes.yaml («2026-11-15») en cada idioma: «15 de noviembre», «15 November»,
 *  «15. November», «15 novembre». Vacía, nada. */
export function fechaLarga(iso: string, lang: Lang) {
  if (!iso) return '';
  return new Intl.DateTimeFormat(regiones[lang], { day: 'numeric', month: 'long', timeZone: 'UTC' }).format(new Date(`${iso}T00:00:00Z`));
}
