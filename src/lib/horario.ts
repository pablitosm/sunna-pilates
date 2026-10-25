/**
 * Horario del estudio: los tramos se escriben una sola vez en ajustes.yaml (horarios) y de aquí
 * salen el bloque de horario, el pie, el dibujo de «Por qué SUNNA» y los textos con {horario}.
 */
import type { Ajustes, Lang } from './content';

/** Los tramos de la fase vigente (ajustes.yaml → horario), como [desde, hasta]. */
export const tramosHorario = (a: Ajustes) =>
  a.horarios[a.horario].map((t) => t.split('-') as [string, string]);

/** Cada tramo en corto: «08:00–14:00». */
export const tramosCortos = (a: Ajustes, separador = '–') =>
  tramosHorario(a).map(([desde, hasta]) => `${desde}${separador}${hasta}`);

// Cómo se dice un tramo dentro de una frase en cada idioma
const enFrase: Record<Lang, (desde: string, hasta: string) => string> = {
  es: (d, h) => `de ${d} a ${h}`,
  fr: (d, h) => `de ${d} à ${h}`,
  en: (d, h) => `${d}–${h}`,
  de: (d, h) => `${d}–${h}`,
};

/** El horario como frase: «de 08:00 a 14:00 y de 16:00 a 22:00», «08:00–14:00 and 16:00–22:00». */
export const fraseHorario = (a: Ajustes, lang: Lang) =>
  new Intl.ListFormat(lang, { type: 'conjunction' }).format(tramosHorario(a).map(([d, h]) => enFrase[lang](d, h)));

/** Cambia {horario} de un texto por la frase; si el texto empieza por ella, en mayúscula. */
export function conHorario(texto: string, a: Ajustes, lang: Lang) {
  if (!texto.includes('{horario}')) return texto;
  const frase = fraseHorario(a, lang);
  const inicial = texto.startsWith('{horario}') ? frase.charAt(0).toUpperCase() + frase.slice(1) : frase;
  return texto.replace('{horario}', inicial).replaceAll('{horario}', frase);
}
