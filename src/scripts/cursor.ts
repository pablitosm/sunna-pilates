/*
 * Cursor de la lámina (del diseño de referencia): punto de 8 px Naranja 500 y
 * halo de vidrio de 32 px que lo sigue acercándose un 22 % por fotograma.
 * Enlaces: 56 px teñido al 15 %. Fotos: 96 px con «ver». CTA: 132 × 52 con «reservar».
 * Sobre texto corrido vuelve la barra del sistema.
 * Solo con ratón y si <html data-cursor="on"> (ajustes.yaml → cursorPersonalizado,
 * o el interruptor de desarrollo).
 */

const reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const conRaton = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

function cursor() {
  if (!conRaton || reducido || document.documentElement.dataset.cursor !== 'on') return;
  const punto = document.createElement('div');
  const halo = document.createElement('div');
  const texto = document.createElement('span');
  punto.className = 'cursor-punto';
  halo.className = 'cursor-halo';
  halo.appendChild(texto);
  document.body.append(halo, punto);
  document.documentElement.classList.add('con-cursor');

  const tgt = { x: -200, y: -200 };
  const pos = { x: -200, y: -200 };
  let modo: string | null = null;

  const formas: Record<string, [number, number, string, string, number]> = {
    link: [56, 56, 'rgba(255,130,53,.15)', '', 14],
    photo: [96, 96, 'rgba(255,241,230,.25)', 'ver', 14],
    cta: [132, 52, 'rgba(255,130,53,.22)', 'reservar', 15],
    base: [32, 32, 'transparent', '', 14],
  };

  const aplicar = (m: string | null) => {
    const [w, h, bg, txt, fs] = formas[m ?? 'base'] ?? formas.base;
    halo.style.width = `${w}px`;
    halo.style.height = `${h}px`;
    halo.style.margin = `${-h / 2}px 0 0 ${-w / 2}px`;
    halo.style.backgroundColor = bg;
    texto.textContent = txt;
    texto.style.opacity = txt ? '1' : '0';
    texto.style.fontSize = `${fs}px`;
  };
  aplicar(null);

  document.addEventListener(
    'mousemove',
    (e) => {
      tgt.x = e.clientX;
      tgt.y = e.clientY;
      const el = e.target as Element | null;
      const t = el?.closest?.('[data-cur], a, button, summary, label, input');
      const m = t ? t.getAttribute('data-cur') || 'link' : null;
      // Sobre texto corrido vuelve el cursor del sistema
      const enTexto = !t && !!el?.closest?.('p, li, dd, dt, address, h1, h2, h3, blockquote, td, th');
      document.documentElement.classList.toggle('cursor-texto', enTexto);
      if (m !== modo) {
        modo = m;
        aplicar(m);
      }
    },
    { passive: true },
  );

  document.documentElement.addEventListener('mouseleave', () => {
    tgt.x = -200;
    tgt.y = -200;
  });

  // Los <dialog> abiertos viven en la capa superior: el cursor se mete dentro.
  const recolocar = () => {
    const destino = document.querySelector('dialog[open]') ?? document.body;
    if (halo.parentElement !== destino) destino.append(halo, punto);
  };
  new MutationObserver(recolocar).observe(document.body, {
    subtree: true,
    attributes: true,
    attributeFilter: ['open'],
  });

  const tick = () => {
    pos.x += (tgt.x - pos.x) * 0.22;
    pos.y += (tgt.y - pos.y) * 0.22;
    punto.style.transform = `translate(${tgt.x}px, ${tgt.y}px)`;
    halo.style.transform = `translate(${pos.x}px, ${pos.y}px)`;
    requestAnimationFrame(tick);
  };
  tick();
}

cursor();
