<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
  links: { texto: string; href: string }[];
  whatsapp: string;
  whatsappTexto: string;
  instagram: string;
  cerrar: string;
}>();

const dialogo = ref<HTMLDialogElement | null>(null);
const abierto = ref(false);

function abrir() {
  dialogo.value?.showModal();
  abierto.value = true;
}

function cerrarMenu() {
  dialogo.value?.close();
}

function alCerrar() {
  abierto.value = false;
}

function alPulsarFondo(e: MouseEvent) {
  if (e.target === dialogo.value) cerrarMenu();
}
</script>

<template>
  <button
    type="button"
    class="menu-boton"
    :aria-expanded="abierto"
    aria-controls="menu-movil"
    aria-label="Abrir menú"
    @click="abrir"
  >
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true">
      <path d="M4.5 9h15M4.5 15h15" />
    </svg>
  </button>

  <dialog id="menu-movil" ref="dialogo" class="menu" aria-label="Menú" @close="alCerrar" @click="alPulsarFondo">
    <div class="menu__hoja">
      <button type="button" class="menu__cerrar" :aria-label="props.cerrar" @click="cerrarMenu">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true">
          <path d="m6.25 6.25 11.5 11.5M17.75 6.25 6.25 17.75" />
        </svg>
      </button>
      <nav aria-label="Principal">
        <ul role="list" class="menu__lista">
          <li v-for="l in props.links" :key="l.href">
            <a :href="l.href" @click="cerrarMenu">{{ l.texto }}</a>
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
  </dialog>
</template>

<style scoped>
.menu-boton {
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

@media (max-width: 56.25rem) {
  .menu-boton {
    display: grid;
  }
}

.menu {
  width: 100%;
  max-width: none;
  height: 100%;
  max-height: none;
  margin: 0;
  padding: 0.75rem var(--gutter);
  border: 0;
  background: transparent;
  color: var(--tinta);
}

.menu::backdrop {
  background: rgb(253 246 238 / 0.55);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
}

.menu__hoja {
  position: relative;
  padding: 4.5rem 1.5rem 2rem;
  border-radius: var(--r-l);
  background: var(--n50);
  border: 1px solid var(--n100);
  box-shadow: var(--sombra);
  transform-origin: top right;
  animation: estirar 0.42s var(--ease);
}

@keyframes estirar {
  from {
    opacity: 0;
    transform: scale(0.92) translateY(-8px);
    border-radius: 999px;
  }
}

.menu__cerrar {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  display: grid;
  place-items: center;
  width: 2.75rem;
  height: 2.75rem;
  border: 0;
  border-radius: 50%;
  background: var(--crema);
  color: var(--tinta);
  cursor: pointer;
}

.menu__lista {
  display: grid;
  gap: 0.25rem;
}

.menu__lista a {
  display: block;
  padding: 0.4rem 0;
  font-size: 2.25rem;
  line-height: 1.15;
  letter-spacing: -0.03em;
  text-decoration: none;
}

.menu__contacto {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.5rem;
  margin-top: 2rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--linea);
  color: var(--tinta-60);
}
</style>
