<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
  links: { texto: string; href: string; hijos?: { texto: string; href: string }[] }[];
  whatsapp: string;
  whatsappTexto: string;
  instagram: string;
  cerrar: string;
  abrirMenu: string;
  menu: string;
  navegacion: string;
  idiomaTitulo: string;
  idiomas: { codigo: string; nombre: string; href: string; actual: boolean }[];
  inicio: string;
  irInicio: string;
}>();

const dialogo = ref<HTMLDialogElement | null>(null);
const abierto = ref(false);

// Pantalla completa: mientras está abierto, la página de detrás no se desplaza
function abrir() {
  dialogo.value?.showModal();
  document.documentElement.style.overflow = 'hidden';
  abierto.value = true;
}

function cerrarMenu() {
  dialogo.value?.close();
}

// Misma cookie que el selector de la cabecera (la lee el servidor).
function recordarIdioma(codigo: string) {
  document.cookie = `sunna-idioma=${codigo}; path=/; max-age=31536000; samesite=lax`;
}

function alCerrar() {
  document.documentElement.style.overflow = '';
  abierto.value = false;
}
</script>

<template>
  <button
    type="button"
    class="menu-boton"
    :aria-expanded="abierto"
    aria-controls="menu-movil"
    :aria-label="props.abrirMenu"
    @click="abrir"
  >
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true">
      <path d="M4.5 9h15M4.5 15h15" />
    </svg>
  </button>

  <!-- Menú a pantalla completa sobre crema: la cabecera se queda donde está (logo y,
       en el sitio del botón de menú, el de cerrar) y debajo van los enlaces en filas -->
  <dialog id="menu-movil" ref="dialogo" class="menu" :aria-label="props.menu" @close="alCerrar">
    <div class="menu__barra">
      <a class="menu__logo" :href="props.inicio" :aria-label="props.irInicio" @click="cerrarMenu"><slot /></a>
      <button type="button" class="menu__cerrar" :aria-label="props.cerrar" @click="cerrarMenu">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true">
          <path d="m6.75 6.75 10.5 10.5M17.25 6.75 6.75 17.25" />
        </svg>
      </button>
    </div>

    <div class="menu__cuerpo">
      <nav :aria-label="props.navegacion">
        <ul role="list" class="menu__lista">
          <li v-for="l in props.links" :key="l.href">
            <a :href="l.href" class="menu__enlace" @click="cerrarMenu">{{ l.texto }}</a>
            <ul v-if="l.hijos?.length" role="list" class="menu__sublista">
              <li v-for="h in l.hijos" :key="h.href">
                <a :href="h.href" @click="cerrarMenu">{{ h.texto }}</a>
              </li>
            </ul>
          </li>
        </ul>
      </nav>

      <div class="menu__pie">
        <nav class="menu__idiomas" :aria-label="props.idiomaTitulo">
          <ul role="list">
            <li v-for="i in props.idiomas" :key="i.codigo">
              <a
                :href="i.href"
                :hreflang="i.codigo"
                :lang="i.codigo"
                :title="i.nombre"
                :aria-label="i.nombre"
                :aria-current="i.actual ? 'page' : undefined"
                @click="recordarIdioma(i.codigo)"
                >{{ i.codigo.toUpperCase() }}</a
              >
            </li>
          </ul>
        </nav>
        <ul role="list" class="menu__contacto">
          <li v-if="props.whatsapp">
            <a :href="props.whatsapp" target="_blank" rel="noopener">{{ props.whatsappTexto }}</a>
          </li>
          <li v-if="props.instagram">
            <a :href="props.instagram" target="_blank" rel="noopener">Instagram</a>
          </li>
        </ul>
      </div>
    </div>
  </dialog>
</template>

<style scoped>
.menu-boton,
.menu__cerrar {
  display: none;
  place-items: center;
  width: 2.75rem;
  height: 2.75rem;
  border: 0;
  border-radius: 50%;
  background: var(--n50);
  color: var(--tinta);
  cursor: pointer;
  box-shadow: inset 0 0 0 1px var(--n100);
}

.menu__cerrar {
  display: grid;
}

@media (max-width: 68rem) {
  .menu-boton {
    display: grid;
  }
}

/* Pantalla completa, crema sólida, sin velo, sin sombra y sin esquinas */
.menu {
  width: 100%;
  max-width: none;
  height: 100dvh;
  max-height: none;
  margin: 0;
  padding: 0;
  border: 0;
  background: var(--crema);
  color: var(--tinta);
}

.menu[open] {
  display: flex;
  flex-direction: column;
}

.menu::backdrop {
  background: var(--crema);
}

/* La misma barra que la cabecera: logo a la izquierda, cerrar a la derecha */
.menu__barra {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.625rem max(var(--gutter), (100% - var(--ancho)) / 2);
  border-bottom: 1px solid var(--linea);
}

.menu__logo {
  display: block;
  height: 22px;
}

.menu__logo :deep(.logo) {
  width: auto;
  height: 100%;
}

.menu__cuerpo {
  flex: 1;
  display: flex;
  flex-direction: column;
  width: min(100% - 2 * var(--gutter), var(--ancho));
  margin-inline: auto;
  padding: 1.5rem 0 calc(1.5rem + env(safe-area-inset-bottom));
  overflow-y: auto;
}

/* Enlaces en filas grandes, entre líneas finas */
.menu__lista > li {
  border-bottom: 1px solid var(--linea);
}

.menu__enlace {
  display: block;
  padding: 0.875rem 0;
  font-size: clamp(1.75rem, 1.4rem + 1.5vw, 2.25rem);
  line-height: 1.1;
  letter-spacing: -0.025em;
  text-decoration: none;
}

/* Los espacios, en una línea debajo de su enlace */
.menu__sublista {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1.25rem;
  margin: -0.25rem 0 1rem;
}

.menu__sublista a {
  font-size: 1.0625rem;
  color: var(--tinta-60);
  text-decoration: underline;
  text-decoration-color: var(--n200);
  text-underline-offset: 0.25em;
}

.menu__enlace:hover,
.menu__sublista a:hover {
  color: var(--n900);
}

/* Idiomas y contacto, abajo del todo */
.menu__pie {
  margin-top: auto;
  padding-top: 2.5rem;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem 2rem;
}

.menu__idiomas ul {
  display: flex;
  gap: 1.25rem;
}

.menu__idiomas a {
  font-size: 0.9375rem;
  letter-spacing: 0.08em;
  color: var(--tinta-60);
  text-decoration: none;
}

.menu__idiomas a[aria-current='page'] {
  color: var(--tinta);
  text-decoration: underline;
  text-decoration-color: var(--n500);
  text-decoration-thickness: 1.5px;
  text-underline-offset: 0.35em;
}

.menu__contacto {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.5rem;
  font-size: 0.9375rem;
}

.menu__contacto a {
  color: var(--n900);
}
</style>
