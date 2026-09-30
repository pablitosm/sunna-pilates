/*
 * Movimiento: el punto del mapa pulsa una vez al entrar en pantalla.
 * Respeta prefers-reduced-motion.
 */

const reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* Pulso del mapa al entrar */
function alEntrar() {
  const elementos = document.querySelectorAll<HTMLElement>('[data-pulso]');
  if (reducido || !('IntersectionObserver' in window)) {
    elementos.forEach((e) => e.classList.add('pulsado'));
    return;
  }
  const io = new IntersectionObserver(
    (entradas) => {
      for (const e of entradas) {
        if (!e.isIntersecting) continue;
        e.target.classList.add('pulsado');
        io.unobserve(e.target);
      }
    },
    { threshold: 0.35 },
  );
  elementos.forEach((e) => io.observe(e));
}

alEntrar();
