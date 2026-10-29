from __future__ import annotations
import os
import re
import secrets
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

BASE = Path(__file__).resolve().parent
LOCAL = Path(os.environ.get('AUTOAUDIT_LOCAL_DIR', str(BASE / '.local')))
DB = LOCAL / 'usuarios.sqlite3'
KEY = LOCAL / 'session.key'
USERNAME = re.compile(r'^[a-zA-Z0-9_.-]{3,32}$')


def _private_file(path, data=None):
    LOCAL.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(LOCAL, 0o700)
    if not path.exists():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as out:
            if data is not None:
                out.write(data)
    os.chmod(path, 0o600)


def connect():
    _private_file(DB)
    cn = sqlite3.connect(DB, timeout=10)
    cn.row_factory = sqlite3.Row
    return cn


def initialize():
    _private_file(KEY, secrets.token_bytes(32))
    with connect() as cn:
        cn.execute('''CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            clave_hash TEXT NOT NULL,
            rol TEXT NOT NULL CHECK (rol IN ('admin','usuario')),
            activo INTEGER NOT NULL DEFAULT 1,
            creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        count = cn.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0]
        if count == 0:
            first_password = secrets.token_urlsafe(15)
            cn.execute('INSERT INTO usuarios(usuario,clave_hash,rol) VALUES(?,?,?)',
                       ('admin', generate_password_hash(first_password, method='scrypt'), 'admin'))
            print('\n' + '='*65)
            print(' PRIMER ACCESO A AUTOAUDIT (anotar esta clave)')
            print(' Usuario: admin')
            print(' Clave inicial: ' + first_password)
            print(' Cambiarla desde Usuarios -> Mi contraseña al ingresar.')
            print('='*65 + '\n', flush=True)
    return KEY.read_bytes()


def get_user(uid):
    with connect() as cn:
        row = cn.execute('SELECT id,usuario,rol,activo FROM usuarios WHERE id=?', (uid,)).fetchone()
        return dict(row) if row else None


def authenticate(username, password):
    with connect() as cn:
        row = cn.execute('SELECT * FROM usuarios WHERE usuario=? AND activo=1', (username,)).fetchone()
    if not row or not check_password_hash(row['clave_hash'],password):
        return None
    return {'id':row['id'], 'usuario':row['usuario'], 'rol':row['rol'], 'activo':row['activo']}


def list_users():
    with connect() as cn:
        return [dict(x) for x in cn.execute('SELECT id,usuario,rol,activo,creado FROM usuarios ORDER BY id')]


def add_user(username,password,role):
    if not USERNAME.fullmatch(str(username)):
        raise ValueError('El usuario debe tener 3–32 caracteres: letras, números, punto, guion o _')
    if len(password) < 10:
        raise ValueError('La contraseña debe tener por lo menos 10 caracteres')
    if role not in ('admin','usuario'):
        raise ValueError('Rol no permitido')
    try:
        with connect() as cn:
            cn.execute('INSERT INTO usuarios(usuario,clave_hash,rol) VALUES(?,?,?)',
                       (username,generate_password_hash(password, method='scrypt'),role))
    except sqlite3.IntegrityError:
        raise ValueError('Ya existe ese usuario') from None


def set_password(uid, password):
    if len(password) < 10:
        raise ValueError('La contraseña debe tener por lo menos 10 caracteres')
    with connect() as cn:
        cn.execute('UPDATE usuarios SET clave_hash=? WHERE id=?',
                   (generate_password_hash(password,method='scrypt'),uid))


def check_old_password(uid, old):
    with connect() as cn:
        row=cn.execute('SELECT clave_hash FROM usuarios WHERE id=?',(uid,)).fetchone()
        return bool(row and check_password_hash(row[0],old))


def set_enabled(uid, active, current_id):
    with connect() as cn:
        row=cn.execute('SELECT rol,activo FROM usuarios WHERE id=?',(uid,)).fetchone()
        if not row: raise ValueError('Usuario no encontrado')
        if uid==current_id and not active: raise ValueError('No se puede desactivar la sesión propia')
        if row['rol']=='admin' and not active:
            count=cn.execute("SELECT COUNT(*) FROM usuarios WHERE rol='admin' AND activo=1").fetchone()[0]
            if count<2: raise ValueError('Debe quedar al menos un administrador habilitado')
        cn.execute('UPDATE usuarios SET activo=? WHERE id=?',(int(active),uid))
