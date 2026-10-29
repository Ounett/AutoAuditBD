#!/usr/bin/env python3

import secrets
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import auth_local

if __name__=='__main__':
    auth_local.initialize()
    admins=[u for u in auth_local.list_users() if u['rol']=='admin' and u['activo']]
    if not admins:
        print('No hay una cuenta administradora activa. Revisar datos locales.')
        sys.exit(1)
    u=admins[0]
    new=secrets.token_urlsafe(17)
    auth_local.set_password(u['id'],new)
    print('Nueva contraseña temporal para usuario:',u['usuario'])
    print(new)
    print('Cambiar la contraseña desde la interfaz después de iniciar sesión.')
