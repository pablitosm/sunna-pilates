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
