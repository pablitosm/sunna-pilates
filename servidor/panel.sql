-- Base de datos del panel de SUNNA (PostgreSQL 10+).
-- Se aplica con: python3 panel.py esquema   (es idempotente).

CREATE TABLE IF NOT EXISTS administradores (
  id            serial PRIMARY KEY,
  usuario       text NOT NULL UNIQUE,
  hash          text NOT NULL,              -- pbkdf2$iteraciones$sal$hash
  creado        timestamptz NOT NULL DEFAULT now(),
  ultimo_acceso timestamptz
);

-- Personas que se apuntan desde el formulario de la web (lista de espera / socios fundadores).
CREATE TABLE IF NOT EXISTS registros (
  id              serial PRIMARY KEY,
  nombre          text NOT NULL,
  email           text NOT NULL,
  telefono        text NOT NULL DEFAULT '',
  idioma          text NOT NULL DEFAULT 'es',
  ip              text NOT NULL DEFAULT '',
  consentimiento  timestamptz NOT NULL,     -- cuándo aceptó la política de privacidad
  creado          timestamptz NOT NULL DEFAULT now()
);

-- Un email solo se guarda una vez (sin distinguir mayúsculas).
CREATE UNIQUE INDEX IF NOT EXISTS registros_email_unico ON registros (lower(email));
CREATE INDEX IF NOT EXISTS registros_creado ON registros (creado DESC);

-- Analítica propia de la web, sin cookies: vistas de página, clics, apartados vistos y tiempo.
-- No guarda la IP: «visitante» es una huella anónima que cambia cada día (HMAC de fecha, IP y
-- navegador con el secreto del panel), así se cuentan personas únicas por día sin seguir a nadie.
CREATE TABLE IF NOT EXISTS eventos (
  id           bigserial PRIMARY KEY,
  creado       timestamptz NOT NULL DEFAULT now(),
  tipo         text NOT NULL,                -- vista | clic | seccion | salida
  vista        text NOT NULL DEFAULT '',     -- id aleatorio de la vista de página (agrupa sus eventos)
  visitante    text NOT NULL,
  ruta         text NOT NULL,                -- /precios/, /en/sauna/…
  pagina       text NOT NULL DEFAULT '',     -- inicio, precios, primera-sesion… (igual en los 4 idiomas)
  idioma       text NOT NULL DEFAULT 'es',
  dispositivo  text NOT NULL DEFAULT '',     -- movil | tableta | escritorio
  fuente       text NOT NULL DEFAULT '',     -- vista: de dónde llega (Google, Instagram, Directo…)
  nombre       text NOT NULL DEFAULT '',     -- clic: destino (whatsapp, /precios/…); seccion: id del apartado
  etiqueta     text NOT NULL DEFAULT '',     -- clic: texto del botón o enlace
  zona         text NOT NULL DEFAULT '',     -- clic: dónde estaba (cabecera, pie, portada, precios…)
  objetivo     boolean NOT NULL DEFAULT false, -- clic en un botón de reservar (CTA, WhatsApp, apps)
  segundos     integer,                      -- salida: tiempo con la página visible
  profundidad  smallint                      -- salida: porcentaje de la página recorrido
);

CREATE INDEX IF NOT EXISTS eventos_creado ON eventos (creado DESC);
CREATE INDEX IF NOT EXISTS eventos_tipo_creado ON eventos (tipo, creado DESC);
