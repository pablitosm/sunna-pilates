#!/usr/bin/env python3
"""
Panel de administración de SUNNA.

Sirve el panel en /panel (con su propio inicio de sesión de administrador),
recibe los registros del formulario de la web en POST /api/registro y los eventos
de la analítica propia (sin cookies) en POST /api/evento.
Los datos viven en PostgreSQL (esquema en panel.sql).

Apartados:
  /panel             Resumen: cómo va la web esta semana (cifras, visitas y botones).
  /panel/analitica   Analítica de la web: visitas, clics, apartados vistos, fuentes y embudo.
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
import ipaddress
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
MAX_EVENTOS = 600
fallos = {}
envios = {}
eventos = {}

# Analítica: tipos de evento que manda la web y navegadores que no son personas
TIPOS_EVENTO = ("vista", "clic", "seccion", "salida")
BOTS = re.compile(r"bot|crawl|spider|slurp|lighthouse|headless|preview|facebookexternalhit|whatsapp|curl|python|wget", re.I)
ID_VISTA = re.compile(r"^[a-z0-9]{6,24}$")
PAGINA = re.compile(r"^[a-z-]{0,30}$")
ZONA_HORARIA = "Atlantic/Canary"


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


def huella_hash(guardado):
    # Va dentro del token: al cambiar la contraseña caducan las sesiones abiertas con la anterior
    return hashlib.sha256(guardado.encode()).hexdigest()[:16]


def crear_token(admin_id, guardado):
    datos = "{}:{}:{}".format(admin_id, int(time.time()) + DURACION, huella_hash(guardado))
    return datos + "." + firma(datos)


def leer_token(token):
    """(id del administrador, huella de su contraseña) si el token es válido y no ha caducado."""
    if not token or "." not in token:
        return None
    datos, recibida = token.rsplit(".", 1)
    if not hmac.compare_digest(firma(datos), recibida):
        return None
    try:
        admin_id, caduca, huella = datos.split(":")
        return (int(admin_id), huella) if int(caduca) > time.time() else None
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
    if recientes:
        registro[clave] = recientes
    else:
        # Sin intentos recientes la entrada sobra: si no, queda una por cada IP para siempre
        registro.pop(clave, None)
    return len(recientes) >= maximo


def anotar(registro, clave):
    ahora = time.time()
    registro.setdefault(clave, []).append(ahora)
    # Las IP que no vuelven dejarían su entrada para siempre: de vez en cuando se barren
    if len(registro) > 2000:
        for vieja in [c for c, ts in registro.items() if ahora - ts[-1] >= VENTANA]:
            registro.pop(vieja, None)


# Destino tras entrar al panel: solo rutas del panel con caracteres de URL corrientes. Fuera
# quedan tabuladores y saltos de línea, que en la cabecera Location permitirían colar cabeceras.
RUTA_PANEL = re.compile(r"/panel[A-Za-z0-9/_.~%?=&#+:@!$'()*,;-]*")


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


# ─── Analítica ──────────────────────────────────────────────────

def dispositivo_de(agente):
    if re.search(r"iPad|Tablet|PlayBook|Silk", agente) or (re.search(r"Android", agente) and not re.search(r"Mobile", agente)):
        return "tableta"
    if re.search(r"Mobi|iPhone|iPod|Android", agente):
        return "movil"
    return "escritorio"


# De dónde llega la visita: el dominio de procedencia o el utm_source, con nombres conocidos
FUENTES = (
    (r"(^|\.)google\.", "Google"), (r"instagram", "Instagram"), (r"(^|\.)(facebook|fb)\.|^l\.facebook", "Facebook"),
    (r"(^|\.)(t\.co|twitter\.com|x\.com)$", "X"), (r"whatsapp|^wa\.me", "WhatsApp"), (r"tiktok", "TikTok"),
    (r"(^|\.)bing\.", "Bing"), (r"duckduckgo", "DuckDuckGo"), (r"(^|\.)yahoo\.", "Yahoo"),
    (r"maps\.app|google\.[a-z.]+/maps", "Google Maps"), (r"linkedin|lnkd", "LinkedIn"),
)


def fuente_de(texto):
    texto = (texto or "").strip().lower()[:120]
    if not texto:
        return "Directo"
    if texto.startswith("www."):
        texto = texto[4:]
    for patron, nombre in FUENTES:
        if re.search(patron, texto):
            return nombre
    return texto


def huella(ip, agente):
    """Visitante anónimo: cambia cada día y no permite recuperar la IP."""
    dia = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return firma("visitante:{}:{}:{}".format(dia, ip, agente))[:16]


def recortar(valor, largo):
    return re.sub(r"\s+", " ", str(valor or "")).strip()[:largo]


def entero(valor, minimo, maximo):
    try:
        return max(minimo, min(maximo, int(valor)))
    except (TypeError, ValueError):
        return None


def numero(n):
    return "{:,}".format(int(n or 0)).replace(",", ".")


def duracion(segundos):
    if not segundos:
        return "0 s"
    segundos = int(round(segundos))
    return "{}m {:02d}s".format(segundos // 60, segundos % 60) if segundos >= 60 else "{} s".format(segundos)


def escala(maximo):
    """Techo «redondo» para el eje del gráfico (1, 2, 5, 10, 20, 50…)."""
    maximo = max(int(maximo or 0), 4)
    paso = 1
    while True:
        for m in (1, 2, 5):
            if paso * m * 4 >= maximo:
                return paso * m * 4
        paso *= 10


def grafico_dias(serie):
    """Visitantes (área) y páginas vistas (línea) por día, en SVG sin librerías."""
    ancho, alto, izq, abajo, arriba, der = 760, 230, 40, 28, 14, 10
    plano_a, plano_h = ancho - izq - der, alto - arriba - abajo
    techo = escala(max([f[2] for f in serie] + [0]))
    n = len(serie)
    paso = plano_a / max(n - 1, 1)

    def x(i):
        return izq + i * paso

    def y(v):
        return arriba + plano_h - plano_h * v / techo

    rejilla = ""
    for k in range(5):
        valor = techo * k // 4
        rejilla += ('<line x1="{0}" x2="{1}" y1="{2:.1f}" y2="{2:.1f}" class="g-rejilla"/>'
                    '<text x="{3}" y="{4:.1f}" class="g-eje" text-anchor="end">{5}</text>').format(
            izq, ancho - der, y(valor), izq - 8, y(valor) + 4, numero(valor))
    puntos_vis = " ".join("{:.1f},{:.1f}".format(x(i), y(f[1])) for i, f in enumerate(serie))
    puntos_vistas = " ".join("{:.1f},{:.1f}".format(x(i), y(f[2])) for i, f in enumerate(serie))
    area = "M{:.1f},{:.1f} L{} L{:.1f},{:.1f} Z".format(x(0), y(0), puntos_vis, x(n - 1), y(0))
    cada = max(1, int(round(n / 7)))
    # La primera y la última fecha se alinean al borde para que no se corten
    etiquetas = "".join(
        '<text x="{:.1f}" y="{}" class="g-eje" text-anchor="{}">{}</text>'.format(
            x(i), alto - 8, "start" if i == 0 else "end" if i == n - 1 else "middle", f[0].strftime("%d/%m"))
        for i, f in enumerate(serie) if i % cada == 0 or i == n - 1 and n - 1 - (i // cada) * cada > cada // 2
    )
    puntos = "" if n > 31 else "".join(
        '<circle cx="{:.1f}" cy="{:.1f}" r="3" class="g-punto"/>'.format(x(i), y(f[1])) for i, f in enumerate(serie))
    # Datos del hover: por día, posición y cifras ya escritas (GRAFICO_JS pinta la guía y la tarjeta).
    # La serie siempre acaba hoy (hora de Canarias, ver serie_dias): el último día es «Hoy».
    datos = [{"x": round(x(i), 1), "yv": round(y(f[1]), 1), "yp": round(y(f[2]), 1),
              "fecha": "Hoy, " + fecha_larga(f[0]) if i == n - 1 else fecha_larga(f[0]),
              "v": numero(f[1]), "p": numero(f[2])}
             for i, f in enumerate(serie)]
    # Lectura accesible: el mismo dato en texto, por si no se puede usar el ratón
    resumen = "; ".join("{}: {} visitantes, {} páginas vistas".format(d["fecha"], d["v"], d["p"]) for d in datos)
    return ('<div class="grafico-caja" data-serie="{}" data-arriba="{}" data-abajo="{}" data-ancho="{}">'
            '<svg class="grafico" viewBox="0 0 {} {}" role="img" tabindex="0" aria-label="Visitantes y páginas vistas por día. {}">'
            '{}<path d="{}" class="g-area"/><polyline points="{}" class="g-linea"/>'
            '<polyline points="{}" class="g-linea g-linea--vistas"/>{}{}'
            '<g class="g-foco"><line class="g-guia" y1="{}" y2="{}"/><circle class="g-foco__vistas" r="4"/>'
            '<circle class="g-foco__vis" r="5"/></g></svg>'
            '<div class="g-tip" aria-hidden="true"><p class="g-tip__fecha"></p>'
            '<p class="g-tip__fila"><i></i>Visitantes<strong class="g-tip__v"></strong></p>'
            '<p class="g-tip__fila"><i class="vistas"></i>Páginas vistas<strong class="g-tip__p"></strong></p></div>'
            '</div>').format(
        e(json.dumps(datos)), arriba, arriba + plano_h, ancho, ancho, alto, e(resumen), rejilla, area, puntos_vis,
        puntos_vistas, puntos, etiquetas, arriba, arriba + plano_h) + GRAFICO_JS


DIAS_SEMANA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")


def fecha_larga(dia):
    """«jueves, 20 de noviembre»"""
    return "{}, {} de {}".format(DIAS_SEMANA[dia.weekday()], dia.day, MESES[dia.month - 1])


# Hover del gráfico: el día más cercano al puntero (ratón o dedo) o el elegido con las flechas.
# Mueve la guía y los dos puntos del día y coloca la tarjeta a su lado, sin salirse del gráfico.
GRAFICO_JS = """<script>
document.querySelectorAll('.grafico-caja').forEach(function (caja) {
  var datos = JSON.parse(caja.dataset.serie), svg = caja.querySelector('svg'), foco = caja.querySelector('.g-foco');
  var tip = caja.querySelector('.g-tip'), actual = -1, ancho = +caja.dataset.ancho;
  var guia = foco.querySelector('.g-guia'), pv = foco.querySelector('.g-foco__vis'), pp = foco.querySelector('.g-foco__vistas');
  function mostrar(i) {
    i = Math.max(0, Math.min(datos.length - 1, i));
    var d = datos[i];
    actual = i;
    guia.setAttribute('x1', d.x); guia.setAttribute('x2', d.x);
    pv.setAttribute('cx', d.x); pv.setAttribute('cy', d.yv);
    pp.setAttribute('cx', d.x); pp.setAttribute('cy', d.yp);
    tip.querySelector('.g-tip__fecha').textContent = d.fecha;
    tip.querySelector('.g-tip__v').textContent = d.v;
    tip.querySelector('.g-tip__p').textContent = d.p;
    caja.classList.add('activo');
    // Coordenadas de pantalla: la tarjeta va a la derecha del día y, si no cabe en la parte visible
    // (en móvil el gráfico es más ancho que la pantalla y se desplaza), a la izquierda
    var r = svg.getBoundingClientRect(), escala = r.width / ancho, punto = r.left + d.x * escala;
    var marco = (caja.closest('.grafico-envoltura') || caja).getBoundingClientRect();
    var minimo = Math.max(marco.left, 0) + 4, maximo = Math.min(marco.right, innerWidth) - tip.offsetWidth - 4;
    var izq = punto + 14;
    if (izq > maximo) izq = punto - 14 - tip.offsetWidth;
    izq = Math.max(minimo, izq);
    tip.style.transform = 'translate(' + Math.round(izq - caja.getBoundingClientRect().left) + 'px,' +
      Math.round(+caja.dataset.arriba * escala) + 'px)';
  }
  function ocultar() { caja.classList.remove('activo'); actual = -1; }
  function cercano(ev) {
    var r = svg.getBoundingClientRect(), xv = (ev.clientX - r.left) * ancho / r.width, mejor = 0;
    datos.forEach(function (d, i) { if (Math.abs(d.x - xv) < Math.abs(datos[mejor].x - xv)) mejor = i; });
    return mejor;
  }
  svg.addEventListener('pointermove', function (ev) { mostrar(cercano(ev)); });
  svg.addEventListener('pointerdown', function (ev) { mostrar(cercano(ev)); });
  svg.addEventListener('pointerleave', function (ev) { if (ev.pointerType === 'mouse') ocultar(); });
  svg.addEventListener('focus', function () { mostrar(actual < 0 ? datos.length - 1 : actual); });
  svg.addEventListener('blur', ocultar);
  svg.addEventListener('keydown', function (ev) {
    var paso = {ArrowLeft: -1, ArrowRight: 1}[ev.key];
    if (paso) { ev.preventDefault(); mostrar((actual < 0 ? datos.length - 1 : actual) + paso); }
    else if (ev.key === 'Home' || ev.key === 'End') { ev.preventDefault(); mostrar(ev.key === 'Home' ? 0 : datos.length - 1); }
    else if (ev.key === 'Escape') ocultar();
  });
});
</script>"""


def lista_barras(filas, vacio="Sin datos en este periodo."):
    """Filas (texto, detalle, valor, valor_mostrado, marca) como barras horizontales, al estilo de Vercel."""
    if not filas:
        return '<p class="vacio vacio--corto">{}</p>'.format(e(vacio))
    maximo = max(f[2] for f in filas) or 1
    items = ""
    for texto, detalle, valor, mostrado, marca in filas:
        items += ('<li class="barra"><span class="barra__relleno" style="width:{:.1f}%"></span>'
                  '<span class="barra__texto"><span class="barra__nombre">{}</span>{}{}</span>'
                  '<span class="barra__valor">{}</span></li>').format(
            100 * valor / maximo, e(texto), '<span class="marca-reserva">Reserva</span>' if marca else "",
            '<span class="barra__detalle">{}</span>'.format(e(detalle)) if detalle else "", e(mostrado))
    return '<ul class="barras" role="list">{}</ul>'.format(items)


def cifra_comparada(titulo, valor, anterior, mostrado, destacada=False, nota=""):
    cambio = ""
    if anterior:
        dif = (valor - anterior) * 100.0 / anterior
        if abs(dif) >= 0.5:
            cambio = '<span class="cambio cambio--{}">{}{:.0f}%</span>'.format("sube" if dif > 0 else "baja", "+" if dif > 0 else "", dif)
    elif valor:
        cambio = '<span class="cambio cambio--sube">nuevo</span>'
    return ('<div class="cifra{}"><p class="etiqueta">{}</p><strong>{}{}</strong>{}</div>').format(
        " cifra--destacada" if destacada else "", e(titulo), e(mostrado), cambio,
        '<p class="cifra__nota">{}</p>'.format(e(nota)) if nota else "")


def cifras_html(hoy, prev):
    """Las cuatro cifras de la analítica, comparadas con el periodo anterior. Todas cuentan personas
    (salvo el tiempo); los clics sueltos y el detalle de cada botón están más abajo."""
    nota_visitantes = "{} páginas vistas".format(numero(hoy["vistas"]))
    if hoy["visitantes"]:
        nota_visitantes += " · {:.1f} por visitante".format(hoy["vistas"] / hoy["visitantes"])
    nota_reservar = "{} en «Reservar en bsport»".format(numero(hoy["pase"]))
    if hoy["ven_primera"]:
        nota_reservar += " ({:.0f}% de quien ve la primera sesión)".format(100.0 * hoy["pase"] / hoy["ven_primera"])
    return '<div class="cifras">{}{}{}{}</div>'.format(
        cifra_comparada("Visitantes", hoy["visitantes"], prev["visitantes"], numero(hoy["visitantes"]), True,
                        nota=nota_visitantes),
        cifra_comparada("Pulsan para reservar", hoy["convertidos"], prev["convertidos"], numero(hoy["convertidos"]), True,
                        nota=nota_reservar),
        cifra_comparada("Conversión", hoy["conversion"], prev["conversion"], "{:.1f}%".format(hoy["conversion"]),
                        nota="Visitantes que van a bsport, WhatsApp o las apps"),
        cifra_comparada("Tiempo en una página", hoy["tiempo"], prev["tiempo"], duracion(hoy["tiempo"]),
                        nota="Lo habitual (mediana) · bajan hasta el {:.0f}%".format(hoy["profundidad"])
                        if hoy["profundidad"] else "Lo habitual (mediana)"),
    )


def tarjeta_grafico(serie, hay_datos, titulo="Visitas por día"):
    return ('<section class="tarjeta"><div class="tarjeta__cabeza"><h2>{}</h2>'
            '<div class="leyenda"><span><i></i>Visitantes</span><span><i class="vistas"></i>Páginas vistas</span></div></div>'
            '<div class="tarjeta__cuerpo grafico-envoltura">{}</div></section>').format(
        e(titulo), grafico_dias(serie) if hay_datos else
        '<p class="vacio">Aún no hay visitas en este periodo. La web empieza a medir en cuanto se publica con la analítica.</p>')


# Clics en «Reservar en bsport» de la primera sesión: los dos botones (data-evento) y, de antes de
# distinguirlos, los enlaces a bsport desde esa página
CLIC_PASE = "(nombre IN ('pase-gratis-arriba', 'pase-gratis-abajo') OR (nombre = 'bsport' AND pagina = 'primera-sesion'))"
# Clic para reservar: solo los que salen de la web hacia donde de verdad se reserva (bsport, WhatsApp,
# las apps y los dos botones del pase). Va por el destino y no por la columna «objetivo», que hasta
# noviembre de 2026 también marcaba enlaces internos como «Primera sesión gratis» de la cabecera:
# así los datos antiguos se cuentan con el mismo criterio.
NOMBRES_RESERVA = ("bsport", "whatsapp", "app-store", "google-play", "pase-gratis-arriba", "pase-gratis-abajo")
CLIC_RESERVA = "(tipo = 'clic' AND nombre IN ({}))".format(", ".join("'{}'".format(n) for n in NOMBRES_RESERVA))
CLICS = {"pase-gratis-arriba": "Pase gratis, botón de arriba", "pase-gratis-abajo": "Pase gratis, botón de abajo"}


def filas_clics(clics):
    filas = []
    for nombre, etiqueta, zona, n in clics:
        objetivo = nombre in NOMBRES_RESERVA
        nombre = CLICS.get(nombre, nombre)
        detalle = [x for x in (nombre if etiqueta and etiqueta != nombre else "", nombre_apartado(zona) if zona else "") if x]
        filas.append((etiqueta or nombre, " · ".join(detalle), n, numero(n), objetivo))
    return filas


# Nombres legibles de los apartados (id del <section> en la web)
APARTADOS = {
    "portada": "Portada", "por-que": "Por qué SUNNA", "como-funciona": "Cómo funciona", "explora": "Descubre SUNNA",
    "app": "La app", "estudio": "El estudio", "preguntas": "Preguntas frecuentes", "faq": "Preguntas frecuentes", "dudas": "¿Y si…?", "cierre": "Cierre",
    "precios": "Precios", "fundadores": "Socios fundadores", "incluye": "Qué hacemos en la primera sesión", "prueba": "Primera sesión",
    "clases": "Las clases", "recovery": "Reformer, sauna y luz roja",
    "arriba": "Primera sesión, arriba", "reservar": "Primera sesión, reservar",
}
PAGINAS = {
    "inicio": "Inicio", "precios": "Precios", "primera-sesion": "Primera sesión", "reformer": "Reformer",
    "sauna": "Sauna", "luz-roja": "Luz roja", "otra": "Otras (legales, 404)",
}


# Orden en que aparecen los apartados en cada página (src/components/PaginaInicio.astro y
# PaginaPrimeraSesion.astro): así se ve dónde deja de bajar la gente. Las páginas que no están aquí
# y los apartados nuevos van detrás, de más a menos vistos.
ORDEN_PAGINAS = ("inicio", "primera-sesion", "precios", "reformer", "sauna", "luz-roja", "otra")
ORDEN_APARTADOS = {
    "inicio": ("portada", "por-que", "como-funciona", "app", "estudio", "preguntas"),
    "primera-sesion": ("arriba", "incluye", "reservar"),
}


def nombre_apartado(clave):
    return APARTADOS.get(clave) or clave.replace("-", " ").capitalize()


NOTA_CUENTA = ('<p class="nota-privacidad">Cómo se cuenta: cada visitante es anónimo y cambia cada día, así que quien '
               'vuelve otro día cuenta otra vez. En 30 o 90 días, «Visitantes» suma personas de cada día, no personas '
               'distintas. No se cuentan los dispositivos con los que has entrado a este panel.</p>')

# El panel está en el mismo dominio que la web: al abrirlo, este dispositivo deja de contar en la
# analítica (Base.astro mira esta marca antes de enviar nada).
NO_CONTAR = "<script>try{localStorage.setItem('sunna-no-contar','1')}catch(e){}</script>"


def apartados_html(apartados, vistas_pagina):
    """Por página, cada apartado con el porcentaje de visitas a esa página que llegan a verlo."""
    paginas = {}
    for pg, nombre, n in apartados:
        alcance = min(100.0, 100.0 * n / (vistas_pagina.get(pg) or n))
        paginas.setdefault(pg, []).append((nombre, alcance))
    if not paginas:
        return '<p class="vacio vacio--corto">Aún no hay apartados vistos.</p>'

    def posicion(pg):
        return (ORDEN_PAGINAS.index(pg) if pg in ORDEN_PAGINAS else len(ORDEN_PAGINAS), pg)

    grupos = ""
    for pg in sorted(paginas, key=posicion):
        orden = ORDEN_APARTADOS.get(pg, ())
        filas = sorted(paginas[pg], key=lambda f: (orden.index(f[0]) if f[0] in orden else len(orden), -f[1]))
        grupos += '<div class="apartados__pagina"><h3>{}<span>{} visitas</span></h3>{}</div>'.format(
            e(PAGINAS.get(pg, pg or "Sin página")), numero(vistas_pagina.get(pg, 0)),
            lista_barras([(nombre_apartado(nombre), "", a, "{:.0f}%".format(a), False) for nombre, a in filas]))
    return '<div class="apartados">{}</div>'.format(grupos)


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
.periodo{display:inline-flex;padding:2px;border:1px solid var(--borde-fuerte);border-radius:var(--r);background:var(--blanco)}
.periodo a{padding:.3125rem .75rem;border-radius:4px;color:var(--suave);font-weight:500;text-decoration:none;white-space:nowrap}
.periodo a[aria-current=true]{background:var(--naranja-claro);color:var(--texto)}
.cifra strong{display:flex;align-items:baseline;gap:.5rem}
.cambio{font-size:.75rem;font-weight:600;padding:.0625rem .375rem;border-radius:4px}
.cambio--sube{background:var(--verde-claro);color:var(--verde)}
.cambio--baja{background:var(--rojo-claro);color:var(--rojo)}
.cifra__nota{margin-top:.25rem;font-size:.75rem;color:var(--suave)}
.rejilla{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.5rem;margin-top:1.5rem;align-items:start}
.rejilla--tres{grid-template-columns:repeat(3,minmax(0,1fr))}
.rejilla--una{grid-template-columns:minmax(0,1fr)}
.grafico-envoltura{overflow-x:auto}
.rejilla .tarjeta+.tarjeta{margin-top:0}
.leyenda{display:flex;gap:1rem;font-size:.8125rem;color:var(--suave)}
.leyenda span{display:inline-flex;align-items:center;gap:.375rem}
.leyenda i{display:inline-block;width:.75rem;height:.1875rem;border-radius:2px;background:var(--naranja)}
.leyenda i.vistas{background:none;border-top:2px dashed #98a2b3;height:0}
.grafico{display:block;width:100%;height:auto}
.g-rejilla{stroke:var(--borde);stroke-width:1}
.g-eje{font-size:11px;fill:var(--suave);font-variant-numeric:tabular-nums}
.g-area{fill:rgb(255 130 53/.14)}
.g-linea{fill:none;stroke:var(--naranja);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.g-linea--vistas{stroke:#98a2b3;stroke-width:1.5;stroke-dasharray:4 4}
.g-punto{fill:var(--blanco);stroke:var(--naranja);stroke-width:2}
.grafico-caja{position:relative}
.grafico-caja svg{cursor:crosshair;touch-action:pan-y;outline:0}
.grafico-caja svg:focus-visible{outline:2px solid var(--naranja);outline-offset:4px;border-radius:4px}
.g-foco{opacity:0;transition:opacity .15s;pointer-events:none}
.grafico-caja.activo .g-foco{opacity:1}
.g-guia{stroke:#98a2b3;stroke-width:1;stroke-dasharray:3 3}
.g-foco__vis{fill:var(--naranja);stroke:var(--blanco);stroke-width:2.5}
.g-foco__vistas{fill:#98a2b3;stroke:var(--blanco);stroke-width:2}
.g-tip{position:absolute;top:0;left:0;z-index:2;min-width:12.5rem;padding:.625rem .75rem;border-radius:var(--r-g);
background:var(--texto);color:#fff;box-shadow:0 12px 28px -6px rgb(16 24 40/.28),0 4px 8px -4px rgb(16 24 40/.16);
font-size:.8125rem;line-height:1.4;pointer-events:none;opacity:0;transition:opacity .15s,transform .12s ease-out}
.grafico-caja.activo .g-tip{opacity:1}
.g-tip__fecha{margin-bottom:.375rem;font-size:.75rem;color:#d0d5dd}
.g-tip__fecha::first-letter{text-transform:uppercase}
.g-tip__fila{display:flex;align-items:center;gap:.5rem}
.g-tip__fila+.g-tip__fila{margin-top:.125rem}
.g-tip__fila i{flex:none;width:.625rem;height:.625rem;border-radius:50%;background:var(--naranja)}
.g-tip__fila i.vistas{background:#98a2b3}
.g-tip__fila strong{margin-left:auto;padding-left:1rem;font-weight:600;font-variant-numeric:tabular-nums}
@media (prefers-reduced-motion:reduce){.g-tip,.g-foco{transition:none}}
.barras{list-style:none;padding:.5rem .75rem .75rem;display:grid;gap:2px}
.barra{position:relative;display:flex;align-items:center;justify-content:space-between;gap:1rem;min-height:2.25rem;
padding:.375rem .625rem;border-radius:var(--r);overflow:hidden}
.barra__relleno{position:absolute;inset:0 auto 0 0;background:var(--naranja-claro);border-radius:var(--r)}
.barra__texto,.barra__valor{position:relative}
.barra__texto{display:flex;flex-wrap:wrap;align-items:baseline;gap:.25rem .5rem;min-width:0}
.barra__nombre{overflow-wrap:anywhere}
.barra__detalle{font-size:.75rem;color:var(--suave)}
.barra__valor{font-weight:500;font-variant-numeric:tabular-nums;white-space:nowrap}
.marca-reserva{font-size:.6875rem;font-weight:600;padding:0 .375rem;border-radius:4px;background:var(--naranja);color:var(--texto)}
.vacio--corto{padding:1.5rem 1rem}
.embudo{display:grid;gap:1rem;padding:1.25rem}
.embudo__paso{display:grid;gap:.375rem}
.embudo__fila{display:flex;justify-content:space-between;gap:1rem;font-size:.8125rem}
.embudo__fila strong{font-variant-numeric:tabular-nums}
.embudo__pista{height:.625rem;border-radius:999px;background:var(--fondo);overflow:hidden}
.embudo__pista span{display:block;height:100%;border-radius:999px;background:var(--naranja)}
.embudo__fila span small{margin-left:.375rem;font-size:.75rem;color:var(--suave)}
.apartados{display:grid;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));gap:.5rem 1.5rem;padding:.5rem .5rem .25rem}
.apartados__pagina h3{display:flex;justify-content:space-between;gap:1rem;padding:.75rem .75rem 0;font-size:.8125rem;font-weight:600}
.apartados__pagina h3 span{font-weight:400;color:var(--suave)}
.hoy{display:flex;flex-wrap:wrap;gap:.25rem 1.25rem;margin-bottom:1rem;color:var(--suave)}
.hoy strong{color:var(--texto);font-variant-numeric:tabular-nums}
.nota-privacidad{margin-top:1.5rem;font-size:.75rem;color:var(--suave)}
.nota-privacidad+.nota-privacidad{margin-top:.375rem}
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
.rejilla,.rejilla--tres{grid-template-columns:minmax(0,1fr);gap:1rem;margin-top:1rem}
.grafico-caja{min-width:36rem}
.cabeza .periodo{width:100%}.periodo a{flex:1;text-align:center}
.nav{grid-template-columns:repeat(4,1fr)}
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
    "analitica": '<path d="M3 16.5h14M5.5 13.5V9.5M9 13.5V5M12.5 13.5v-3.5M16 13.5V7"/>',
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
            ("analitica", "/panel/analitica", "Analítica"),
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
    return documento(titulo, cuerpo + NO_CONTAR)


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
    """IP del visitante. Apache añade la suya a X-Forwarded-For y Caddy, que confía en Apache
    (servidor/ip-real.caddy), la conserva y añade la de Apache al final. Se recorre la cadena de
    derecha a izquierda saltando los equipos locales (Apache, Caddy): la primera IP pública es la
    del visitante. Lo que el visitante escriba a la izquierda no cuenta, así que no puede falsearla."""
    cadena = [s.strip() for s in handler.headers.get("X-Forwarded-For", "").split(",") if s.strip()]
    cadena.append(handler.client_address[0])
    for salto in reversed(cadena):
        try:
            ip = ipaddress.ip_address(salto)
        except ValueError:
            continue
        if not (ip.is_loopback or ip.is_private):
            return salto
    return handler.client_address[0]


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

    def sin_contenido(self):
        self.send_response(204)
        self.send_header("Cache-Control", "no-store")
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
        leido = leer_token(token)
        if leido is None:
            return None, ""
        admin_id, huella = leido
        fila = self.bd.uno("SELECT id, usuario, hash FROM administradores WHERE id = %s", (admin_id,))
        if not fila or not hmac.compare_digest(huella, huella_hash(fila[2])):
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
            if ruta == "/panel/analitica":
                return self.responder(200, self.vista_analitica(admin, consulta))
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
            if ruta == "/api/evento":
                return self.evento()
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
            if ruta == "/api/evento":
                return self.sin_contenido()
            return self.responder(500, "Error del servidor", "text/plain; charset=utf-8")

    # Acciones

    def entrar(self):
        ip = ip_cliente(self)
        campos = self.campos()
        siguiente = campos.get("next", "/panel")
        if not RUTA_PANEL.fullmatch(siguiente) or siguiente.startswith("/panel/entrar"):
            siguiente = "/panel"
        if limitar(fallos, ip, MAX_FALLOS):
            return self.redirigir("/panel/entrar?error=espera")
        fila = self.bd.uno("SELECT id, hash FROM administradores WHERE usuario = %s", (campos.get("usuario", "").strip(),))
        if comprobar_hash(campos.get("password", ""), fila[1] if fila else HASH_RELLENO) and fila:
            fallos.pop(ip, None)
            self.bd.ejecutar("UPDATE administradores SET ultimo_acceso = now() WHERE id = %s", (fila[0],))
            return self.redirigir(siguiente, self.cookie(crear_token(fila[0], fila[1]), DURACION))
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
        if not isinstance(datos, dict):
            return self.json(400, {"ok": False, "error": "formato"})
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

    def evento(self):
        """Analítica de la web (sin cookies). Siempre responde 204: la web no espera nada."""
        ip = ip_cliente(self)
        agente = self.headers.get("User-Agent") or ""
        if not agente or BOTS.search(agente) or limitar(eventos, ip, MAX_EVENTOS):
            return self.sin_contenido()
        try:
            datos = json.loads(self.leer_cuerpo(2048) or "{}")
        except ValueError:
            return self.sin_contenido()
        if not isinstance(datos, dict):
            return self.sin_contenido()
        tipo = datos.get("t")
        ruta = recortar(datos.get("ruta"), 200).split("?")[0].split("#")[0]
        vista = str(datos.get("v") or "")
        if tipo not in TIPOS_EVENTO or not ruta.startswith("/") or not ID_VISTA.match(vista):
            return self.sin_contenido()
        anotar(eventos, ip)
        if secrets.randbelow(500) == 0:
            self.bd.ejecutar("DELETE FROM eventos WHERE creado < now() - interval '13 months'")
        pagina = str(datos.get("pagina") or "")
        idioma = str(datos.get("idioma") or "es")
        self.bd.ejecutar(
            "INSERT INTO eventos (tipo, vista, visitante, ruta, pagina, idioma, dispositivo, fuente, nombre, etiqueta, "
            "zona, objetivo, segundos, profundidad) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                tipo, vista, huella(ip, agente), ruta,
                pagina if PAGINA.match(pagina) else "",
                idioma if idioma in IDIOMAS else "es",
                dispositivo_de(agente),
                # La fuente solo en la página de entrada; las de dentro de la web van vacías
                fuente_de(datos.get("fuente")) if tipo == "vista" and datos.get("interna") is not True else "",
                recortar(datos.get("nombre"), 120),
                recortar(datos.get("etiqueta"), 80),
                recortar(datos.get("zona"), 40),
                tipo == "clic" and datos.get("objetivo") is True,
                entero(datos.get("segundos"), 0, 7200) if tipo == "salida" else None,
                entero(datos.get("profundidad"), 0, 100) if tipo == "salida" else None,
            ),
        )
        return self.sin_contenido()

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

    # Consultas de la analítica

    def periodo(self, dias):
        """(desde, antes, ahora) en hora de Canarias: desde el principio del día de hace (dias - 1) días,
        y el inicio del periodo anterior de la misma duración, para comparar."""
        return self.bd.uno(
            "SELECT d, d - %s * interval '1 day', now() FROM (SELECT ((now() AT TIME ZONE %s)::date - %s)::timestamp "
            "AT TIME ZONE %s AS d) t", (dias, ZONA_HORARIA, dias - 1, ZONA_HORARIA))

    def cifras(self, inicio, fin):
        v = self.bd.uno(
            "SELECT count(DISTINCT visitante) FILTER (WHERE tipo = 'vista'), count(*) FILTER (WHERE tipo = 'vista'), "
            "count(DISTINCT visitante) FILTER (WHERE " + CLIC_RESERVA + "), "
            "count(DISTINCT visitante) FILTER (WHERE tipo = 'clic' AND " + CLIC_PASE + "), "
            "count(DISTINCT visitante) FILTER (WHERE tipo = 'vista' AND pagina = 'primera-sesion') "
            "FROM eventos WHERE creado >= %s AND creado < %s", (inicio, fin))
        # Mediana y no media: una pestaña olvidada abierta una hora no debe mover la cifra
        t = self.bd.uno(
            "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY s), percentile_cont(0.5) WITHIN GROUP (ORDER BY p) "
            "FROM (SELECT max(segundos) s, max(profundidad) p FROM eventos "
            "WHERE tipo = 'salida' AND creado >= %s AND creado < %s GROUP BY vista) x", (inicio, fin))
        return {"visitantes": v[0], "vistas": v[1], "convertidos": v[2], "pase": v[3], "ven_primera": v[4],
                "conversion": 100.0 * v[2] / v[0] if v[0] else 0,
                "tiempo": float(t[0] or 0), "profundidad": float(t[1] or 0)}

    def embudo(self, inicio, fin):
        """Embudo encadenado por visitante: cada paso solo cuenta a quien también dio el anterior.
        Devuelve los cuatro pasos y cuántos pulsan para reservar sin pasar por el paso 2."""
        return self.bd.uno(
            "SELECT count(*), count(*) FILTER (WHERE interes), count(*) FILTER (WHERE interes AND reserva), "
            "count(*) FILTER (WHERE interes AND reserva AND pase), count(*) FILTER (WHERE reserva AND NOT interes) "
            "FROM (SELECT visitante, "
            "bool_or(tipo = 'vista' AND pagina IN ('precios', 'primera-sesion')) interes, "
            "bool_or(" + CLIC_RESERVA + ") reserva, bool_or(tipo = 'clic' AND " + CLIC_PASE + ") pase "
            "FROM eventos WHERE creado >= %s AND creado < %s GROUP BY visitante "
            "HAVING bool_or(tipo = 'vista')) x", (inicio, fin))

    def cifras_periodo(self, dias):
        """Cifras del periodo actual y del anterior, y su comienzo."""
        desde, antes, ahora = self.periodo(dias)
        return self.cifras(desde, ahora + timedelta(seconds=1)), self.cifras(antes, desde), desde

    def serie_dias(self, dias, desde):
        return self.bd.todos(
            "SELECT d::date, coalesce(v.visitantes, 0), coalesce(v.vistas, 0) "
            "FROM generate_series(((now() AT TIME ZONE %s)::date - %s)::timestamp, (now() AT TIME ZONE %s)::date::timestamp, "
            "interval '1 day') d LEFT JOIN (SELECT (creado AT TIME ZONE %s)::date dia, count(DISTINCT visitante) visitantes, "
            "count(*) vistas FROM eventos WHERE tipo = 'vista' AND creado >= %s GROUP BY 1) v ON v.dia = d::date ORDER BY 1",
            (ZONA_HORARIA, dias - 1, ZONA_HORARIA, ZONA_HORARIA, desde))

    def top_clics(self, desde, limite):
        return self.bd.todos(
            "SELECT nombre, mode() WITHIN GROUP (ORDER BY etiqueta), mode() WITHIN GROUP (ORDER BY zona), "
            "count(*) FROM eventos "
            "WHERE tipo = 'clic' AND creado >= %s GROUP BY nombre ORDER BY 4 DESC LIMIT %s", (desde, limite))

    # Vistas

    def vista_resumen(self, admin):
        hoy, prev, desde = self.cifras_periodo(7)
        d = self.cifras(self.periodo(1)[0], datetime.now(timezone.utc) + timedelta(seconds=1))
        linea_hoy = ('<p class="hoy"><span>Hoy:</span><span><strong>{}</strong> visitantes</span>'
                     '<span><strong>{}</strong> pulsan para reservar</span><span><strong>{}</strong> páginas vistas</span></p>').format(
            numero(d["visitantes"]), numero(d["convertidos"]), numero(d["vistas"]))
        botones = ('<section class="tarjeta"><div class="tarjeta__cabeza"><h2>Botones más pulsados</h2>'
                   '<a class="boton boton--claro boton--pequeno" href="/panel/analitica?dias=7">Ver analítica</a></div>'
                   '{}</section>').format(
            lista_barras(filas_clics(self.top_clics(desde, 5)), "Aún no se ha pulsado ningún botón esta semana."))
        contenido = (linea_hoy + cifras_html(hoy, prev)
                     + tarjeta_grafico(self.serie_dias(7, desde), hoy["vistas"], "Visitas esta semana")
                     + botones + NOTA_CUENTA)
        acciones = '<a class="boton" href="/panel/analitica">Analítica completa</a>'
        return marco("resumen", admin, "Resumen", "Cómo va la web estos 7 días, comparado con los 7 anteriores.",
                     contenido, acciones)

    def vista_analitica(self, admin, consulta):
        dias = (consulta.get("dias") or ["30"])[0]
        dias = int(dias) if dias in ("7", "30", "90") else 30
        hoy, prev, desde = self.cifras_periodo(dias)

        cifras = cifras_html(hoy, prev)
        grafico = tarjeta_grafico(self.serie_dias(dias, desde), hoy["vistas"])

        def tarjeta(titulo, cuerpo, pie=""):
            return '<section class="tarjeta"><div class="tarjeta__cabeza"><h2>{}</h2></div>{}{}</section>'.format(
                e(titulo), cuerpo, '<div class="tarjeta__pie">{}</div>'.format(e(pie)) if pie else "")

        paginas = self.bd.todos(
            "SELECT ruta, max(pagina), count(DISTINCT visitante), count(*) FROM eventos "
            "WHERE tipo = 'vista' AND creado >= %s GROUP BY ruta ORDER BY 3 DESC, 4 DESC LIMIT 10", (desde,))
        paginas_html = lista_barras([
            (r, PAGINAS.get(pg, ""), vis, "{} · {} vistas".format(numero(vis), numero(vistas)), False)
            for r, pg, vis, vistas in paginas], "Aún no hay páginas vistas.")

        clics_html = lista_barras(filas_clics(self.top_clics(desde, 12)), "Aún no se ha pulsado ningún botón.")

        vistas_pagina = dict(self.bd.todos(
            "SELECT pagina, count(DISTINCT vista) FROM eventos WHERE tipo = 'vista' AND creado >= %s GROUP BY 1", (desde,)))
        apartados = self.bd.todos(
            "SELECT pagina, nombre, count(DISTINCT vista) FROM eventos WHERE tipo = 'seccion' AND creado >= %s "
            "GROUP BY 1, 2", (desde,))

        def reparto(columna, nombres=None, filtro=""):
            filas = self.bd.todos(
                "SELECT {0}, count(DISTINCT visitante) FROM eventos WHERE tipo = 'vista' AND creado >= %s {1} "
                "GROUP BY 1 ORDER BY 2 DESC LIMIT 8".format(columna, filtro), (desde,))
            total = sum(f[1] for f in filas) or 1
            return lista_barras([
                ((nombres or {}).get(k, k) or "—", "", n, "{} · {:.0f}%".format(numero(n), 100.0 * n / total), False)
                for k, n in filas])

        fuentes_html = reparto("fuente", filtro="AND fuente <> ''")
        dispositivos_html = reparto("dispositivo", {"movil": "Móvil", "tableta": "Tableta", "escritorio": "Ordenador"})
        idiomas_html = reparto("idioma", {"es": "Castellano", "en": "English", "de": "Deutsch", "fr": "Français"})

        total, interes, reserva, pase, directos = self.embudo(desde, datetime.now(timezone.utc) + timedelta(seconds=1))
        pasos = (("Visitan la web", total), ("Ven precios o la primera sesión", interes),
                 ("Y pulsan para reservar", reserva), ("Y pulsan «Reservar en bsport»", pase))
        base = total or 1
        filas_embudo = ""
        anterior = None
        for t, n in pasos:
            del_anterior = " <small>{:.0f}% del paso anterior</small>".format(100.0 * n / anterior) if anterior else ""
            filas_embudo += ('<div class="embudo__paso"><div class="embudo__fila"><span>{}{}</span>'
                             '<strong>{} · {:.0f}%</strong></div>'
                             '<div class="embudo__pista"><span style="width:{:.1f}%"></span></div></div>').format(
                e(t), del_anterior, numero(n), 100.0 * n / base, 100.0 * n / base)
            anterior = n
        embudo = '<div class="embudo">{}</div>'.format(filas_embudo)
        pie_embudo = "Cada paso cuenta solo a quien dio el anterior."
        if directos:
            pie_embudo += " Además, {} {} para reservar sin ver precios ni la primera sesión.".format(
                numero(directos), "pulsa" if directos == 1 else "pulsan")

        periodo = '<nav class="periodo" aria-label="Periodo">{}</nav>'.format("".join(
            '<a href="/panel/analitica?dias={0}"{1}>{0} días</a>'.format(d, ' aria-current="true"' if d == dias else "")
            for d in (7, 30, 90)))
        contenido = (
            cifras + grafico
            + '<div class="rejilla">{}{}</div>'.format(
                tarjeta("Embudo de reserva", embudo, pie_embudo),
                tarjeta("Botones y enlaces más pulsados", clics_html, "Clics en el periodo"))
            + '<div class="rejilla rejilla--una">{}</div>'.format(
                tarjeta("Hasta dónde bajan", apartados_html(apartados, vistas_pagina),
                        "Porcentaje de visitas a cada página que llegan a ver el apartado, en el orden de la página"))
            + '<div class="rejilla rejilla--tres">{}{}{}</div>'.format(
                tarjeta("Páginas más vistas", paginas_html, "Visitantes · páginas vistas"),
                tarjeta("De dónde llegan", fuentes_html, "Solo la página por la que entran"),
                tarjeta("Dispositivos e idiomas", dispositivos_html + idiomas_html))
            + NOTA_CUENTA
            + '<p class="nota-privacidad">Analítica propia y sin cookies: no se guarda la IP y cada visitante es anónimo '
              'y cambia cada día. No cuenta a quien pide no ser seguido (Do Not Track / GPC).</p>')
        sub = "Últimos {} días, comparado con los {} anteriores.".format(dias, dias)
        return marco("analitica", admin, "Analítica", sub, contenido, periodo)

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
