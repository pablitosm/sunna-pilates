#!/usr/bin/env python3
"""
Panel de administración de SUNNA.

Sirve el panel en /panel (con su propio inicio de sesión de administrador) y
recibe los registros del formulario de la web en POST /api/registro.
Los datos viven en PostgreSQL (esquema en panel.sql).

Apartados:
  /panel             Resumen: cifras y últimos registros.
  /panel/registros   Quién se ha registrado; búsqueda, CSV y borrado.
  /panel/usuarios    Administradores: crear, cambiar contraseña, borrar.

Configuración en /etc/sunnapilates-panel.env:
  PANEL_DSN            cadena de conexión de Postgres
                       (p. ej. "host=127.0.0.1 dbname=sunna user=sunna_web password=…")
  PANEL_SECRETO        clave para firmar las sesiones (aleatoria, larga)
  PANEL_COOKIE_SEGURA  1 cuando la web va por HTTPS
  PANEL_PUERTO         puerto local (por defecto 8084)

Comandos (en el servidor):
  python3 panel.py esquema                 crea las tablas (idempotente)
  python3 panel.py crear-admin USUARIO     crea o actualiza un administrador;
                                           la contraseña se lee de la entrada estándar
Requiere psycopg2 (apt install python3-psycopg2). Python 3.6+.
"""
import base64
import csv
import hashlib
import hmac
import html
import io
import json
import os
import re
import secrets
import socketserver
import sys
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote, urlsplit

DSN = os.environ.get("PANEL_DSN", "")
SECRETO = os.environ.get("PANEL_SECRETO", "").encode()
COOKIE_SEGURA = os.environ.get("PANEL_COOKIE_SEGURA", "0") == "1"
PUERTO = int(os.environ.get("PANEL_PUERTO", "8084"))
COOKIE = "sunna_panel"
DURACION = 12 * 3600  # la sesión del panel dura 12 horas
ITERACIONES = 310000
IDIOMAS = ("es", "en", "de", "fr")

# Frenos: inicios de sesión fallidos y registros por IP en una ventana de tiempo.
VENTANA = 15 * 60
MAX_FALLOS = 10
MAX_REGISTROS = 20
fallos = {}
envios = {}


# ─── Base de datos ──────────────────────────────────────────────

def conectar():
    import psycopg2  # se importa aquí para poder usar "hash" y la ayuda sin psycopg2

    conexion = psycopg2.connect(DSN)
    conexion.autocommit = True
    return conexion


class BD:
    """Conexión abierta bajo demanda; cada petición abre la suya y la cierra al terminar."""

    def __init__(self):
        self.conexion = None

    def cursor(self):
        if self.conexion is None or self.conexion.closed:
            self.conexion = conectar()
        return self.conexion.cursor()

    def cerrar(self):
        if self.conexion is not None and not self.conexion.closed:
            self.conexion.close()

    def uno(self, sql, args=()):
        with self.cursor() as c:
            c.execute(sql, args)
            return c.fetchone()

    def todos(self, sql, args=()):
        with self.cursor() as c:
            c.execute(sql, args)
            return c.fetchall()

    def ejecutar(self, sql, args=()):
        with self.cursor() as c:
            c.execute(sql, args)
            return c.rowcount


# ─── Contraseñas y sesiones ─────────────────────────────────────

def generar_hash(password, iteraciones=ITERACIONES):
    sal = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), sal, iteraciones)
    return "pbkdf2${}${}${}".format(iteraciones, sal.hex(), h.hex())


def comprobar_hash(password, guardado):
    try:
        _, iteraciones, sal, esperado = guardado.split("$")
        calculado = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), int(iteraciones))
        return hmac.compare_digest(calculado.hex(), esperado)
    except Exception:
        return False


# Hash de relleno: si el usuario no existe se comprueba igual (mismo tiempo de respuesta).
HASH_RELLENO = generar_hash(secrets.token_hex(16))


def firma(datos):
    return base64.urlsafe_b64encode(hmac.new(SECRETO, datos.encode(), hashlib.sha256).digest()).decode().rstrip("=")


def crear_token(admin_id):
    datos = "{}:{}".format(admin_id, int(time.time()) + DURACION)
    return datos + "." + firma(datos)


def leer_token(token):
    """Devuelve el id del administrador si el token es válido y no ha caducado."""
    if not token or "." not in token:
        return None
    datos, recibida = token.rsplit(".", 1)
    if not hmac.compare_digest(firma(datos), recibida):
        return None
    try:
        admin_id, caduca = datos.split(":")
        return int(admin_id) if int(caduca) > time.time() else None
    except ValueError:
        return None


def token_csrf(token):
    return firma("csrf:" + token)


def leer_cookie(cabecera, nombre):
    for trozo in (cabecera or "").split(";"):
        clave, _, valor = trozo.strip().partition("=")
        if clave == nombre:
            return valor
    return ""


def limitar(registro, clave, maximo):
    """True si la clave ya ha superado el máximo de intentos en la ventana."""
    ahora = time.time()
    recientes = [t for t in registro.get(clave, []) if ahora - t < VENTANA]
    registro[clave] = recientes
    return len(recientes) >= maximo


def anotar(registro, clave):
    registro.setdefault(clave, []).append(time.time())


# ─── Utilidades de presentación ─────────────────────────────────

def e(texto):
    return html.escape("" if texto is None else str(texto), quote=True)


def fecha(valor, con_hora=True):
    """Fecha en hora de Canarias (Europe/Atlantic/Canary: UTC+0 en invierno, UTC+1 en verano)."""
    if not valor:
        return "—"
    utc = valor.astimezone(timezone.utc)
    # Horario de verano europeo: del último domingo de marzo al último domingo de octubre, a la 01:00 UTC.
    def ultimo_domingo(anio, mes):
        d = datetime(anio, mes + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        return d - timedelta(days=(d.weekday() + 1) % 7)

    inicio = ultimo_domingo(utc.year, 3).replace(hour=1)
    fin = ultimo_domingo(utc.year, 10).replace(hour=1)
    local = utc + timedelta(hours=1 if inicio <= utc < fin else 0)
    return local.strftime("%d/%m/%Y %H:%M" if con_hora else "%d/%m/%Y")


TELEFONO = re.compile(r"^\+?[\d\s().-]+$")


def texto_csv(valor):
    """Evita que Excel interprete un campo como fórmula (los teléfonos se dejan tal cual)."""
    valor = "" if valor is None else str(valor)
    if valor and valor[0] in "=+-@" and not TELEFONO.match(valor):
        return "'" + valor
    return valor


def cargar_logo():
    """Logotipo original de SUNNA (copiado junto a panel.py como sunna-logo.svg)."""
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sunna-logo.svg")
    try:
        with open(ruta, encoding="utf-8") as f:
            svg = f.read().strip()
        return svg.replace("<svg ", '<svg class="logo" role="img" aria-label="SUNNA" ', 1)
    except OSError:
        return '<span class="logo-texto">SUNNA</span>'


LOGO = cargar_logo()

# Favicon de la web (public/favicon.svg): icono de la pestaña y avatar del usuario.
FAVICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" '
           'fill="#FDF6EE"/><circle cx="32" cy="32" r="20" fill="#FF8235"/></svg>')
FAVICON_URL = "data:image/svg+xml," + quote(FAVICON)

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USUARIO = re.compile(r"^[a-zA-Z0-9._-]{3,40}$")


# ─── Páginas ────────────────────────────────────────────────────

ESTILOS = """
:root{--fondo:#f6f7f9;--blanco:#fff;--borde:#e4e7ec;--borde-fuerte:#d0d5dd;--texto:#1d2939;--suave:#667085;
--naranja:#ff8235;--naranja-hover:#f0701f;--naranja-claro:#fff4ec;--rojo:#d92d20;--rojo-claro:#fef3f2;
--verde-claro:#ecfdf3;--verde:#067647;--r:6px;--r-g:8px}
*{box-sizing:border-box;margin:0}
body{font-family:'Inter',ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;background:var(--fondo);
color:var(--texto);font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:inherit}
.marco{display:grid;grid-template-columns:15rem minmax(0,1fr);min-height:100vh}
.lateral{position:sticky;top:0;height:100vh;display:flex;flex-direction:column;background:var(--blanco);
border-right:1px solid var(--borde)}
.marca{display:flex;align-items:center;gap:.625rem;height:3.75rem;padding:0 1.25rem;border-bottom:1px solid var(--borde);
font-weight:600;letter-spacing:.08em}
.marca .logo{display:block;width:auto;height:1.125rem}
.logo-texto{font-weight:600;letter-spacing:.08em}
.nav{display:grid;gap:2px;padding:.75rem}
.nav a{display:flex;align-items:center;gap:.625rem;padding:.5rem .75rem;border-radius:var(--r);
text-decoration:none;color:var(--suave);font-weight:500}
.nav a:hover{background:var(--fondo);color:var(--texto)}
.nav a[aria-current=page]{background:var(--naranja-claro);color:var(--texto)}
.nav a[aria-current=page] svg{color:var(--naranja)}
.nav svg{flex:none}
.lateral__pie{margin-top:auto;display:flex;align-items:center;justify-content:space-between;gap:.5rem;
padding:1rem 1.25rem;border-top:1px solid var(--borde);font-size:.8125rem;color:var(--suave)}
.usuario{display:flex;align-items:center;gap:.5rem;min-width:0;font-weight:500;color:var(--texto)}
.usuario img{flex:none;border-radius:6px}
.lateral__pie a{color:var(--suave);font-weight:500;text-decoration:none}
.lateral__pie a:hover{color:var(--naranja-hover)}
.principal{padding:2rem clamp(1rem,3vw,2.5rem) 3rem;min-width:0}
.cabeza{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:1rem;margin-bottom:1.5rem}
h1{font-size:1.5rem;font-weight:600;letter-spacing:-.01em;line-height:1.2}
h2{font-size:1rem;font-weight:600}
.sub{margin-top:.25rem;color:var(--suave)}
.etiqueta{font-size:.8125rem;font-weight:500;color:var(--suave)}
.cifras{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));gap:1rem;margin-bottom:1.5rem}
.cifra{padding:1.125rem 1.25rem;border:1px solid var(--borde);border-radius:var(--r-g);background:var(--blanco)}
.cifra strong{display:block;margin-top:.375rem;font-size:1.75rem;font-weight:600;line-height:1.2;
font-variant-numeric:tabular-nums}
.cifra--destacada{border-top:3px solid var(--naranja)}
.tarjeta{border:1px solid var(--borde);border-radius:var(--r-g);background:var(--blanco)}
.tarjeta+.tarjeta{margin-top:1.5rem}
.tarjeta__cabeza{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:.75rem;
padding:1rem 1.25rem;border-bottom:1px solid var(--borde)}
.tarjeta__cuerpo{padding:1.25rem}
.tarjeta__pie{padding:.75rem 1.25rem;border-top:1px solid var(--borde);font-size:.8125rem;color:var(--suave)}
.tabla-envoltura{overflow-x:auto}
table{width:100%;border-collapse:collapse}
th{text-align:left;font-weight:500;font-size:.75rem;color:var(--suave);background:#f9fafb;
padding:.625rem 1.25rem;border-bottom:1px solid var(--borde);white-space:nowrap}
td{padding:.75rem 1.25rem;border-bottom:1px solid var(--borde);vertical-align:middle}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover td{background:#fcfcfd}
td.suave{color:var(--suave);white-space:nowrap}
td a{color:var(--texto);text-decoration:none}
td a:hover{color:var(--naranja-hover);text-decoration:underline}
.idioma{display:inline-block;min-width:2rem;padding:.0625rem .375rem;border:1px solid var(--borde);border-radius:4px;
font-size:.6875rem;font-weight:600;text-align:center;color:var(--suave);text-transform:uppercase}
.vacio{padding:2.5rem 1rem;text-align:center;color:var(--suave)}
.herramientas{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center}
input[type=text],input[type=search],input[type=password]{height:2.25rem;padding:0 .75rem;border:1px solid var(--borde-fuerte);
border-radius:var(--r);background:var(--blanco);font:inherit;color:inherit;min-width:0}
input:focus{outline:0;border-color:var(--naranja);box-shadow:0 0 0 3px rgb(255 130 53/.18)}
button:focus-visible,a:focus-visible{outline:2px solid var(--naranja);outline-offset:2px}
.boton{display:inline-flex;align-items:center;justify-content:center;gap:.375rem;height:2.25rem;padding:0 .875rem;
border:1px solid var(--naranja);border-radius:var(--r);background:var(--naranja);color:var(--texto);font:inherit;font-weight:500;
text-decoration:none;cursor:pointer;white-space:nowrap}
.boton:hover{background:var(--naranja-hover);border-color:var(--naranja-hover)}
.boton--claro{border-color:var(--borde-fuerte);background:var(--blanco);color:var(--texto)}
.boton--claro:hover{background:var(--fondo);border-color:var(--borde-fuerte)}
.boton--peligro{height:1.875rem;padding:0 .625rem;border-color:transparent;background:transparent;color:var(--rojo);font-size:.8125rem}
.boton--peligro:hover{background:var(--rojo-claro);border-color:transparent}
.boton--pequeno{height:1.875rem;font-size:.8125rem}
form.linea{display:inline}
.aviso{margin-bottom:1.25rem;padding:.625rem .875rem;border:1px solid #abefc6;border-radius:var(--r);
background:var(--verde-claro);color:var(--verde)}
.aviso--error{border-color:#fecdca;background:var(--rojo-claro);color:var(--rojo)}
.campos{display:grid;grid-template-columns:repeat(auto-fit,minmax(12rem,1fr));max-width:48rem;gap:.75rem;align-items:end}
.campos label{display:grid;gap:.375rem;font-size:.8125rem;font-weight:500}
.tu{margin-left:.375rem;font-size:.75rem;color:var(--suave)}
.en-fila{flex-wrap:nowrap}
.acceso{min-height:100vh;display:grid;place-items:center;padding:1.5rem}
.acceso .tarjeta{width:min(100%,22rem);padding:2rem}
.acceso .marca{height:auto;padding:0;border:0;margin-bottom:1.75rem}
.acceso .marca .logo{height:1.375rem}
.acceso h1{font-size:1.25rem;margin-bottom:.25rem}
.acceso .sub{margin:0 0 1.5rem}
.acceso form{display:grid;gap:1rem}
.acceso label{display:grid;gap:.375rem;font-size:.8125rem;font-weight:500}
.acceso .boton{margin-top:.25rem;width:100%}
@media (max-width:52rem){.marco{grid-template-columns:minmax(0,1fr)}
.lateral{position:sticky;top:0;z-index:5;height:auto;display:grid;grid-template-columns:1fr auto;border-right:0;
border-bottom:1px solid var(--borde)}
.marca{height:3.25rem;padding:0 1rem;border-bottom:0}
.lateral__pie{grid-row:1;grid-column:2;margin:0;padding:0 1rem;border-top:0;gap:.875rem}
.usuario span,.usuario{font-size:0}.usuario img{width:28px;height:28px}
.nav{grid-column:1/-1;grid-template-columns:repeat(3,1fr);grid-auto-flow:row;padding:0 .5rem;gap:0;
border-top:1px solid var(--borde)}
.nav a{justify-content:center;gap:.375rem;padding:.625rem .25rem;border-radius:0;border-bottom:2px solid transparent}
.nav a[aria-current=page]{background:none;border-bottom-color:var(--naranja)}
.principal{padding:1.25rem 1rem 2.5rem}
.cabeza{align-items:stretch;flex-direction:column;margin-bottom:1.25rem}
.cabeza .boton{width:100%}
.cifras{grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem}
.cifra{padding:.875rem 1rem}.cifra strong{font-size:1.5rem}
.tarjeta__cabeza,.tarjeta__cuerpo{padding:1rem}
.tarjeta__cabeza.herramientas input{max-width:none!important}
.campos{grid-template-columns:1fr}
/* Tablas como fichas: una por registro, con la etiqueta de cada dato */
.tabla-envoltura{overflow:visible}
table,tbody,tr,td{display:block}
thead{display:none}
tbody tr{padding:.875rem 1rem;border-bottom:1px solid var(--borde)}
tbody tr:last-child{border-bottom:0}
tbody tr:hover td{background:none}
td{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.1875rem 0;border:0;text-align:right}
td[data-etiqueta]::before{content:attr(data-etiqueta);flex:none;font-size:.75rem;color:var(--suave);text-align:left}
td.principal-celda{padding-bottom:.375rem;font-weight:600;text-align:left}
td.principal-celda::before{display:none}
td.acciones-celda{justify-content:flex-end;padding-top:.375rem}
td .en-fila{flex-wrap:wrap;justify-content:flex-end}
td .en-fila input{width:100%!important}
td a{overflow-wrap:anywhere}}
"""

ICONOS = {
    "resumen": '<path d="M3 13h6V3H3zM11 17h6V9h-6zM3 17h6v-2H3zM11 7h6V3h-6z"/>',
    "registros": '<path d="M4 3h12v14H4zM7 7h6M7 10h6M7 13h4"/>',
    "usuarios": '<circle cx="10" cy="7" r="3.25"/><path d="M3.5 17a6.5 6.5 0 0 1 13 0"/>',
}


def icono(nombre):
    return ('<svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
            'stroke-width="1.5" stroke-linejoin="round" aria-hidden="true">{}</svg>').format(ICONOS[nombre])


def documento(titulo, cuerpo):
    return """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>{} · Panel SUNNA</title>
<link rel="icon" href="{}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>{}</style></head><body>{}</body></html>""".format(e(titulo), FAVICON_URL, ESTILOS, cuerpo)


def marco(actual, admin, titulo, sub, contenido, acciones=""):
    enlaces = "".join(
        '<a href="{}"{}>{}{}</a>'.format(ruta, ' aria-current="page"' if clave == actual else "", icono(clave), texto)
        for clave, ruta, texto in (
            ("resumen", "/panel", "Resumen"),
            ("registros", "/panel/registros", "Registros"),
            ("usuarios", "/panel/usuarios", "Usuarios"),
        )
    )
    cuerpo = """<div class="marco"><aside class="lateral"><div class="marca">{}</div>
<nav class="nav" aria-label="Panel">{}</nav>
<div class="lateral__pie"><span class="usuario"><img src="{}" alt="" width="28" height="28">{}</span><a href="/panel/salir">Cerrar sesión</a></div></aside>
<main class="principal"><div class="cabeza"><div><h1>{}</h1>{}</div>{}</div>{}</main></div>""".format(
        LOGO, enlaces, FAVICON_URL, e(admin["usuario"]), e(titulo), '<p class="sub">{}</p>'.format(e(sub)) if sub else "", acciones, contenido
    )
    return documento(titulo, cuerpo)


def aviso(consulta):
    mensajes = {
        "creado": ("Administrador creado.", False),
        "password": ("Contraseña actualizada.", False),
        "borrado": ("Eliminado.", False),
        "existe": ("Ese nombre de usuario ya existe.", True),
        "usuario": ("El usuario debe tener entre 3 y 40 letras, números, puntos o guiones.", True),
        "corta": ("La contraseña debe tener al menos 10 caracteres.", True),
        "tu": ("No puedes eliminar tu propio usuario.", True),
    }
    clave = (consulta.get("ok") or consulta.get("error") or [""])[0]
    if clave not in mensajes:
        return ""
    texto, error = mensajes[clave]
    return '<p class="aviso{}" role="status">{}</p>'.format(" aviso--error" if error else "", e(texto))


def tabla_registros(filas, csrf=None):
    if not filas:
        return '<p class="vacio">Todavía no se ha registrado nadie.</p>'
    cabeza = "<th>Nombre</th><th>Email</th><th>Teléfono</th><th>Idioma</th><th>Fecha</th>" + ("<th></th>" if csrf else "")
    cuerpo = ""
    for r in filas:
        borrar = ""
        if csrf:
            borrar = ('<td class="acciones-celda"><form class="linea" method="post" action="/panel/registros/{}/borrar" '
                      'onsubmit="return confirm(\'¿Eliminar este registro?\')">'
                      '<input type="hidden" name="csrf" value="{}"><button class="boton boton--peligro">Eliminar</button>'
                      "</form></td>").format(r[0], e(csrf))
        cuerpo += ('<tr><td data-etiqueta="Nombre" class="principal-celda">{}</td>'
                   '<td data-etiqueta="Email"><a href="mailto:{}">{}</a></td>'
                   '<td data-etiqueta="Teléfono" class="suave">{}</td>'
                   '<td data-etiqueta="Idioma"><span class="idioma">{}</span></td>'
                   '<td data-etiqueta="Fecha" class="suave">{}</td>{}</tr>').format(
            e(r[1]), e(r[2]), e(r[2]), e(r[3] or "—"), e(r[4]), fecha(r[5]), borrar)
    return '<div class="tabla-envoltura"><table><thead><tr>{}</tr></thead><tbody>{}</tbody></table></div>'.format(cabeza, cuerpo)


def pagina_login(error="", siguiente="/panel"):
    mensaje = {
        "1": "Usuario o contraseña incorrectos.",
        "espera": "Demasiados intentos. Espera unos minutos.",
    }.get(error, "")
    cuerpo = """<main class="acceso"><div class="tarjeta"><div class="marca">{}</div>
<h1>Iniciar sesión</h1><p class="sub">Panel de administración</p>{}
<form method="post" action="/panel/entrar"><input type="hidden" name="next" value="{}">
<label>Usuario<input type="text" name="usuario" autocomplete="username" required autofocus></label>
<label>Contraseña<input type="password" name="password" autocomplete="current-password" required></label>
<button class="boton">Entrar</button></form></div></main>""".format(
        LOGO, '<p class="aviso aviso--error" role="alert">{}</p>'.format(e(mensaje)) if mensaje else "", e(siguiente)
    )
    return documento("Entrar", cuerpo)


# ─── Servidor ───────────────────────────────────────────────────

def ip_cliente(handler):
    reenviada = handler.headers.get("X-Forwarded-For", "")
    return reenviada.split(",")[0].strip() or handler.client_address[0]


class Panel(BaseHTTPRequestHandler):
    server_version = "sunna-panel"

    def setup(self):
        super().setup()
        self.bd = BD()

    def finish(self):
        try:
            super().finish()
        finally:
            self.bd.cerrar()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (ip_cliente(self), fmt % args))

    # Respuestas

    def responder(self, codigo, cuerpo, tipo="text/html; charset=utf-8", extra=None):
        datos = cuerpo.encode() if isinstance(cuerpo, str) else cuerpo
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        for clave, valor in (extra or {}).items():
            self.send_header(clave, valor)
        self.end_headers()
        self.wfile.write(datos)

    def redirigir(self, destino, cookie=None):
        self.send_response(303)
        self.send_header("Location", destino)
        self.send_header("Cache-Control", "no-store")
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def json(self, codigo, datos):
        self.responder(codigo, json.dumps(datos), "application/json; charset=utf-8")

    def cookie(self, valor, max_age):
        partes = ["{}={}".format(COOKIE, valor), "Path=/panel", "HttpOnly", "SameSite=Strict", "Max-Age={}".format(max_age)]
        if COOKIE_SEGURA:
            partes.append("Secure")
        return "; ".join(partes)

    def leer_cuerpo(self, maximo=8192):
        longitud = min(int(self.headers.get("Content-Length") or 0), maximo)
        return self.rfile.read(longitud).decode("utf-8", "replace")

    def campos(self):
        return {k: v[0] for k, v in parse_qs(self.leer_cuerpo()).items()}

    # Sesión

    def sesion(self):
        """(admin, token) si hay una sesión válida de un administrador que sigue existiendo."""
        token = leer_cookie(self.headers.get("Cookie"), COOKIE)
        admin_id = leer_token(token)
        if admin_id is None:
            return None, ""
        fila = self.bd.uno("SELECT id, usuario FROM administradores WHERE id = %s", (admin_id,))
        if not fila:
            return None, ""
        return {"id": fila[0], "usuario": fila[1]}, token

    # Rutas

    def do_GET(self):
        partes = urlsplit(self.path)
        ruta, consulta = partes.path.rstrip("/") or "/", parse_qs(partes.query)
        try:
            if ruta == "/panel/entrar":
                return self.responder(200, pagina_login((consulta.get("error") or [""])[0],
                                                        (consulta.get("next") or ["/panel"])[0]))
            if ruta == "/panel/salir":
                return self.redirigir("/panel/entrar", self.cookie("", 0))
            if not ruta.startswith("/panel"):
                return self.responder(404, "No encontrado", "text/plain; charset=utf-8")

            admin, token = self.sesion()
            if not admin:
                return self.redirigir("/panel/entrar?next=" + quote(ruta, safe="/"))
            csrf = token_csrf(token)

            if ruta == "/panel":
                return self.responder(200, self.vista_resumen(admin))
            if ruta == "/panel/registros":
                return self.responder(200, self.vista_registros(admin, consulta, csrf))
            if ruta == "/panel/registros.csv":
                return self.exportar_csv()
            if ruta == "/panel/usuarios":
                return self.responder(200, self.vista_usuarios(admin, consulta, csrf))
            return self.responder(404, "No encontrado", "text/plain; charset=utf-8")
        except Exception as error:
            self.log_message("error: %r", error)
            return self.responder(500, "Error del servidor", "text/plain; charset=utf-8")

    def do_POST(self):
        ruta = urlsplit(self.path).path.rstrip("/")
        try:
            if ruta == "/api/registro":
                return self.registrar()
            if ruta == "/panel/entrar":
                return self.entrar()

            admin, token = self.sesion()
            if not admin:
                return self.redirigir("/panel/entrar")
            campos = self.campos()
            if not hmac.compare_digest(campos.get("csrf", ""), token_csrf(token)):
                return self.responder(403, "Formulario caducado. Vuelve atrás y recarga la página.",
                                      "text/plain; charset=utf-8")

            m = re.fullmatch(r"/panel/registros/(\d+)/borrar", ruta)
            if m:
                self.bd.ejecutar("DELETE FROM registros WHERE id = %s", (int(m.group(1)),))
                return self.redirigir("/panel/registros?ok=borrado")
            if ruta == "/panel/usuarios":
                return self.crear_admin(campos)
            m = re.fullmatch(r"/panel/usuarios/(\d+)/(password|borrar)", ruta)
            if m:
                return self.cambiar_admin(admin, int(m.group(1)), m.group(2), campos)
            return self.responder(404, "No encontrado", "text/plain; charset=utf-8")
        except Exception as error:
            self.log_message("error: %r", error)
            if ruta == "/api/registro":
                return self.json(500, {"ok": False})
            return self.responder(500, "Error del servidor", "text/plain; charset=utf-8")

    # Acciones

    def entrar(self):
        ip = ip_cliente(self)
        campos = self.campos()
        siguiente = campos.get("next", "/panel")
        if not siguiente.startswith("/panel") or siguiente.startswith("/panel/entrar"):
            siguiente = "/panel"
        if limitar(fallos, ip, MAX_FALLOS):
            return self.redirigir("/panel/entrar?error=espera")
        fila = self.bd.uno("SELECT id, hash FROM administradores WHERE usuario = %s", (campos.get("usuario", "").strip(),))
        if comprobar_hash(campos.get("password", ""), fila[1] if fila else HASH_RELLENO) and fila:
            fallos.pop(ip, None)
            self.bd.ejecutar("UPDATE administradores SET ultimo_acceso = now() WHERE id = %s", (fila[0],))
            return self.redirigir(siguiente, self.cookie(crear_token(fila[0]), DURACION))
        anotar(fallos, ip)
        time.sleep(1)
        return self.redirigir("/panel/entrar?error=1&next=" + quote(siguiente, safe="/"))

    def registrar(self):
        """Formulario público de la web. Acepta JSON o formulario."""
        ip = ip_cliente(self)
        if limitar(envios, ip, MAX_REGISTROS):
            return self.json(429, {"ok": False, "error": "demasiados"})
        crudo = self.leer_cuerpo(4096)
        if "json" in (self.headers.get("Content-Type") or ""):
            try:
                datos = json.loads(crudo or "{}")
            except ValueError:
                return self.json(400, {"ok": False, "error": "formato"})
        else:
            datos = {k: v[0] for k, v in parse_qs(crudo).items()}
        nombre = str(datos.get("nombre", "")).strip()[:120]
        email = str(datos.get("email", "")).strip()[:200]
        telefono = str(datos.get("telefono", "")).strip()[:40]
        idioma = str(datos.get("idioma", "es"))
        acepta = datos.get("consentimiento") in (True, "true", "on", "1", 1)
        if str(datos.get("web", "")):  # campo trampa para bots: las personas lo dejan vacío
            return self.json(200, {"ok": True})
        if not nombre or not EMAIL.match(email) or not acepta:
            return self.json(400, {"ok": False, "error": "campos"})
        anotar(envios, ip)
        self.bd.ejecutar(
            "INSERT INTO registros (nombre, email, telefono, idioma, ip, consentimiento) "
            "VALUES (%s, %s, %s, %s, %s, now()) ON CONFLICT (lower(email)) DO NOTHING",
            (nombre, email, telefono, idioma if idioma in IDIOMAS else "es", ip),
        )
        return self.json(200, {"ok": True})

    def crear_admin(self, campos):
        usuario = campos.get("usuario", "").strip()
        password = campos.get("password", "")
        if not USUARIO.match(usuario):
            return self.redirigir("/panel/usuarios?error=usuario")
        if len(password) < 10:
            return self.redirigir("/panel/usuarios?error=corta")
        if self.bd.uno("SELECT 1 FROM administradores WHERE usuario = %s", (usuario,)):
            return self.redirigir("/panel/usuarios?error=existe")
        self.bd.ejecutar("INSERT INTO administradores (usuario, hash) VALUES (%s, %s)", (usuario, generar_hash(password)))
        return self.redirigir("/panel/usuarios?ok=creado")

    def cambiar_admin(self, admin, admin_id, accion, campos):
        if accion == "borrar":
            if admin_id == admin["id"]:
                return self.redirigir("/panel/usuarios?error=tu")
            self.bd.ejecutar("DELETE FROM administradores WHERE id = %s", (admin_id,))
            return self.redirigir("/panel/usuarios?ok=borrado")
        password = campos.get("password", "")
        if len(password) < 10:
            return self.redirigir("/panel/usuarios?error=corta")
        self.bd.ejecutar("UPDATE administradores SET hash = %s WHERE id = %s", (generar_hash(password), admin_id))
        return self.redirigir("/panel/usuarios?ok=password")

    def exportar_csv(self):
        filas = self.bd.todos("SELECT nombre, email, telefono, idioma, creado, consentimiento FROM registros ORDER BY creado DESC")
        salida = io.StringIO()
        escritor = csv.writer(salida, delimiter=";")
        escritor.writerow(["Nombre", "Email", "Teléfono", "Idioma", "Fecha de registro", "Consentimiento"])
        for f in filas:
            limpio = [texto_csv(c) for c in f[:4]]
            escritor.writerow(limpio + [fecha(f[4]), fecha(f[5])])
        nombre = "sunna-registros-{}.csv".format(datetime.now().strftime("%Y-%m-%d"))
        self.responder(200, "﻿" + salida.getvalue(), "text/csv; charset=utf-8",
                       {"Content-Disposition": 'attachment; filename="{}"'.format(nombre)})

    # Vistas

    def vista_resumen(self, admin):
        total, semana, hoy = self.bd.uno(
            "SELECT count(*), count(*) FILTER (WHERE creado > now() - interval '7 days'), "
            "count(*) FILTER (WHERE creado > date_trunc('day', now())) FROM registros"
        )
        admins = self.bd.uno("SELECT count(*) FROM administradores")[0]
        por_idioma = dict(self.bd.todos("SELECT idioma, count(*) FROM registros GROUP BY idioma"))
        ultimos = self.bd.todos(
            "SELECT id, nombre, email, telefono, idioma, creado FROM registros ORDER BY creado DESC LIMIT 6"
        )
        idiomas = " · ".join("{} {}".format(i.upper(), por_idioma.get(i, 0)) for i in IDIOMAS)
        cifras = """<div class="cifras">
<div class="cifra cifra--destacada"><p class="etiqueta">Registros totales</p><strong>{}</strong></div>
<div class="cifra"><p class="etiqueta">Últimos 7 días</p><strong>{}</strong></div>
<div class="cifra"><p class="etiqueta">Hoy</p><strong>{}</strong></div>
<div class="cifra"><p class="etiqueta">Administradores</p><strong>{}</strong></div></div>""".format(total, semana, hoy, admins)
        ultimos_html = """<section class="tarjeta"><div class="tarjeta__cabeza"><h2>Últimos registros</h2>
<a class="boton boton--claro boton--pequeno" href="/panel/registros">Ver todos</a></div>{}<div class="tarjeta__pie">Por idioma: {}</div></section>""".format(
            tabla_registros(ultimos), idiomas)
        return marco("resumen", admin, "Resumen", "Registros de la lista de espera y socios fundadores.", cifras + ultimos_html)

    def vista_registros(self, admin, consulta, csrf):
        q = (consulta.get("q") or [""])[0].strip()[:100]
        if q:
            patron = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            filas = self.bd.todos(
                "SELECT id, nombre, email, telefono, idioma, creado FROM registros "
                "WHERE nombre ILIKE %s OR email ILIKE %s OR telefono ILIKE %s ORDER BY creado DESC LIMIT 500",
                (patron, patron, patron),
            )
        else:
            filas = self.bd.todos(
                "SELECT id, nombre, email, telefono, idioma, creado FROM registros ORDER BY creado DESC LIMIT 500"
            )
        total = self.bd.uno("SELECT count(*) FROM registros")[0]
        buscador = """<form class="tarjeta__cabeza herramientas" method="get" action="/panel/registros" style="justify-content:flex-start">
<input type="search" name="q" value="{}" placeholder="Buscar por nombre, email o teléfono" aria-label="Buscar" style="flex:1;max-width:24rem;min-width:12rem">
<button class="boton boton--claro">Buscar</button>{}</form>""".format(
            e(q), '<a class="boton boton--claro" href="/panel/registros">Quitar filtro</a>' if q else "")
        contenido = aviso(consulta) + '<section class="tarjeta">{}{}</section>'.format(
            buscador, tabla_registros(filas, csrf) if filas or not q else '<p class="vacio">Sin resultados para «{}».</p>'.format(e(q)))
        acciones = '<a class="boton" href="/panel/registros.csv">Descargar CSV</a>' if total else ""
        sub = "{} {} en la lista de espera y socios fundadores.".format(total, "persona" if total == 1 else "personas")
        return marco("registros", admin, "Registros", sub, contenido, acciones)

    def vista_usuarios(self, admin, consulta, csrf):
        filas = self.bd.todos("SELECT id, usuario, creado, ultimo_acceso FROM administradores ORDER BY usuario")
        cuerpo = ""
        for f in filas:
            propio = f[0] == admin["id"]
            borrar = "" if propio else (
                '<form class="linea" method="post" action="/panel/usuarios/{}/borrar" '
                'onsubmit="return confirm(\'¿Eliminar a {}?\')"><input type="hidden" name="csrf" value="{}">'
                '<button class="boton boton--peligro">Eliminar</button></form>').format(f[0], e(f[1]), e(csrf))
            cambiar = ('<form class="herramientas en-fila" method="post" action="/panel/usuarios/{}/password">'
                       '<input type="hidden" name="csrf" value="{}">'
                       '<input type="password" name="password" placeholder="Nueva contraseña" autocomplete="new-password" '
                       'minlength="10" required aria-label="Nueva contraseña de {}" style="width:12rem;height:1.875rem">'
                       '<button class="boton boton--claro boton--pequeno">Cambiar</button></form>').format(
                f[0], e(csrf), e(f[1]))
            cuerpo += ('<tr><td data-etiqueta="Usuario" class="principal-celda">{}{}</td>'
                       '<td data-etiqueta="Creado" class="suave">{}</td><td data-etiqueta="Último acceso" class="suave">{}</td>'
                       '<td data-etiqueta="Contraseña">{}</td><td class="acciones-celda">{}</td></tr>').format(
                e(f[1]), '<span class="tu">(tú)</span>' if propio else "", fecha(f[2], False), fecha(f[3]), cambiar, borrar)
        lista = """<section class="tarjeta"><div class="tarjeta__cabeza"><h2>Administradores</h2></div><div class="tabla-envoltura"><table>
<thead><tr><th>Usuario</th><th>Creado</th><th>Último acceso</th><th>Contraseña</th><th></th></tr></thead>
<tbody>{}</tbody></table></div></section>""".format(cuerpo)
        nuevo = """<section class="tarjeta"><div class="tarjeta__cabeza"><h2>Nuevo administrador</h2></div>
<form method="post" action="/panel/usuarios" class="campos tarjeta__cuerpo"><input type="hidden" name="csrf" value="{}">
<label>Usuario<input type="text" name="usuario" required pattern="[a-zA-Z0-9._\\-]{{3,40}}" autocomplete="off"></label>
<label>Contraseña (mín. 10)<input type="password" name="password" required minlength="10" autocomplete="new-password"></label>
<button class="boton">Crear</button></form></section>""".format(e(csrf))
        contenido = aviso(consulta) + lista + nuevo
        return marco("usuarios", admin, "Usuarios", "Quién puede entrar en este panel.", contenido)


class Servidor(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


def comando_esquema():
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel.sql")
    bd = BD()
    with open(ruta, encoding="utf-8") as f:
        bd.ejecutar(f.read())
    bd.cerrar()
    print("Esquema aplicado.")


def comando_crear_admin(usuario):
    if not USUARIO.match(usuario):
        sys.exit("Usuario no válido: 3–40 letras, números, puntos o guiones.")
    password = sys.stdin.readline().rstrip("\n")
    if len(password) < 10:
        sys.exit("La contraseña debe tener al menos 10 caracteres.")
    bd = BD()
    bd.ejecutar(
        "INSERT INTO administradores (usuario, hash) VALUES (%s, %s) "
        "ON CONFLICT (usuario) DO UPDATE SET hash = EXCLUDED.hash",
        (usuario, generar_hash(password)),
    )
    bd.cerrar()
    print("Administrador «{}» listo.".format(usuario))


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else ""
    if orden in ("esquema", "crear-admin") and not DSN:
        sys.exit("Falta PANEL_DSN")
    if orden == "esquema":
        comando_esquema()
    elif orden == "crear-admin" and len(sys.argv) == 3:
        comando_crear_admin(sys.argv[2])
    elif orden:
        sys.exit(__doc__)
    else:
        if not (DSN and SECRETO):
            sys.exit("Falta configuración: PANEL_DSN y PANEL_SECRETO")
        Servidor(("127.0.0.1", PUERTO), Panel).serve_forever()
