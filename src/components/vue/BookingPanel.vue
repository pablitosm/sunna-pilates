<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue';

type Estado = 'preapertura' | 'abierto';

interface TextosPreapertura {
  titulo: string;
  texto: string;
  campos: { nombre: string; email: string; telefono: string };
  consentimiento: string;
  privacidad: string;
  enviar: string;
  enviando: string;
  exitoTitulo: string;
  exitoTexto: string;
  error: string;
  sinConexion: string;
  sinConexionSinContacto: string;
  pie: string;
}

const props = defineProps<{
  estado: Estado;
  endpoint: string;
  reservaUrl: string;
  whatsapp: string;
  instagram: string;
  privacidadUrl: string;
  textos: {
    preapertura: TextosPreapertura;
    abierto: { titulo: string; texto: string; boton: string; widget: string };
    whatsapp: string;
    cerrar: string;
  };
}>();

const dialogo = ref<HTMLDialogElement | null>(null);
const primerCampo = ref<HTMLInputElement | null>(null);
const envio = ref<'inicial' | 'enviando' | 'exito' | 'error' | 'sinConexion'>('inicial');
const datos = reactive({ nombre: '', email: '', telefono: '', consentimiento: false, web: '' });

function abrir(desde?: Element | null) {
  const d = dialogo.value;
  if (!d || d.open) return;
  d.showModal();
  document.body.classList.add('panel-abierto');
  if (props.estado === 'preapertura' && envio.value !== 'exito') {
    requestAnimationFrame(() => primerCampo.value?.focus());
  }
}

function cerrar() {
  const d = dialogo.value;
  if (d?.open) d.close();
}

function alCancelar(e: Event) {
  e.preventDefault();
  cerrar();
}

function alCerrar() {
  document.body.classList.remove('panel-abierto');
}

function alPulsarFondo(e: MouseEvent) {
  if (e.target === dialogo.value) cerrar();
}

function alPulsarDocumento(e: MouseEvent) {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  const disparador = (e.target as Element | null)?.closest?.('[data-open-booking]');
  if (!disparador) return;
  e.preventDefault();
  abrir(disparador);
}

async function enviar() {
  if (datos.web) return; // campo trampa para bots
  if (!props.endpoint) {
    envio.value = 'sinConexion';
    return;
  }
  envio.value = 'enviando';
  try {
    const cuerpo = new FormData();
    cuerpo.append('nombre', datos.nombre.trim());
    cuerpo.append('email', datos.email.trim());
    cuerpo.append('telefono', datos.telefono.trim());
    cuerpo.append('consentimiento', datos.consentimiento ? 'si' : 'no');
    cuerpo.append('origen', 'web-preapertura');
    const r = await fetch(props.endpoint, { method: 'POST', body: cuerpo, headers: { Accept: 'application/json' } });
    envio.value = r.ok ? 'exito' : 'error';
  } catch {
    envio.value = 'error';
  }
}

onMounted(() => {
  document.addEventListener('click', alPulsarDocumento);
  if (location.hash === '#reservar') abrir();
});

onBeforeUnmount(() => document.removeEventListener('click', alPulsarDocumento));
</script>

<template>
  <dialog
    ref="dialogo"
    class="panel"
    aria-labelledby="panel-titulo"
    @close="alCerrar"
    @cancel="alCancelar"
    @click="alPulsarFondo"
  >
    <div class="panel__hoja">
      <button type="button" class="panel__cerrar" :aria-label="props.textos.cerrar" @click="cerrar">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true">
          <path d="m6.25 6.25 11.5 11.5M17.75 6.25 6.25 17.75" />
        </svg>
      </button>

      <!-- Antes de abrir: lista de espera / socios fundadores -->
      <template v-if="props.estado === 'preapertura'">
        <div v-if="envio === 'exito'" class="panel__exito" role="status">
          <span class="panel__sol" aria-hidden="true"></span>
          <h2 id="panel-titulo" class="panel__titulo">{{ props.textos.preapertura.exitoTitulo }}</h2>
          <p class="panel__texto">{{ props.textos.preapertura.exitoTexto }}</p>
        </div>

        <template v-else>
          <h2 id="panel-titulo" class="panel__titulo">{{ props.textos.preapertura.titulo }}</h2>
          <p class="panel__texto">{{ props.textos.preapertura.texto }}</p>

          <form class="formulario" @submit.prevent="enviar">
            <label class="campo">
              <span class="campo__icono" aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="8.5" r="3.75" /><path d="M4.75 20c.75-3.75 3.6-5.75 7.25-5.75S18.5 16.25 19.25 20" /></svg>
              </span>
              <span class="campo__cuerpo">
                <span class="campo__etiqueta">{{ props.textos.preapertura.campos.nombre }}</span>
                <input ref="primerCampo" v-model="datos.nombre" name="nombre" type="text" autocomplete="name" required maxlength="80" />
              </span>
            </label>

            <label class="campo">
              <span class="campo__icono" aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3.75" y="5.75" width="16.5" height="12.5" rx="2.25" /><path d="m4.5 7 7.5 6 7.5-6" /></svg>
              </span>
              <span class="campo__cuerpo">
                <span class="campo__etiqueta">{{ props.textos.preapertura.campos.email }}</span>
                <input v-model="datos.email" name="email" type="email" autocomplete="email" inputmode="email" required maxlength="120" />
              </span>
            </label>

            <label class="campo">
              <span class="campo__icono" aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="6.75" y="2.75" width="10.5" height="18.5" rx="2.5" /><path d="M11 18h2" /></svg>
              </span>
              <span class="campo__cuerpo">
                <span class="campo__etiqueta">{{ props.textos.preapertura.campos.telefono }}</span>
                <input
                  v-model="datos.telefono"
                  name="telefono"
                  type="tel"
                  autocomplete="tel"
                  inputmode="tel"
                  required
                  minlength="9"
                  maxlength="20"
                  pattern="[0-9+ \(\)\-]{9,20}"
                />
              </span>
            </label>

            <label class="consentimiento">
              <input v-model="datos.consentimiento" type="checkbox" name="consentimiento" required />
              <span>
                {{ props.textos.preapertura.consentimiento }}
                <a :href="props.privacidadUrl" target="_blank" rel="noopener">{{ props.textos.preapertura.privacidad }}</a>
              </span>
            </label>

            <label class="trampa" aria-hidden="true">
              Web <input v-model="datos.web" type="text" name="web" tabindex="-1" autocomplete="off" />
            </label>

            <button class="enviar" type="submit" :disabled="envio === 'enviando'">
              <span>{{ envio === 'enviando' ? props.textos.preapertura.enviando : props.textos.preapertura.enviar }}</span>
              <span class="enviar__circulo" aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 12h14.25M13.5 6.75 18.75 12l-5.25 5.25" /></svg>
              </span>
            </button>

            <p v-if="envio === 'error'" class="aviso aviso--error" role="alert">{{ props.textos.preapertura.error }}</p>
            <p v-if="envio === 'sinConexion'" class="aviso" role="alert">
              {{ props.whatsapp ? props.textos.preapertura.sinConexion : props.textos.preapertura.sinConexionSinContacto }}
              <a v-if="props.whatsapp" :href="props.whatsapp" target="_blank" rel="noopener">WhatsApp</a>
              <a v-else-if="props.instagram" :href="props.instagram" target="_blank" rel="noopener">@sunnapilates</a>
            </p>
            <p v-if="props.textos.preapertura.pie" class="panel__pie">{{ props.textos.preapertura.pie }}</p>
          </form>
        </template>
      </template>

      <!-- Tras abrir: primera sesión gratis en bsport -->
      <template v-else>
        <h2 id="panel-titulo" class="panel__titulo">{{ props.textos.abierto.titulo }}</h2>
        <p class="panel__texto">{{ props.textos.abierto.texto }}</p>
        <div class="widget" :class="{ 'widget--solo': !props.textos.abierto.widget }">
          <p v-if="props.textos.abierto.widget">{{ props.textos.abierto.widget }}</p>
          <a v-if="props.reservaUrl" class="enviar" :href="props.reservaUrl" target="_blank" rel="noopener">
            <span>{{ props.textos.abierto.boton }}</span>
            <span class="enviar__circulo" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 12h14.25M13.5 6.75 18.75 12l-5.25 5.25" /></svg>
            </span>
          </a>
        </div>
      </template>

      <a v-if="props.whatsapp" class="panel__wa" :href="props.whatsapp" target="_blank" rel="noopener">
        {{ props.textos.whatsapp }}
      </a>
    </div>
  </dialog>
</template>

<style scoped>
.panel {
  position: fixed;
  inset: 0 0 0 auto;
  width: min(100%, 35rem);
  max-width: none;
  height: 100%;
  max-height: none;
  margin: 0;
  padding: 0.75rem;
  border: 0;
  background: transparent;
  color: var(--tinta);
  overflow: visible;
}

.panel::backdrop {
  background: rgb(var(--tinta-rgb) / 0.28);
}

.panel__hoja {
  position: relative;
  height: 100%;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: clamp(2rem, 1.5rem + 2vw, 3rem) clamp(1.5rem, 1rem + 2vw, 2.75rem) 2rem;
  border-radius: var(--r);
  background:
    radial-gradient(90% 55% at 100% 0%, rgb(var(--n200-rgb) / 0.55), transparent 70%),
    var(--crema);
  border: 1px solid var(--n100);
  box-shadow: var(--sombra);
}

@media (max-width: 40rem) {
  .panel {
    inset: auto 0 0 0;
    width: 100%;
    height: auto;
    max-height: 100%;
    padding: 0.5rem;
  }
  .panel__hoja {
    height: auto;
    max-height: calc(100dvh - 1rem);
    padding-bottom: calc(1.5rem + env(safe-area-inset-bottom));
  }
}

.panel__cerrar {
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: grid;
  place-items: center;
  width: 2.75rem;
  height: 2.75rem;
  border: 0;
  border-radius: 50%;
  background: var(--n50);
  box-shadow: inset 0 0 0 1px var(--n100);
  color: var(--tinta);
  cursor: pointer;
}

.panel__titulo {
  max-width: 14ch;
  font-size: clamp(2rem, 1.6rem + 1.8vw, 2.75rem);
  line-height: 1.06;
  letter-spacing: -0.03em;
  font-weight: 450;
}

.panel__texto {
  margin-top: 1rem;
  max-width: 40ch;
  color: var(--tinta-60);
}

.formulario {
  display: grid;
  gap: 0.75rem;
  margin-top: 2rem;
}

.campo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 1.25rem 0.4rem 0.45rem;
  border-radius: var(--r-pill);
  background: #fff;
  box-shadow: inset 0 0 0 1px var(--n100);
  cursor: text;
  transition: box-shadow 0.25s var(--ease);
}

.campo:focus-within {
  box-shadow:
    inset 0 0 0 1px var(--n300),
    0 0 0 3px var(--n500);
}

.campo__icono {
  display: grid;
  place-items: center;
  flex: none;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background: var(--n50);
  color: var(--n900);
}

.campo__cuerpo {
  display: grid;
  flex: 1;
  min-width: 0;
}

.campo__etiqueta {
  font-size: 0.75rem;
  color: var(--tinta-60);
  line-height: 1.2;
}

.campo input {
  width: 100%;
  padding: 0.1rem 0 0.2rem;
  border: 0;
  background: transparent;
  font-size: 1rem;
  outline: none;
}

.campo:has(input:user-invalid) {
  box-shadow: inset 0 0 0 1px var(--n900);
}

.consentimiento {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  margin-top: 0.5rem;
  font-size: var(--t-small);
  line-height: 1.5;
  color: var(--tinta-60);
  cursor: pointer;
}

.consentimiento input {
  flex: none;
  width: 1.25rem;
  height: 1.25rem;
  margin: 0.1rem 0 0;
  accent-color: var(--n900);
}

.trampa {
  position: absolute;
  left: -9999px;
}

.enviar {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
  min-height: 3.5rem;
  margin-top: 0.75rem;
  padding: 0 0.3rem 0 1.5rem;
  border: 0;
  border-radius: var(--r-pill);
  background: var(--boton, var(--n500));
  color: var(--boton-tinta, var(--tinta));
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  box-shadow: var(--sombra-boton);
  transition: background-color 0.3s var(--ease);
}

.enviar:hover {
  background: var(--boton-hover, var(--n300));
}

.enviar:disabled {
  background: var(--n200);
  cursor: progress;
}

.enviar__circulo {
  display: grid;
  place-items: center;
  width: 2.9rem;
  height: 2.9rem;
  border-radius: 50%;
  background: var(--boton-circulo-fondo, radial-gradient(circle at 35% 30%, var(--n300), var(--n500) 70%));
  color: var(--boton-circulo-tinta, inherit);
}

.aviso {
  padding: 0.875rem 1.125rem;
  border-radius: var(--r);
  background: var(--n50);
  font-size: var(--t-small);
}

.aviso--error {
  background: var(--aviso-error);
  color: var(--n900);
}

.panel__pie {
  font-size: var(--t-small);
  color: var(--tinta-60);
}

.panel__wa {
  display: inline-block;
  margin-top: 2rem;
  font-size: var(--t-small);
  color: var(--tinta-60);
}

.panel__exito {
  padding-top: 2rem;
}

.panel__sol {
  display: block;
  width: 5rem;
  height: 5rem;
  margin-bottom: 2rem;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, var(--sol-300), var(--sol-500) 60%, transparent 72%);
  filter: blur(0.5px);
  box-shadow: 0 0 60px 20px rgb(var(--sol-500-rgb) / 0.35);
}


.widget.widget--solo {
  min-height: 0;
  padding: 0;
  border: 0;
  background: none;
}

.widget {
  display: grid;
  gap: 1rem;
  margin-top: 2rem;
  padding: 1.5rem;
  min-height: 16rem;
  align-content: center;
  border-radius: var(--r);
  background: var(--n50);
  border: 1px dashed var(--n200);
  color: var(--tinta-60);
  font-size: var(--t-small);
}
</style>
