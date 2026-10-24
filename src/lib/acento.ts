// Palabras acentuadas en los títulos: en los textos se marcan entre asteriscos
// ("Tu primera sesión es *gratis*.") y salen con la letra de acento y la pasada
// de rotulador (estilos .acento en global.css).

const escapar = (texto: string) =>
  texto.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/** HTML del título con las palabras marcadas envueltas en <em class="acento">. Para set:html. */
export const acentuar = (texto = '') => escapar(texto).replace(/\*([^*]+)\*/g, '<em class="acento">$1</em>');

/** El mismo texto sin los asteriscos, para donde va en texto plano (enlaces, <title>…). */
export const sinAcento = (texto = '') => texto.replace(/\*([^*]+)\*/g, '$1');
