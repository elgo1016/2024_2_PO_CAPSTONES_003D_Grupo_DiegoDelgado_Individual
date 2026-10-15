"""Demostración local de 3Dedos. Python 3.10+, sin dependencias externas."""
from __future__ import annotations

import argparse
import base64
import binascii
import struct
import zlib
import os
import smtplib
import ssl
from email.message import EmailMessage
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
import webbrowser
from datetime import datetime, timezone, date
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Timer, Lock
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / 'datos' / '3dedos.sqlite3'
SESSION_SECONDS = 8 * 60 * 60
MAIL_LOCK = Lock()
MAIL_PENDING = set()


class AppError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def connect():
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000).hex()
    return f'260000${salt}${digest}'


def check_password(password, encoded):
    rounds, salt, expected = encoded.split('$')
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(rounds)).hex()
    return hmac.compare_digest(expected, digest)


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def text_field(data, key, label, maximum=160, optional=False):
    value = data.get(key, '')
    if not isinstance(value, str):
        raise AppError(f'{label}: ingresa un texto válido.')
    value = value.strip()
    if (not optional and not value) or len(value) > maximum:
        raise AppError(f'{label}: campo obligatorio de hasta {maximum} caracteres.' if not optional else f'{label}: máximo {maximum} caracteres.')
    return value


def integer(data, key, label, minimum=1, maximum=100000000):
    value = data.get(key)
    if type(value) is not int or not minimum <= value <= maximum:
        raise AppError(f'{label}: ingresa un número entero entre {minimum} y {maximum}.')
    return value


def credentials(data):
    email = text_field(data, 'email', 'Correo', 254).lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise AppError('Ingresa un correo electrónico válido.')
    password = data.get('password', '')
    if not isinstance(password, str) or not 10 <= len(password) <= 128:
        raise AppError('La contraseña debe tener entre 10 y 128 caracteres.')
    return email, password


def instagram_link(data):
    link = text_field(data, 'enlace', 'Enlace de Instagram', 500)
    parsed = urlsplit(link)
    host = parsed.hostname or ''
    if parsed.scheme != 'https' or not (host == 'instagram.com' or host.endswith('.instagram.com')):
        raise AppError('Ingresa un enlace válido de Instagram que comience con https://.')
    if not re.fullmatch(r'/(?:p|reel|tv)/[A-Za-z0-9_-]+/?', parsed.path):
        raise AppError('El enlace debe ser de una publicación, reel o video de Instagram.')
    return link


def initialize():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = connect()
    try:
        db.execute('PRAGMA journal_mode = WAL')
        db.executescript((BASE / 'schema.sql').read_text(encoding='utf-8'))
        with db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM negocios LIMIT 1').fetchone():
                return
            db.execute('INSERT INTO negocios VALUES (1, ?, ?)', ('3Dedos', 'Impresión 3D & Merchandising Geek'))
            db.executemany('INSERT INTO sagas VALUES (?, ?, ?)', [
                (1, 'zelda', 'The Legend of Zelda'), (2, 'pokemon', 'Pokémon'),
                (3, 'souls', 'Dark Souls / Elden Ring'), (4, 'donkey-kong', 'Donkey Kong'), (5, 'gta', 'GTA')])
            db.executemany('INSERT INTO productos VALUES (?, 1, ?, ?, ?, 20, 1)', [
                (1, 1, '5 Cuadros Saga completa The legend of zelda', 90990),
                (2, 2, 'Cuadro pequeño Pokemon rubi', 6000),
                (3, 4, 'PAck 3 cuadritos donkey kong country', 15000),
                (4, 5, 'Grande Tengo Elpico', 22000),
                (5, 2, 'Figura Gengar Articulado', 16990),
                (6, 3, 'Réplica Hoguera Rest Area', 12990)])
            db.executemany('INSERT INTO eventos VALUES (?, 1, ?, ?, ?, ?, 1)', [
                (1, 'Rush-Con', '2026-10-15', 'Espacio Vicente Valdes, Santiago', 'Stand #42 - Venta al detalle y mayoristas.'),
                (2, 'Expogame', '2026-11-02', 'Estacion Mapocho', 'Sector expositores.'),
                (3, 'Mega Feria Friki', '2026-11-14', 'Parque Cerrillos', 'Stock exclusivo para navidad.')])
            for i, label in enumerate('ABC', 1):
                uid = db.execute('INSERT INTO usuarios(email, password_hash, rol) VALUES (?, ?, ?)',
                                 (f'cliente-{label.lower()}@example.com', hash_password(secrets.token_urlsafe(32)), 'cliente')).lastrowid
                cid = db.execute('INSERT INTO clientes(usuario_id, nombre, saga_id) VALUES (?, ?, ?)',
                                 (uid, f'Cliente de prueba {label}', i)).lastrowid
                pid = db.execute('INSERT INTO pedidos(cliente_id, fecha, estado, referencia_demo, clave_solicitud, huella_solicitud) VALUES (?, ?, ?, ?, ?, ?)',
                                 (cid, now(), 'pendiente_pago', label, f'semilla-{label}', hashlib.sha256(json.dumps([[i, 1]]).encode()).hexdigest())).lastrowid
                price = db.execute('SELECT precio FROM productos WHERE id=?', (i,)).fetchone()['precio']
                db.execute('INSERT INTO detalle_pedido VALUES (?, ?, 1, ?)', (pid, i, price))
                db.execute('UPDATE productos SET stock=stock-1 WHERE id=?', (i,))
    finally:
        db.close()


def product_image(value):
    if value == '':
        return None
    if not isinstance(value, str) or not value.startswith('data:image/png;base64,') or len(value) > 2800000:
        raise AppError('La imagen no es válida o es demasiado grande.')
    try:
        raw = base64.b64decode(value.split(',', 1)[1], validate=True)
        if len(raw) > 2*1024*1024 or raw[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError()
        pos, chunks, compressed, header = 8, [], bytearray(), None
        while pos < len(raw):
            size = struct.unpack('>I', raw[pos:pos+4])[0]
            kind = raw[pos+4:pos+8]
            end = pos+8+size
            payload = raw[pos+8:end]
            crc = struct.unpack('>I', raw[end:end+4])[0]
            if zlib.crc32(kind+payload) & 0xffffffff != crc:
                raise ValueError()
            if header is None:
                if kind != b'IHDR' or size != 13:
                    raise ValueError()
                width,height,depth,color,comp,filt,interlace = struct.unpack('>IIBBBBB', payload)
                if not (1 <= width <= 1600 and 1 <= height <= 1600) or depth != 8 or color not in (2,6) or (comp,filt,interlace) != (0,0,0):
                    raise ValueError()
                header = (width,height,3 if color == 2 else 4)
            elif kind == b'IHDR':
                raise ValueError()
            if kind == b'IDAT':
                compressed.extend(payload)
            elif kind == b'IEND':
                if size or end+4 != len(raw):
                    raise ValueError()
            elif kind != b'IHDR' and kind[:1].isupper() and kind != b'PLTE':
                raise ValueError()
            if kind in (b'IHDR', b'IDAT', b'IEND'):
                chunks.append(raw[pos:end+4])
            pos = end+4
        if not header or kind != b'IEND':
            raise ValueError()
        width,height,channels = header
        stride = width*channels+1
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(bytes(compressed), stride*height+1)
        if len(pixels) != stride*height or not decoder.eof or decoder.unused_data or any(pixels[i]>4 for i in range(0,len(pixels),stride)):
            raise ValueError()
        return raw[:8]+b''.join(chunks)
    except (ValueError, struct.error, binascii.Error, zlib.error, IndexError):
        raise AppError('No se pudo validar la imagen. Selecciona un archivo JPG, PNG o WebP válido.') from None


def with_image(db, product):
    result = dict(product)
    image = db.execute('SELECT version FROM imagenes_producto WHERE producto_id=?', (result['id'],)).fetchone()
    result['imagen'] = f"/imagenes/productos/{result['id']}?v={image['version']}" if image else ''
    return result


def coupon_for(db, code, email, client_id):
    if code != 'ELGO20':
        raise AppError('El código de descuento no es válido.')
    row = db.execute('SELECT * FROM boletin WHERE email=?', (email,)).fetchone()
    if not row or row['vence'] <= int(time.time()) or row['pedido_id'] is not None:
        raise AppError('El cupón no es válido, venció o ya fue utilizado.')
    if db.execute("SELECT id FROM pedidos WHERE cliente_id=? AND estado!='cancelado' LIMIT 1", (client_id,)).fetchone():
        raise AppError('El descuento es válido solo para tu primera compra.')
    return row


def smtp_error(exc):
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return AppError('Gmail rechazó las credenciales. Revisa el correo y genera una contraseña de aplicación de Google; no uses la contraseña habitual.', 503)
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return AppError('El servidor de correo rechazó la dirección destinataria. Revisa el correo ingresado.', 503)
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return AppError('El servidor rechazó el remitente. Usa el mismo Gmail con el que iniciaste sesión.', 503)
    if isinstance(exc, smtplib.SMTPResponseException):
        return AppError(f'El servidor de correo rechazó el envío (código {exc.smtp_code}). Revisa los límites o restricciones de la cuenta.', 503)
    if isinstance(exc, ssl.SSLError):
        return AppError('No se pudo verificar la conexión segura con Gmail. Revisa la fecha del equipo y los certificados.', 503)
    if isinstance(exc, (OSError, smtplib.SMTPServerDisconnected)):
        return AppError('No se pudo completar la conexión con Gmail. Revisa internet y el acceso al puerto 587; vuelve a intentar.', 503)
    return AppError('No se pudo completar el envío. Revisa la configuración SMTP e intenta nuevamente.', 503)


def smtp_connection():
    host = os.environ.get('SMTP_HOST')
    if not host or not os.environ.get('SMTP_FROM'):
        raise AppError('Este servidor no tiene correo configurado. Detén la tienda y ábrela con INICIAR_CON_GMAIL.bat.', 503)
    smtp = None
    try:
        smtp = smtplib.SMTP(host, int(os.environ.get('SMTP_PORT', '587')), timeout=15)
        smtp.starttls(context=ssl.create_default_context())
        if os.environ.get('SMTP_USER'):
            smtp.login(os.environ['SMTP_USER'], os.environ.get('SMTP_PASSWORD', ''))
        return smtp
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        if smtp:
            smtp.close()
        raise smtp_error(exc) from None


def send_coupon(email, code):
    message = EmailMessage()
    message['Subject'] = 'Tu 20% de bienvenida a 3Dedos'
    message['From'] = os.environ.get('SMTP_FROM', '')
    message['To'] = email
    message.set_content("¡Felicidades!\n\nMuchas gracias por suscribirte a nuestro boletín para recibir actualizaciones de nuevos productos.\n\nAquí tienes tu código: ELGO20\n\nÚsalo en el carrito para obtener un 20% de descuento.\n")
    smtp = smtp_connection()
    try:
        rejected = smtp.send_message(message)
        if rejected:
            raise smtplib.SMTPRecipientsRefused(rejected)
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        raise smtp_error(exc) from None
    finally:
        # Cerrar sin QUIT evita informar un fallo después de que Gmail aceptó el correo.
        smtp.close()


class Handler(BaseHTTPRequestHandler):
    server_version = '3DedosLocal/1.0'

    def log_message(self, format, *args):
        # No registrar formularios, contraseñas ni cookies.
        pass

    def reply(self, status, value, cookie=None):
        body = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        if self.headers.get_content_type() != 'application/json' or self.headers.get('X-3Dedos-Request') != '1':
            raise AppError('Formato de solicitud no permitido.', 415)
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise AppError('Solicitud inválida.')
        image_request = bool(re.fullmatch(r'/api/admin/productos(?:/\d+)?', urlsplit(self.path).path))
        if image_request:
            check_db = connect()
            try:
                self.require(check_db, 'admin')
            finally:
                check_db.close()
        if size <= 0:
            raise AppError('No se recibieron datos. Vuelve a seleccionar la imagen y guarda el producto.', 400)
        if size > (2900000 if image_request else 65536):
            raise AppError('La imagen enviada supera el límite optimizado de 2 MB. Recarga administración con Ctrl+F5 y vuelve a seleccionarla.' if image_request else 'El formulario supera el tamaño permitido.', 413)
        try:
            data = json.loads(self.rfile.read(size))
        except (ValueError, UnicodeError):
            raise AppError('Los datos enviados no son válidos.')
        if not isinstance(data, dict):
            raise AppError('Se esperaba un formulario.')
        return data

    def session(self, db):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            token = cookie['sesion'].value if 'sesion' in cookie else ''
        except Exception:
            return None
        if not token:
            return None
        return db.execute('''SELECT u.id, u.email, u.rol, c.id AS cliente_id, c.nombre,
                             c.saga_id, c.telefono FROM sesiones s
                             JOIN usuarios u ON u.id=s.usuario_id
                             LEFT JOIN clientes c ON c.usuario_id=u.id
                             WHERE s.token_hash=? AND s.vence>?''',
                          (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()

    def require(self, db, role=None):
        user = self.session(db)
        if not user:
            raise AppError('Inicia sesión para continuar.', 401)
        if role and user['rol'] != role:
            raise AppError('No tienes permiso para realizar esta acción.', 403)
        return user

    def new_session(self, db, uid):
        token = secrets.token_urlsafe(32)
        db.execute('DELETE FROM sesiones WHERE vence<=?', (int(time.time()),))
        db.execute('INSERT INTO sesiones VALUES (?, ?, ?)',
                   (hashlib.sha256(token.encode()).hexdigest(), uid, int(time.time()) + SESSION_SECONDS))
        return f'sesion={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}'

    def do_GET(self):
        self.dispatch('GET')

    def do_POST(self):
        self.dispatch('POST')

    def do_PUT(self):
        self.dispatch('PUT')

    def dispatch(self, method):
        db = None
        try:
            allowed_hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            host = self.headers.get('Host', '')
            if host not in allowed_hosts:
                raise AppError('Acceso local no permitido.', 403)
            if method != 'GET' and self.headers.get('Origin') not in (None, f'http://{host}'):
                raise AppError('Origen de solicitud no permitido.', 403)
            path = urlsplit(self.path).path
            if method == 'GET' and not path.startswith('/api/'):
                return self.static(path)
            db = connect()
            data = self.body() if method != 'GET' else {}
            result, status, cookie = self.route(db, method, path, data)
            self.reply(status, result, cookie)
        except AppError as exc:
            self.reply(exc.status, {'error': exc.message})
        except sqlite3.IntegrityError:
            self.reply(409, {'error': 'El registro ya existe o sus relaciones no son válidas.'})
        except sqlite3.OperationalError:
            self.reply(503, {'error': 'La base de datos está ocupada o no está disponible. Intenta nuevamente.'})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            print(f'Error interno: {type(exc).__name__}', flush=True)
            self.reply(500, {'error': 'No se pudo completar la operación.'})
        finally:
            if db is not None:
                db.close()

    def static(self, path):
        match = re.fullmatch(r'/imagenes/productos/(\d+)', path)
        if match:
            db = connect()
            try:
                row = db.execute('SELECT contenido FROM imagenes_producto WHERE producto_id=?', (int(match.group(1)),)).fetchone()
            finally:
                db.close()
            if not row:
                raise AppError('Imagen no encontrada.', 404)
            content = row['contenido']
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(content)
            return
        files = {'/': ('index.html', 'text/html'), '/index.html': ('index.html', 'text/html'),
                 '/app.js': ('app.js', 'text/javascript'), '/admin': ('admin.html', 'text/html'),
                 '/admin.js': ('admin.js', 'text/javascript'), '/estilos.css': ('estilos.css', 'text/css')}
        if path not in files:
            raise AppError('Página no encontrada.', 404)
        filename, mime = files[path]
        content = (BASE / 'public' / filename).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        self.wfile.write(content)

    def order(self, db, oid):
        row = db.execute('''SELECT p.*, c.nombre AS cliente, u.email FROM pedidos p
                            JOIN clientes c ON c.id=p.cliente_id JOIN usuarios u ON u.id=c.usuario_id
                            WHERE p.id=?''', (oid,)).fetchone()
        if not row:
            raise AppError('Pedido no encontrado.', 404)
        result = dict(row)
        result.pop('clave_solicitud')
        result.pop('huella_solicitud')
        result['numero'] = f'PD-{oid:06d}'
        result['detalle'] = [dict(r) for r in db.execute('''SELECT d.producto_id, pr.nombre, d.cantidad, d.precio_unitario,
                        d.cantidad*d.precio_unitario AS subtotal FROM detalle_pedido d
                        JOIN productos pr ON pr.id=d.producto_id WHERE pedido_id=? ORDER BY pr.id''', (oid,))]
        result['subtotal'] = sum(r['subtotal'] for r in result['detalle'])
        discount = db.execute('SELECT monto FROM descuentos_pedido WHERE pedido_id=?', (oid,)).fetchone()
        result['descuento'] = discount['monto'] if discount else 0
        result['total'] = result['subtotal'] - result['descuento']
        return result

    def route(self, db, method, path, data):
        if method == 'POST' and path == '/api/boletin':
            email = text_field(data, 'email', 'Correo', 254).lower()
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
                raise AppError('Ingresa un correo electrónico válido.')
            if data.get('consentimiento') is not True:
                raise AppError('Confirma tu suscripción al boletín.')
            with MAIL_LOCK:
                if email in MAIL_PENDING:
                    raise AppError('Ya hay un envío en curso para este correo. Espera a que termine.', 429)
                MAIL_PENDING.add(email)
            try:
                with db:
                    db.execute('BEGIN IMMEDIATE')
                    row = db.execute('SELECT * FROM boletin WHERE email=?', (email,)).fetchone()
                    if row and row['ultimo_envio'] > int(time.time()) - 300:
                        raise AppError('Ya enviamos un correo. Espera cinco minutos antes de solicitar otro.', 429)
                    if row and (row['pedido_id'] is not None or row['vence'] <= int(time.time())):
                        raise AppError('Ya solicitaste tu descuento de bienvenida.')
                    if not row:
                        db.execute('INSERT INTO boletin(email,codigo,vence,consentido_en,ultimo_envio) VALUES (?,?,?,?,0)',
                                   (email, 'BIENVENIDA-' + secrets.token_hex(6).upper(), int(time.time()) + 30*86400, now()))
                send_coupon(email, 'ELGO20')
                with db:
                    db.execute('UPDATE boletin SET ultimo_envio=? WHERE email=?', (int(time.time()), email))
                return {'mensaje': 'El servidor de correo aceptó el envío de ELGO20. Revisa tu bandeja, Promociones y Spam.'}, 200, None
            finally:
                with MAIL_LOCK:
                    MAIL_PENDING.discard(email)

        if method == 'POST' and path == '/api/cupon':
            user = self.require(db, 'cliente')
            code = text_field(data, 'codigo', 'Código', 60).upper()
            coupon_for(db, code, user['email'], user['cliente_id'])
            return {'porcentaje': 20}, 200, None

        if method == 'GET' and path == '/api/inicio':
            user = self.session(db)
            return {'imagenes_version': 1, 'negocio': dict(db.execute('SELECT * FROM negocios WHERE id=1').fetchone()),
                    'sagas': [dict(r) for r in db.execute('SELECT * FROM sagas ORDER BY id')],
                    'usuario': dict(user) if user else None,
                    'configurar_admin': not bool(db.execute("SELECT id FROM usuarios WHERE rol='admin' LIMIT 1").fetchone())}, 200, None

        if method == 'GET' and path == '/api/productos':
            return [with_image(db, r) for r in db.execute('''SELECT p.*, s.codigo AS saga, s.nombre AS nombre_saga
                         FROM productos p JOIN sagas s ON s.id=p.saga_id WHERE p.activo=1 ORDER BY p.id''')], 200, None

        if method == 'GET' and path == '/api/eventos':
            return [dict(r) for r in db.execute('SELECT * FROM eventos WHERE activo=1 ORDER BY fecha, id')], 200, None

        if method == 'GET' and path == '/api/instagram':
            return [dict(r) for r in db.execute('''SELECT id, titulo, enlace, descripcion FROM publicaciones_instagram
                                                   WHERE activo=1 ORDER BY id DESC LIMIT 3''')], 200, None

        if method == 'POST' and path in ('/api/registro', '/api/configurar-admin'):
            email, password = credentials(data)
            setup = path.endswith('configurar-admin')
            name = text_field(data, 'nombre', 'Nombre', 80) if not setup else None
            phone = text_field(data, 'telefono', 'Teléfono', 30, True) if not setup else ''
            saga = integer(data, 'saga_id', 'Saga', 1, 10000) if not setup else None
            password_hash = hash_password(password)
            with db:
                db.execute('BEGIN IMMEDIATE')
                if setup and db.execute("SELECT id FROM usuarios WHERE rol='admin' LIMIT 1").fetchone():
                    raise AppError('El administrador ya está configurado.', 409)
                if not setup and not db.execute('SELECT id FROM sagas WHERE id=?', (saga,)).fetchone():
                    raise AppError('Selecciona una saga válida.')
                if db.execute('SELECT id FROM usuarios WHERE email=?', (email,)).fetchone():
                    raise AppError('Este correo ya está registrado.', 409)
                uid = db.execute('INSERT INTO usuarios(email, password_hash, rol) VALUES (?, ?, ?)',
                                 (email, password_hash, 'admin' if setup else 'cliente')).lastrowid
                if not setup:
                    db.execute('INSERT INTO clientes(usuario_id, nombre, telefono, saga_id) VALUES (?, ?, ?, ?)', (uid, name, phone, saga))
                cookie = self.new_session(db, uid)
            return {'mensaje': 'Cuenta creada.'}, 201, cookie

        if method == 'POST' and path == '/api/login':
            email, password = credentials(data)
            user = db.execute('SELECT * FROM usuarios WHERE email=?', (email,)).fetchone()
            if not user or not check_password(password, user['password_hash']):
                raise AppError('Correo o contraseña incorrectos.', 401)
            with db:
                cookie = self.new_session(db, user['id'])
            return {'mensaje': 'Sesión iniciada.'}, 200, cookie

        if method == 'POST' and path == '/api/logout':
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            if 'sesion' in cookie:
                with db:
                    db.execute('DELETE FROM sesiones WHERE token_hash=?', (hashlib.sha256(cookie['sesion'].value.encode()).hexdigest(),))
            return {'mensaje': 'Sesión cerrada.'}, 200, 'sesion=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'

        if method == 'GET' and path == '/api/pedidos':
            user = self.require(db, 'cliente')
            ids = db.execute('SELECT id FROM pedidos WHERE cliente_id=? ORDER BY id DESC', (user['cliente_id'],)).fetchall()
            return [self.order(db, r['id']) for r in ids], 200, None

        if method == 'POST' and path == '/api/pedidos':
            user = self.require(db, 'cliente')
            key = text_field(data, 'clave', 'Identificador de solicitud', 100)
            items = data.get('items')
            if not isinstance(items, list) or not 1 <= len(items) <= 50:
                raise AppError('El pedido debe contener entre 1 y 50 productos diferentes.')
            normalized = {}
            for item in items:
                if not isinstance(item, dict):
                    raise AppError('Detalle de pedido inválido.')
                pid = integer(item, 'producto_id', 'Producto')
                qty = integer(item, 'cantidad', 'Cantidad', 1, 99)
                if pid in normalized:
                    raise AppError('Un producto no puede repetirse en el detalle.')
                normalized[pid] = qty
            code = text_field(data, 'codigo', 'Código', 60, True).upper()
            fingerprint = hashlib.sha256(json.dumps([sorted(normalized.items()), code]).encode()).hexdigest()
            with db:
                db.execute('BEGIN IMMEDIATE')
                previous = db.execute('SELECT id, huella_solicitud FROM pedidos WHERE cliente_id=? AND clave_solicitud=?', (user['cliente_id'], key)).fetchone()
                if previous:
                    if previous['huella_solicitud'] != fingerprint:
                        raise AppError('La solicitud anterior tenía otros productos. Actualiza el carrito.', 409)
                    return self.order(db, previous['id']), 200, None
                if code:
                    coupon_for(db, code, user['email'], user['cliente_id'])
                products = []
                for pid, qty in sorted(normalized.items()):
                    product = db.execute('SELECT * FROM productos WHERE id=? AND activo=1', (pid,)).fetchone()
                    if not product:
                        raise AppError('Uno de los productos ya no está disponible.', 409)
                    if product['stock'] < qty:
                        raise AppError(f"Stock insuficiente para {product['nombre']}. Disponibles: {product['stock']}.", 409)
                    products.append((product, qty))
                oid = db.execute('''INSERT INTO pedidos(cliente_id, fecha, estado, clave_solicitud, huella_solicitud)
                                    VALUES (?, ?, 'pendiente_pago', ?, ?)''', (user['cliente_id'], now(), key, fingerprint)).lastrowid
                for p, qty in products:
                    db.execute('INSERT INTO detalle_pedido VALUES (?, ?, ?, ?)', (oid, p['id'], qty, p['precio']))
                    db.execute('UPDATE productos SET stock=stock-? WHERE id=?', (qty, p['id']))
                if code:
                    amount = (sum(p['precio'] * qty for p, qty in products) * 20 + 50) // 100
                    db.execute('INSERT INTO descuentos_pedido VALUES (?,?)', (oid, amount))
                    db.execute('UPDATE boletin SET pedido_id=? WHERE email=?', (oid, user['email']))
                result = self.order(db, oid)
            return result, 201, None

        if path.startswith('/api/admin/'):
            self.require(db, 'admin')
            if method == 'GET' and path == '/api/admin/pedidos':
                ids = db.execute('SELECT id FROM pedidos ORDER BY id DESC').fetchall()
                return [self.order(db, r['id']) for r in ids], 200, None
            if method == 'GET' and path == '/api/admin/clientes':
                return [dict(r) for r in db.execute('''SELECT c.id, c.nombre, c.telefono, u.email, s.nombre AS saga
                                    FROM clientes c JOIN usuarios u ON u.id=c.usuario_id LEFT JOIN sagas s ON s.id=c.saga_id ORDER BY c.id''')], 200, None
            if method == 'GET' and path == '/api/admin/productos':
                return [with_image(db, r) for r in db.execute('SELECT * FROM productos ORDER BY id')], 200, None
            if method == 'GET' and path == '/api/admin/eventos':
                return [dict(r) for r in db.execute('SELECT * FROM eventos ORDER BY fecha, id')], 200, None
            if method == 'GET' and path == '/api/admin/instagram':
                return [dict(r) for r in db.execute('SELECT * FROM publicaciones_instagram ORDER BY id DESC')], 200, None
            if method == 'POST' and re.fullmatch(r'/api/admin/pedidos/\d+/cancelar', path):
                oid = int(path.split('/')[4])
                with db:
                    db.execute('BEGIN IMMEDIATE')
                    order = self.order(db, oid)
                    if order['estado'] != 'cancelado':
                        for item in order['detalle']:
                            db.execute('UPDATE productos SET stock=stock+? WHERE id=?', (item['cantidad'], item['producto_id']))
                        db.execute("UPDATE pedidos SET estado='cancelado' WHERE id=?", (oid,))
                return self.order(db, oid), 200, None
            instagram_match = re.fullmatch(r'/api/admin/instagram(?:/(\d+))?', path)
            if instagram_match and method in ('POST', 'PUT'):
                rid = instagram_match.group(1)
                if (method == 'PUT') != bool(rid):
                    raise AppError('Ruta inválida.', 404)
                title = text_field(data, 'titulo', 'Título', 160)
                link = instagram_link(data)
                description = text_field(data, 'descripcion', 'Texto', 400, True)
                active = integer(data, 'activo', 'Visibilidad', 0, 1)
                with db:
                    if rid:
                        cursor = db.execute('''UPDATE publicaciones_instagram
                                             SET titulo=?, enlace=?, descripcion=?, activo=? WHERE id=?''',
                                            (title, link, description, active, int(rid)))
                        if cursor.rowcount != 1:
                            raise AppError('Publicación no encontrada.', 404)
                    else:
                        rid = db.execute('''INSERT INTO publicaciones_instagram
                                          (negocio_id, titulo, enlace, descripcion, activo, creado_en)
                                          VALUES (1, ?, ?, ?, ?, ?)''',
                                         (title, link, description, active, now())).lastrowid
                return {'id': int(rid), 'mensaje': 'Publicación guardada.'}, 200 if method == 'PUT' else 201, None
            match = re.fullmatch(r'/api/admin/(productos|eventos)(?:/(\d+))?', path)
            if match and method in ('POST', 'PUT'):
                resource, rid = match.groups()
                if (method == 'PUT') != bool(rid):
                    raise AppError('Ruta inválida.', 404)
                name = text_field(data, 'nombre', 'Nombre', 160)
                active = integer(data, 'activo', 'Visibilidad', 0, 1)
                if resource == 'productos':
                    image_bytes = product_image(data['imagen']) if 'imagen' in data else None
                    saga = integer(data, 'saga_id', 'Saga')
                    if not db.execute('SELECT id FROM sagas WHERE id=?', (saga,)).fetchone():
                        raise AppError('Selecciona una saga válida.')
                    price = integer(data, 'precio', 'Precio en pesos', 1, 100000000)
                    stock = integer(data, 'stock', 'Stock', 0, 1000000)
                    fields, values = ['nombre', 'saga_id', 'precio', 'stock', 'activo'], [name, saga, price, stock, active]
                else:
                    day = text_field(data, 'fecha', 'Fecha', 10)
                    try:
                        if date.fromisoformat(day).isoformat() != day:
                            raise ValueError()
                    except ValueError:
                        raise AppError('Ingresa una fecha válida con formato AAAA-MM-DD.')
                    place = text_field(data, 'ubicacion', 'Ubicación', 240)
                    detail = text_field(data, 'detalle', 'Detalle', 400, True)
                    fields, values = ['nombre', 'fecha', 'ubicacion', 'detalle', 'activo'], [name, day, place, detail, active]
                with db:
                    if rid:
                        cursor = db.execute(f'UPDATE {resource} SET ' + ', '.join(f'{f}=?' for f in fields) + ' WHERE id=?', values + [int(rid)])
                        if cursor.rowcount != 1:
                            raise AppError('Registro no encontrado.', 404)
                    else:
                        rid = db.execute(f'INSERT INTO {resource}(negocio_id, ' + ', '.join(fields) + ') VALUES (1, ' + ', '.join('?' for _ in fields) + ')', values).lastrowid
                    if resource == 'productos' and 'imagen' in data:
                        if image_bytes is None:
                            db.execute('DELETE FROM imagenes_producto WHERE producto_id=?', (int(rid),))
                        else:
                            db.execute('INSERT INTO imagenes_producto VALUES (?,?,?) ON CONFLICT(producto_id) DO UPDATE SET contenido=excluded.contenido, version=excluded.version',
                                       (int(rid), image_bytes, hashlib.sha256(image_bytes).hexdigest()[:16]))
                return {'id': int(rid), 'mensaje': 'Cambios guardados.'}, 200 if method == 'PUT' else 201, None
        raise AppError('Recurso no encontrado.', 404)


def main():
    global DB_PATH
    parser = argparse.ArgumentParser(description='3Dedos · servidor local con SQLite')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--db', type=Path, default=DB_PATH)
    parser.add_argument('--abrir', action='store_true')
    args = parser.parse_args()
    DB_PATH = args.db.resolve()
    initialize()
    server = None
    for port in range(args.port, min(args.port + 20, 65536)):
        try:
            server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
            break
        except OSError:
            continue
    if server is None:
        print('No se encontró un puerto disponible. Cierra las ventanas antiguas de la tienda y vuelve a iniciar.', flush=True)
        return 1
    if server.server_port != args.port:
        print('Hay otra tienda abierta. Esta versión se abrirá en una dirección nueva; usa la pestaña que se abre ahora.', flush=True)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'3Dedos funcionando en {url}\nBase de datos: {DB_PATH}\nMantén esta ventana abierta. Ctrl+C para detener.\n', flush=True)
    if args.abrir:
        Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor detenido.')
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
