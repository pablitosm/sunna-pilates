#!/usr/bin/env python3
"""
Acceso privado a la web de SUNNA (sin base de datos).

Caddy pregunta a este servicio en cada petición (forward_auth → /auth/check).
- Con una cookie de sesión válida responde 200 y Caddy sirve la página.
- Sin ella responde 302 hacia /login?next=<ruta>.
POST /auth/login comprueba usuario y contraseña y crea la sesión.
GET /auth/logout la borra.

La contraseña se guarda como hash PBKDF2-SHA256 y la sesión es un token firmado
con HMAC-SHA256 que caduca. Configuración en /etc/sunnapilates-acceso.env:
  ACCESO_USUARIO, ACCESO_HASH (pbkdf2$iteraciones$sal$hash), ACCESO_SECRETO,
  ACCESO_COOKIE_SEGURA (1 cuando la web va por HTTPS).
Solo biblioteca estándar (Python 3.6+).
"""
import base64
import hashlib
import hmac
import os
import secrets
import socketserver
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote, urlsplit

USUARIO = os.environ.get("ACCESO_USUARIO", "")
HASH = os.environ.get("ACCESO_HASH", "")
SECRETO = os.environ.get("ACCESO_SECRETO", "").encode()
COOKIE_SEGURA = os.environ.get("ACCESO_COOKIE_SEGURA", "0") == "1"
COOKIE = "sunna_sesion"
DURACION = 30 * 24 * 3600  # 30 días
PUERTO = int(os.environ.get("ACCESO_PUERTO", "8083"))

# Freno a la fuerza bruta: intentos fallidos por IP en la última ventana.
VENTANA = 15 * 60
MAX_FALLOS = 10
fallos = {}


def comprobar_password(password):
    try:
        _, iteraciones, sal, esperado = HASH.split("$")
        calculado = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), int(iteraciones))
        return hmac.compare_digest(calculado.hex(), esperado)
    except Exception:
        return False


def firmar(datos):
    firma = hmac.new(SECRETO, datos.encode(), hashlib.sha256).digest()
    return datos + "." + base64.urlsafe_b64encode(firma).decode().rstrip("=")


def crear_token():
    caduca = int(time.time()) + DURACION
    return firmar("{}:{}".format(USUARIO, caduca))


def token_valido(token):
    if not token or "." not in token:
        return False
    datos, _ = token.rsplit(".", 1)
    if not hmac.compare_digest(firmar(datos), token):
        return False
    try:
        usuario, caduca = datos.split(":")
        return usuario == USUARIO and int(caduca) > time.time()
    except ValueError:
        return False


def leer_cookie(cabecera, nombre):
    for trozo in (cabecera or "").split(";"):
        clave, _, valor = trozo.strip().partition("=")
        if clave == nombre:
            return valor
    return ""


def destino_seguro(ruta):
    # Solo rutas internas de la propia web (evita redirecciones abiertas).
    if not ruta or not ruta.startswith("/") or ruta.startswith("//") or ruta.startswith("/login"):
        return "/"
    return ruta


def ip_cliente(handler):
    reenviada = handler.headers.get("X-Forwarded-For", "")
    return reenviada.split(",")[0].strip() or handler.client_address[0]


class Acceso(BaseHTTPRequestHandler):
    server_version = "sunna-acceso"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (ip_cliente(self), fmt % args))

    def redirigir(self, destino, cookie=None):
        self.send_response(302)
        self.send_header("Location", destino)
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def cookie(self, valor, max_age):
        partes = ["{}={}".format(COOKIE, valor), "Path=/", "HttpOnly", "SameSite=Lax", "Max-Age={}".format(max_age)]
        if COOKIE_SEGURA:
            partes.append("Secure")
        return "; ".join(partes)

    def do_GET(self):
        ruta = urlsplit(self.path).path
        if ruta == "/auth/check":
            if token_valido(leer_cookie(self.headers.get("Cookie"), COOKIE)):
                self.send_response(200)
                self.end_headers()
                return
            original = self.headers.get("X-Forwarded-Uri", "/")
            self.redirigir("/login?next=" + quote(destino_seguro(original), safe="/"))
            return
        if ruta == "/auth/logout":
            self.redirigir("/login", self.cookie("", 0))
            return
        self.send_error(404)

    def do_POST(self):
        if urlsplit(self.path).path != "/auth/login":
            self.send_error(404)
            return
        ip = ip_cliente(self)
        ahora = time.time()
        recientes = [t for t in fallos.get(ip, []) if ahora - t < VENTANA]
        longitud = min(int(self.headers.get("Content-Length") or 0), 4096)
        campos = parse_qs(self.rfile.read(longitud).decode("utf-8", "replace"))
        usuario = (campos.get("usuario") or [""])[0].strip()
        password = (campos.get("password") or [""])[0]
        siguiente = destino_seguro((campos.get("next") or ["/"])[0])

        if len(recientes) >= MAX_FALLOS:
            self.redirigir("/login?error=espera")
            return
        if hmac.compare_digest(usuario, USUARIO) and comprobar_password(password):
            fallos.pop(ip, None)
            self.redirigir(siguiente, self.cookie(crear_token(), DURACION))
            return
        recientes.append(ahora)
        fallos[ip] = recientes
        time.sleep(1)
        self.redirigir("/login?error=1&next=" + quote(siguiente, safe="/"))


class Servidor(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


def generar_hash(password, iteraciones=310000):
    sal = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), sal, iteraciones)
    return "pbkdf2${}${}${}".format(iteraciones, sal.hex(), h.hex())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "hash":
        # Uso: python3 acceso.py hash  (lee la contraseña de la entrada estándar)
        print(generar_hash(sys.stdin.readline().rstrip("\n")))
        sys.exit(0)
    if not (USUARIO and HASH and SECRETO):
        sys.exit("Falta configuración: ACCESO_USUARIO, ACCESO_HASH y ACCESO_SECRETO")
    Servidor(("127.0.0.1", PUERTO), Acceso).serve_forever()
