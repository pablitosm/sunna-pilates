/*
 * /llms.txt: resumen de SUNNA en Markdown para modelos de lenguaje (ChatGPT, Claude, Perplexity…),
 * según la propuesta de llmstxt.org. Se genera al construir la web con los mismos textos que la
 * web (home.yaml y ajustes.yaml), así que nunca se queda atrás: no hay que editarlo a mano.
 */
import type { APIRoute } from 'astro';
import { sinAcento } from '../lib/acento';
import { direccionCompleta, getSite, idiomas, nombresIdioma, urlPagina, whatsappUrl, type Pagina } from '../lib/content';
import { conHorario } from '../lib/horario';

export const GET: APIRoute = async ({ site }) => {
  const { ajustes, home } = await getSite('es');
  const url = (ruta: string) => (site ? new URL(ruta, site).href : ruta);
  const rellenar = (t: string) => conHorario(t, ajustes, 'es').replaceAll('{direccion}', direccionCompleta(ajustes));
  const sn = home.sobreNosotros;
  const wa = whatsappUrl(ajustes.contacto.whatsapp);

  const paginas: [Pagina | undefined, string][] = [
    [undefined, 'Inicio: qué es SUNNA, cómo funciona, horario y preguntas frecuentes'],
    ['sobre-nosotros', 'Sobre nosotros: SUNNA en datos'],
    ['primera-sesion', 'Primera sesión gratis'],
    ['precios', 'Precios y membresías'],
    ['reformer', 'El reformer y las clases'],
    ['sauna', 'Sauna de infrarrojos'],
    ['luz-roja', 'Sala de luz roja'],
  ];

  const faq = home.faq.grupos.flatMap((g) =>
    g.preguntas
      .map((p) => ({ pregunta: p.pregunta, respuesta: conHorario((ajustes.horario === 'ampliado' && p.respuestaAmpliado) || p.respuesta, ajustes, 'es') }))
      .filter((p) => p.respuesta.trim()),
  );

  const lineas = [
    '# SUNNA Pilates',
    '',
    `> ${sn ? rellenar(sn.texto) : home.seo.descripcion}`,
    '',
    `Estudio de Pilates Reformer en ${ajustes.direccion.ciudad} (Tenerife, Islas Canarias, España). ${home.seo.descripcion}`,
    '',
    '## Datos',
    '',
    ...(sn ? sn.datos.map((d) => `- **${d.nombre}:** ${rellenar(d.valor)}`) : []),
    `- **Tipos de clase:** ${home.clases.tipos.join(', ')}.`,
    `- **Precios:** ${home.precios.membresias.map((m) => `${m.nombre} ${m.precio} €/mes (${m.pilates}; ${m.recovery})`).join(' · ')}.`,
    `- **Idiomas de la web:** ${idiomas.map((l) => `${nombresIdioma[l]} (${url(urlPagina(l))})`).join(', ')}.`,
    '',
    '## Contacto',
    '',
    `- Dirección: ${direccionCompleta(ajustes)}`,
    ...(wa ? [`- WhatsApp: ${ajustes.contacto.whatsapp} (${wa})`] : []),
    ...(ajustes.contacto.email ? [`- Email: ${ajustes.contacto.email}`] : []),
    ...(ajustes.contacto.instagram ? [`- Instagram: ${ajustes.contacto.instagram}`] : []),
    ...(ajustes.contacto.googleBusiness ? [`- Google: ${ajustes.contacto.googleBusiness}`] : []),
    '',
    '## Páginas',
    '',
    ...paginas.map(([p, texto]) => `- [${texto}](${url(urlPagina('es', p))})`),
    '',
    '## Preguntas frecuentes',
    '',
    ...[...(sn?.preguntas ?? []).map((p) => ({ pregunta: p.pregunta, respuesta: rellenar(p.respuesta) })), ...faq]
      .filter((p) => p.respuesta.trim())
      .flatMap((p) => [`### ${sinAcento(p.pregunta)}`, '', p.respuesta, '']),
  ];

  return new Response(lineas.join('\n'), { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
