# Web de SUNNA

Web de SUNNA Pilates (Santa Cruz de Tenerife), hecha con [Astro](https://astro.build) y
[Vue](https://vuejs.org). Genera una web estática: carpeta `dist/` lista para subir a cualquier
hosting.

## Puesta en marcha

Requiere Node.js 22.12 o superior.

```bash
npm install
npm run dev        # desarrollo en http://localhost:4321
npm run build      # genera la web en dist/
npm run preview    # sirve dist/ en local para revisarla
```

Para el despliegue, define el dominio final al generar la web. Con él se crean las URL
canónicas y el `sitemap-index.xml`:

```bash
SITE_URL=https://tudominio.com npm run build
```

Sube el contenido de `dist/` a tu hosting. Cada página es una carpeta con su `index.html`
(`/privacidad/`), así que funciona en cualquier servidor sin configuración extra.

### Publicar en el servidor

`npm run deploy` compila con el dominio `sunnapilates.es` y sube `dist/` al servidor por
rsync (necesita tu acceso SSH). En el servidor, Apache atiende el HTTPS y hace reverse proxy a
Caddy en `127.0.0.1:8082`, que sirve `/var/www/sunnapilates`. Actualizar la web no requiere
tocar ni recargar Apache ni Caddy.

### Acceso privado

Mientras la web esté cerrada al público, solo entra el usuario `sunna` desde `/login`.
Sin sesión, cualquier página redirige al login. No hay base de datos: el servicio
`servidor/acceso.py` (sin dependencias) comprueba la contraseña, guardada como hash en
`/etc/sunnapilates-acceso.env` del servidor, y crea una cookie de sesión firmada que dura
30 días. Caddy le pregunta en cada petición (`forward_auth`). Para salir: `/auth/logout`.

- **Cambiar la contraseña:** en el servidor,
  `python3 /opt/sunnapilates-acceso/acceso.py hash`, escribe la nueva contraseña, copia el
  resultado en `ACCESO_HASH=` de `/etc/sunnapilates-acceso.env` y ejecuta
  `systemctl restart sunnapilates-acceso`.
- **Abrir la web al público:** en el bloque `http://:8082` del Caddyfile, quita la parte de
  `forward_auth` y la cabecera `X-Robots-Tag`. Después, `systemctl reload caddy`.

## Editar textos, precios y fotos

Todo el contenido está en `src/content/es/` y no hace falta tocar componentes:

| Archivo | Qué contiene |
| --- | --- |
| `ajustes.yaml` | Estado de la web, fecha de apertura, dirección, WhatsApp, Instagram, plazas de fundadores, analítica y SEO |
| `home.yaml` | Todos los textos de la home, en el orden de la página, incluidos los precios |
| `legal/*.md` | Aviso legal, privacidad, cookies y condiciones de membresía |

Las líneas que empiezan por `#` son notas. Las marcadas como **PENDIENTE** son datos que faltan
por cerrar. Si un dato está mal escrito, `npm run build` avisa con un mensaje de qué campo falla.

### Cambiar de preapertura a abierto

En `ajustes.yaml`, cambia `estado: preapertura` por `estado: abierto` y rellena
`reservas.primeraSesionUrl` con el enlace de bsport. El botón principal, el panel y el cierre
cambian solos.

### Fotos

La web funciona sin fotos: la portada, Recovery y El estudio usan formas del diseño
(arcos y sol). Para añadir una foto real, guárdala en `src/assets/fotos/` y quita las `#`
de las líneas `foto:` que hay en `home.yaml` para la portada y para Recovery. En El estudio,
añade `foto:` a cualquiera de los arcos. Astro la optimiza sola (AVIF/WebP, varios tamaños).

### Formulario de preapertura

`ajustes.yaml → formulario.endpoint`: la URL a la que se envían nombre, email, teléfono y
consentimiento (POST con `FormData`). Puede ser bsport, Brevo, Formspree o la herramienta que
elijáis. Mientras esté vacía, el formulario propone escribir por Instagram.

### Cookies y analítica

Rellena `medicion.googleAnalyticsId` y/o `medicion.metaPixelId`. Aparecerá el banner de
consentimiento y los scripts solo se cargarán si la persona acepta. El mapa de Google solo se
carga si se pulsa «Ver el mapa».

## Inglés

La estructura está preparada: copia `src/content/es/` en `src/content/en/`, traduce los textos y
crea `src/pages/en/index.astro` con el mismo contenido que `src/pages/index.astro`, cambiando
`getSite('es')` por `getSite('en')` y `lang="es"` por `lang="en"`.

## Estructura

```
src/
  content/es/        contenido editable (YAML y Markdown)
  components/        cabecera, pie, botón, iconos, huecos de foto
  components/secciones/   las 10 secciones de la home, en orden
  components/vue/    islas interactivas: panel de reserva, menú móvil, cookies
  layouts/Base.astro SEO, datos estructurados de negocio local, islas
  styles/global.css  tokens de diseño (colores, tipografía, radios, vidrio)
PRODUCT.md           contexto del producto (impeccable)
```
