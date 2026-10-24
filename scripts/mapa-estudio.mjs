/*
 * Genera src/components/MapaEstudio.astro: el mapa de la zona del estudio
 * dibujado con datos reales de OpenStreetMap (calles, parques, plazas, costa
 * y muelles) y pintado con los colores de la web. No carga nada de terceros.
 *
 *   node scripts/mapa-estudio.mjs            usa la descarga guardada (o la hace si no existe)
 *   node scripts/mapa-estudio.mjs --nuevo    vuelve a descargar los datos de OpenStreetMap
 *
 * Si cambia la dirección, actualiza PIN (y, si hace falta, el encuadre).
 * Datos © colaboradores de OpenStreetMap (ODbL): la atribución va junto al mapa (Estudio.astro).
 */
import { existsSync, readFileSync, writeFileSync } from 'node:fs';

// El estudio: C/ San Francisco Javier 5, Santa Cruz de Tenerife
const PIN = { lat: 28.47075, lon: -16.24915 };
// Encuadre: 1200 × 520 unidades. El estudio queda algo a la derecha del centro y el mar entra por la derecha.
const ANCHO = 1200;
const ALTO = 520;
const OESTE = -16.259;
const ESTE = -16.242;
const NORTE = PIN.lat + 0.0035;

const k = ANCHO / ((ESTE - OESTE) * Math.cos((PIN.lat * Math.PI) / 180));
const SUR = NORTE - ALTO / k;
const xy = ({ lat, lon }) => [(lon - OESTE) * Math.cos((PIN.lat * Math.PI) / 180) * k, (NORTE - lat) * k];
const f = (n) => Math.round(n);
// Solo lo que cae dentro del encuadre (con margen) entra en el dibujo
const dentro = (g) => g.some((p) => { const [x, y] = xy(p); return x > -60 && x < ANCHO + 60 && y > -60 && y < ALTO + 60; });

async function datos() {
  const guardado = new URL('../node_modules/.cache/mapa-estudio-osm.json', import.meta.url);
  if (existsSync(guardado) && !process.argv.includes('--nuevo')) return JSON.parse(readFileSync(guardado, 'utf8'));
  const m = 0.004;
  const caja = `${SUR - m},${OESTE - m},${NORTE + m},${ESTE + m}`;
  const consulta = `[out:json][timeout:60];(
    way["highway"](${caja});
    way["leisure"~"park|garden"](${caja});
    relation["leisure"="park"](${caja});
    way["landuse"="grass"](${caja});
    way["place"="square"](${caja});
    way["highway"="pedestrian"]["area"="yes"](${caja});
    way["man_made"~"pier|breakwater"](${caja});
    way["natural"="coastline"](28.44,-16.28,28.50,-16.22);
  );out geom;`;
  // Los servidores públicos de Overpass a veces fallan: se prueba en varios, con reintentos
  const servidores = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'];
  for (let intento = 0; intento < 6; intento++) {
    const url = servidores[intento % servidores.length];
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'User-Agent': 'sunna-web-mapa' },
      body: new URLSearchParams({ data: consulta }),
      signal: AbortSignal.timeout(90_000),
    }).catch(() => null);
    const texto = r?.ok ? await r.text() : '';
    if (texto.startsWith('{')) {
      writeFileSync(guardado, texto);
      return JSON.parse(texto);
    }
    await new Promise((listo) => setTimeout(listo, 3000));
  }
  throw new Error('OpenStreetMap (Overpass) no responde; prueba más tarde.');
}

const { elements } = await datos();
const tag = (e, t) => e.tags?.[t];
const linea = (g) =>
  g
    .map((p) => xy(p).map(f).join(' '))
    .filter((p, i, todos) => i === 0 || p !== todos[i - 1])
    .map((p, i) => `${i ? 'L' : 'M'}${p}`)
    .join('');
const area = (g) => `${linea(g)}Z`;

// Costa: se unen los tramos (la tierra queda a la izquierda del sentido del trazo) y el mar se cierra por el este
const tramos = elements.filter((e) => tag(e, 'natural') === 'coastline').map((e) => e.geometry);
const clave = (p) => `${p.lat.toFixed(7)},${p.lon.toFixed(7)}`;
const porInicio = new Map(tramos.map((t) => [clave(t[0]), t]));
const finales = new Set(tramos.map((t) => clave(t.at(-1))));
let costa = [];
for (const t of tramos) {
  if (finales.has(clave(t[0]))) continue; // solo empezamos por un extremo libre
  const cadena = [...t];
  let siguiente = porInicio.get(clave(t.at(-1)));
  while (siguiente && siguiente !== t) {
    cadena.push(...siguiente.slice(1));
    siguiente = porInicio.get(clave(siguiente.at(-1)));
  }
  if (cadena.length > costa.length) costa = cadena;
}
const lejos = 4000;
const [cx0, cy0] = xy(costa[0]);
const [cx1, cy1] = xy(costa.at(-1));
const mar = `${linea(costa)}L${f(cx1)} ${-lejos}L${lejos} ${-lejos}L${lejos} ${lejos}L${f(cx0)} ${lejos}Z`;

// Zonas verdes y plazas
const verdes = elements
  .filter((e) => e.type === 'way' && (/park|garden/.test(tag(e, 'leisure') ?? '') || tag(e, 'landuse') === 'grass'))
  .filter((e) => dentro(e.geometry))
  .map((e) => area(e.geometry));
const relVerdes = elements
  .filter((e) => e.type === 'relation' && e.members)
  .flatMap((e) => e.members.filter((m) => m.role !== 'inner' && m.geometry).map((m) => area(m.geometry)));
const plazas = elements
  .filter((e) => e.type === 'way' && (tag(e, 'place') === 'square' || (tag(e, 'highway') === 'pedestrian' && tag(e, 'area') === 'yes')))
  .filter((e) => dentro(e.geometry))
  .map((e) => area(e.geometry));
const muelles = elements.filter((e) => /pier|breakwater/.test(tag(e, 'man_made') ?? '') && dentro(e.geometry)).map((e) => linea(e.geometry));

// Calles por categoría
const grupo = (tipos) =>
  elements
    .filter((e) => e.type === 'way' && tipos.includes(tag(e, 'highway')) && tag(e, 'area') !== 'yes' && dentro(e.geometry))
    .map((e) => linea(e.geometry))
    .join('');
const principales = grupo(['primary', 'primary_link', 'secondary', 'secondary_link', 'trunk', 'trunk_link']);
const medias = grupo(['tertiary', 'tertiary_link', 'unclassified']);
const calles = grupo(['residential', 'living_street', 'pedestrian']);
const menores = grupo(['service', 'footway', 'path', 'steps', 'cycleway']);

// Nombres sobre su calle: el tramo más largo con ese nombre, en el sentido de lectura (de izquierda a derecha)
function trazoNombre(nombre) {
  const ways = elements.filter((e) => e.type === 'way' && tag(e, 'name') === nombre && tag(e, 'highway'));
  const g = ways.sort((a, b) => b.geometry.length - a.geometry.length)[0]?.geometry;
  if (!g) return '';
  const p = g.map(xy);
  return linea(p[0][0] > p.at(-1)[0] ? [...g].reverse() : g);
}

const [px, py] = xy(PIN).map(f);
const nombres = [
  ['san-francisco-javier', 'Calle San Francisco Javier', 'San Francisco Javier'],
  ['la-rosa', 'Calle de la Rosa', 'Calle de la Rosa'],
  ['rambla', 'Rambla de Santa Cruz', 'Rambla de Santa Cruz'],
].map(([id, nombre, texto]) => ({ id, d: trazoNombre(nombre), texto }));

// Etiquetas de lugares en el centro de su caja
function centro(nombre) {
  const e = elements.find((x) => tag(x, 'name') === nombre && x.bounds);
  if (!e) return null;
  return xy({ lat: (e.bounds.minlat + e.bounds.maxlat) / 2, lon: (e.bounds.minlon + e.bounds.maxlon) / 2 }).map(f);
}
const lugares = [
  ['Parque García Sanabria', centro('Parque García Sanabria')],
  ['Plaza del Príncipe', centro('Plaza del Príncipe de Asturias')],
].filter(([, c]) => c);

const salida = `---
/*
 * Mapa de la zona del estudio. GENERADO por scripts/mapa-estudio.mjs con datos
 * de OpenStreetMap: no editar a mano, volver a ejecutar el script.
 */
interface Props {
  class?: string;
}
const { class: className } = Astro.props;
---

<svg class:list={['mapa-osm', className]} viewBox="0 0 ${ANCHO} ${ALTO}" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
  <defs>
    <radialGradient id="mapa-osm-halo">
      <stop offset="0" style="stop-color: var(--sol-500)" stop-opacity="0.5" />
      <stop offset="1" style="stop-color: var(--sol-500)" stop-opacity="0" />
    </radialGradient>
${nombres.map((n) => `    <path id="mapa-osm-${n.id}" d="${n.d}" />`).join('\n')}
  </defs>
  <rect class="tierra" width="${ANCHO}" height="${ALTO}" />
  <path class="mar" d="${mar}" />
  <path class="plaza" d="${plazas.join('')}" />
  <path class="verde" d="${[...verdes, ...relVerdes].join('')}" />
  <path class="muelle" d="${muelles.join('')}" />
  <path class="menor" d="${menores}" />
  <path class="calle-borde" d="${calles}" />
  <path class="media-borde" d="${medias}" />
  <path class="principal-borde" d="${principales}" />
  <path class="calle" d="${calles}" />
  <path class="media" d="${medias}" />
  <path class="principal" d="${principales}" />
  <g class="nombres">
${nombres.map((n) => `    <text dy="4"><textPath href="#mapa-osm-${n.id}" startOffset="50%" text-anchor="middle">${n.texto}</textPath></text>`).join('\n')}
${lugares.map(([t, [x, y]]) => `    <text x="${x}" y="${y}" text-anchor="middle">${t}</text>`).join('\n')}
  </g>
  <circle cx="${px}" cy="${py}" r="80" fill="url(#mapa-osm-halo)" />
  <circle class="punto" cx="${px}" cy="${py}" r="11" />
  <g class="marca" transform="translate(${f(px + 26)} ${py})">
    <path d="M1 -7-8 0 1 7Z" />
    <rect x="0" y="-18" width="100" height="36" rx="18" />
    <text x="50" y="5" text-anchor="middle">SUNNA</text>
  </g>
</svg>

<style>
  .mapa-osm {
    display: block;
    width: 100%;
    height: 100%;
  }

  .tierra {
    fill: color-mix(in srgb, var(--sol-200) 30%, var(--tostado));
  }

  .mar {
    fill: color-mix(in srgb, var(--sol-300) 65%, var(--sol-100));
  }

  .plaza {
    fill: color-mix(in srgb, var(--sol-300) 32%, var(--tostado));
  }

  .verde {
    fill: var(--oliva);
    opacity: 0.85;
  }

  .muelle {
    fill: none;
    stroke: color-mix(in srgb, var(--sol-300) 32%, var(--tostado));
    stroke-width: 6;
  }

  .menor,
  .calle-borde,
  .media-borde,
  .principal-borde,
  .calle,
  .media,
  .principal {
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .menor {
    stroke: var(--sol-50);
    stroke-width: 1.5;
  }

  .calle-borde {
    stroke: none;
    stroke-width: 9;
  }

  .calle {
    stroke: var(--sol-50);
    stroke-width: 6.5;
  }

  .media-borde {
    stroke: none;
    stroke-width: 11;
  }

  .media {
    stroke: var(--sol-50);
    stroke-width: 8;
  }

  .principal-borde {
    stroke: none;
    stroke-width: 14;
  }

  .principal {
    stroke: var(--crema);
    stroke-width: 12;
  }

  .nombres {
    font: 400 11px var(--font);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    fill: var(--tinta-60);
    paint-order: stroke;
    stroke: color-mix(in srgb, var(--sol-200) 30%, var(--tostado));
    stroke-width: 4;
    stroke-linejoin: round;
  }

  .punto {
    fill: var(--n500);
    stroke: var(--sol-200);
    stroke-width: 4;
  }

  .marca path,
  .marca rect {
    fill: var(--n700);
  }

  .marca text {
    font: 400 14px var(--font);
    letter-spacing: 0.16em;
    fill: var(--crema);
  }
</style>
`;

writeFileSync(new URL('../src/components/MapaEstudio.astro', import.meta.url), salida);
console.log('src/components/MapaEstudio.astro', { k: f(k), sur: SUR.toFixed(5), costa: costa.length });
