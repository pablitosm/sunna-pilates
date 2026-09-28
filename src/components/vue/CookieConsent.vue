<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue';

/*
 * Banner de consentimiento. Google Analytics y el píxel de Meta
 * solo se cargan después de que la persona los acepte.
 */
const props = defineProps<{
  gaId: string;
  pixelId: string;
  cookiesUrl: string;
  textos: {
    titulo: string;
    texto: string;
    aceptar: string;
    rechazar: string;
    configurar: string;
    guardar: string;
    analitica: { titulo: string; texto: string };
    marketing: { titulo: string; texto: string };
  };
}>();

const CLAVE = 'sunna-consent';
const visible = ref(false);
const detalle = ref(false);
const eleccion = reactive({ analitica: false, marketing: false });
let cargado = { analitica: false, marketing: false };

function leer(): { analitica: boolean; marketing: boolean } | null {
  try {
    const v = localStorage.getItem(CLAVE);
    return v ? JSON.parse(v) : null;
  } catch {
    return null;
  }
}

function guardar(analitica: boolean, marketing: boolean) {
  const anterior = { ...cargado };
  try {
    localStorage.setItem(CLAVE, JSON.stringify({ analitica, marketing, fecha: new Date().toISOString() }));
  } catch {
    /* sin almacenamiento: la elección vale solo para esta visita */
  }
  visible.value = false;
  // Retirar un consentimiento ya aplicado exige recargar para descargar los scripts.
  if ((anterior.analitica && !analitica) || (anterior.marketing && !marketing)) {
    location.reload();
    return;
  }
  aplicar(analitica, marketing);
}

function aplicar(analitica: boolean, marketing: boolean) {
  if (analitica && props.gaId && !cargado.analitica) {
    cargado.analitica = true;
    const s = document.createElement('script');
    s.async = true;
    s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(props.gaId)}`;
    document.head.appendChild(s);
    const w = window as unknown as { dataLayer: unknown[]; gtag: (...a: unknown[]) => void };
    w.dataLayer = w.dataLayer || [];
    w.gtag = function () {
      // eslint-disable-next-line prefer-rest-params
      w.dataLayer.push(arguments);
    };
    w.gtag('js', new Date());
    w.gtag('config', props.gaId, { anonymize_ip: true });
  }
  if (marketing && props.pixelId && !cargado.marketing) {
    cargado.marketing = true;
    /* Código base del píxel de Meta */
    const w = window as unknown as Record<string, any>;
    if (!w.fbq) {
      const n: any = function (...args: unknown[]) {
        n.callMethod ? n.callMethod(...args) : n.queue.push(args);
      };
      w.fbq = n;
      w._fbq = n;
      n.push = n;
      n.loaded = true;
      n.version = '2.0';
      n.queue = [];
      const s = document.createElement('script');
      s.async = true;
      s.src = 'https://connect.facebook.net/en_US/fbevents.js';
      document.head.appendChild(s);
    }
    w.fbq('init', props.pixelId);
    w.fbq('track', 'PageView');
  }
}

function abrirPreferencias(e: MouseEvent) {
  const t = (e.target as Element | null)?.closest?.('[data-open-cookies]');
  if (!t) return;
  e.preventDefault();
  const previa = leer();
  eleccion.analitica = previa?.analitica ?? false;
  eleccion.marketing = previa?.marketing ?? false;
  detalle.value = true;
  visible.value = true;
}

onMounted(() => {
  const previa = leer();
  if (previa) aplicar(previa.analitica, previa.marketing);
  else visible.value = true;
  document.addEventListener('click', abrirPreferencias);
});

onBeforeUnmount(() => document.removeEventListener('click', abrirPreferencias));
</script>

<template>
  <section v-if="visible" class="cookies" role="region" :aria-label="props.textos.titulo">
    <p class="cookies__texto">
      {{ props.textos.texto }}
      <a :href="props.cookiesUrl">{{ props.textos.titulo }}</a>
    </p>

    <div v-if="detalle" class="cookies__detalle">
      <label v-if="props.gaId" class="opcion">
        <input v-model="eleccion.analitica" type="checkbox" />
        <span>
          <strong>{{ props.textos.analitica.titulo }}</strong>
          {{ props.textos.analitica.texto }}
        </span>
      </label>
      <label v-if="props.pixelId" class="opcion">
        <input v-model="eleccion.marketing" type="checkbox" />
        <span>
          <strong>{{ props.textos.marketing.titulo }}</strong>
          {{ props.textos.marketing.texto }}
        </span>
      </label>
    </div>

    <div class="cookies__botones">
      <template v-if="detalle">
        <button type="button" class="boton" @click="guardar(eleccion.analitica, eleccion.marketing)">
          {{ props.textos.guardar }}
        </button>
      </template>
      <template v-else>
        <button type="button" class="boton" @click="guardar(false, false)">{{ props.textos.rechazar }}</button>
        <button type="button" class="boton" @click="guardar(true, true)">{{ props.textos.aceptar }}</button>
        <button type="button" class="boton boton--texto" @click="detalle = true">{{ props.textos.configurar }}</button>
      </template>
    </div>
  </section>
</template>

<style scoped>
.cookies {
  position: fixed;
  left: 1rem;
  bottom: 1rem;
  z-index: 50;
  width: min(calc(100% - 2rem), 27rem);
  padding: 1.25rem;
  border-radius: 20px;
  background: var(--n50);
  border: 1px solid var(--n200);
  box-shadow: var(--sombra);
  font-size: var(--t-small);
  line-height: 1.5;
  animation: aparecer 0.5s var(--ease);
}

@keyframes aparecer {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
}

.cookies__texto a {
  white-space: nowrap;
}

.cookies__detalle {
  display: grid;
  gap: 0.75rem;
  margin-top: 1rem;
}

.opcion {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  color: var(--tinta-60);
  cursor: pointer;
}

.opcion strong {
  display: block;
  font-weight: 500;
  color: var(--tinta);
}

.opcion input {
  flex: none;
  width: 1.125rem;
  height: 1.125rem;
  margin: 0.15rem 0 0;
  accent-color: var(--n900);
}

.cookies__botones {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
}

.boton {
  flex: 1 1 auto;
  min-height: 2.75rem;
  padding: 0 1.25rem;
  border: 0;
  border-radius: var(--r-pill);
  background: var(--tinta);
  color: var(--crema);
  font-weight: 500;
  cursor: pointer;
}

.boton--texto {
  flex: 0 0 auto;
  background: none;
  color: var(--tinta);
  text-decoration: underline;
  text-underline-offset: 0.22em;
  text-decoration-color: var(--n300);
}

@media (max-width: 56.25rem) {
  .cookies {
    left: 0.75rem;
    right: 0.75rem;
    bottom: calc(5.5rem + env(safe-area-inset-bottom));
    width: auto;
  }
}
</style>
