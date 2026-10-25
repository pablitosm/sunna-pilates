/** Iconos de «Cómo funciona» con dibujo propio (la carta) y pegatina (la píldora). Cualquier otro
 *  icono cae en el glifo de trazo en los dos sitios. */
export const iconosConDibujo = ['arco', 'pantalla', 'punto', 'reserva'] as const;
export const tieneDibujo = (icono: string) => (iconosConDibujo as readonly string[]).includes(icono);
