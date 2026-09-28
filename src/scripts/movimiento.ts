/*
 * Movimiento de la home (notas de movimiento del diseño de referencia).
 * Todo respeta prefers-reduced-motion: sin desplazamientos, el contenido
 * aparece directamente.
 */

const html = document.documentElement;
const reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const conRaton = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
const escritorio = window.matchMedia('(min-width: 64rem)');

/* 01 · Titular por líneas con máscara, 40 ms de desfase */
function titularPorLineas() {
  const titulo = document.querySelector<HTMLElement>('.portada__titulo');
  if (!titulo) return;
  if (reducido || !html.classList.contains('js-lineas')) {
    html.classList.remove('js-lineas');
    return;
  }
  const palabras = (titulo.textContent ?? '').trim().split(/\s+/);
  titulo.innerHTML = palabras.map((p) => `<span class="palabra">${p}</span>`).join(' ');
  const spans = [...titulo.querySelectorAll<HTMLElement>('.palabra')];
  const lineas: string[][] = [];
  let top = -1;
  for (const s of spans) {
    if (s.offsetTop !== top) {
      lineas.push([]);
      top = s.offsetTop;
    }
    lineas[lineas.length - 1].push(s.textContent ?? '');
  }
  const retraso = html.classList.contains('ya-cargado') ? 0 : 700;
  titulo.innerHTML = lineas
    .map(
      (l, i) =>
        `<span class="linea"><span class="linea__in" style="animation-delay:${retraso + i * 40}ms">${l.join(' ')}</span></span>`,
    )
    .join('');
  titulo.setAttribute('aria-label', palabras.join(' '));
  html.classList.remove('js-lineas');
}

/* Iconos que trazan su línea al entrar (60 ms de desfase) y pulso del mapa */
function alEntrar() {
  const elementos = document.querySelectorAll<HTMLElement>('[data-trazar], [data-pulso]');
  if (reducido || !('IntersectionObserver' in window)) {
    elementos.forEach((e) => e.classList.add('trazado', 'pulsado'));
    return;
  }
  const io = new IntersectionObserver(
    (entradas) => {
      for (const e of entradas) {
        if (!e.isIntersecting) continue;
        e.target.classList.add('trazado', 'pulsado');
        io.unobserve(e.target);
      }
    },
    { threshold: 0.35 },
  );
  elementos.forEach((e) => io.observe(e));
}

/* Cabecera: al bajar se compacta (el logo mantiene su tamaño) */
function cabeceraCompacta() {
  const cabecera = document.querySelector<HTMLElement>('[data-cabecera]');
  if (!cabecera) return;
  const pintar = () => cabecera.classList.toggle('es-compacta', window.scrollY > 24);
  pintar();
  window.addEventListener('scroll', pintar, { passive: true });
}

/* 01 · Parallax del portal de la portada, 8 % máximo */
function parallaxPortada() {
  const portal = document.querySelector<HTMLElement>('.portada__portal, .portada__foto');
  if (!portal || reducido) return;
  let pendiente = false;
  const pintar = () => {
    pendiente = false;
    const max = portal.offsetHeight * 0.08;
    const y = Math.min(window.scrollY * 0.08, max);
    portal.style.transform = `translate3d(0, ${y}px, 0)`;
  };
  window.addEventListener(
    'scroll',
    () => {
      if (!pendiente) {
        pendiente = true;
        requestAnimationFrame(pintar);
      }
    },
    { passive: true },
  );
}

/* 03 · Cómo funciona: sección anclada, los pasos avanzan en horizontal */
function seccionAnclada() {
  const seccion = document.querySelector<HTMLElement>('[data-como]');
  const anclaje = seccion?.querySelector<HTMLElement>('[data-anclaje]');
  const pista = seccion?.querySelector<HTMLElement>('[data-pista]');
  if (!seccion || !anclaje || !pista || reducido) return;

  let distancia = 0;
  let pendiente = false;

  const medir = () => {
    const activo = escritorio.matches;
    seccion.classList.toggle('como--anclado', activo);
    if (!activo) {
      pista.style.transform = '';
      anclaje.style.removeProperty('--alto-anclaje');
      return;
    }
    distancia = Math.max(0, pista.scrollWidth - window.innerWidth);
    anclaje.style.setProperty('--alto-anclaje', `${window.innerHeight + distancia}px`);
    pintar();
  };

  const pintar = () => {
    pendiente = false;
    if (!seccion.classList.contains('como--anclado')) return;
    const inicio = anclaje.getBoundingClientRect().top;
    const progreso = Math.min(1, Math.max(0, -inicio / Math.max(1, distancia)));
    pista.style.transform = `translate3d(${-progreso * distancia}px, 0, 0)`;
  };

  window.addEventListener(
    'scroll',
    () => {
      if (!pendiente) {
        pendiente = true;
        requestAnimationFrame(pintar);
      }
    },
    { passive: true },
  );
  window.addEventListener('resize', medir);
  escritorio.addEventListener('change', medir);
  medir();
}

/* 03 · Tarjetas magnéticas: 4 px hacia el cursor */
function tarjetasMagneticas() {
  if (!conRaton || reducido) return;
  document.querySelectorAll<HTMLElement>('[data-iman]').forEach((t) => {
    t.addEventListener('mousemove', (e) => {
      const r = t.getBoundingClientRect();
      const x = ((e.clientX - r.left) / r.width - 0.5) * 8;
      const y = ((e.clientY - r.top) / r.height - 0.5) * 8;
      t.style.setProperty('--iman-x', `${x.toFixed(2)}px`);
      t.style.setProperty('--iman-y', `${y.toFixed(2)}px`);
    });
    t.addEventListener('mouseleave', () => {
      t.style.removeProperty('--iman-x');
      t.style.removeProperty('--iman-y');
    });
  });
}

titularPorLineas();
alEntrar();
cabeceraCompacta();
parallaxPortada();
seccionAnclada();
tarjetasMagneticas();
