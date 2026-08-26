# Preparación de Lux para hosting gratuito

Lux es un proyecto Django independiente de Render. El proveedor solo necesita ejecutar la aplicación con Gunicorn y proporcionar una base de datos PostgreSQL (o, durante las pruebas, SQLite).

## Variables de producción

No se guardan en Git ni se comparten. En el panel del hosting se configurarán:

```text
DJANGO_ENV=production
DEBUG=False
SECRET_KEY=<clave aleatoria privada>
ALLOWED_HOSTS=<dominio-del-servidor>
CSRF_TRUSTED_ORIGINS=https://<dominio-del-servidor>
DATABASE_URL=postgresql://<usuario>:<contraseña>@<host>:5432/<base>
```

El comando de arranque es:

```text
gunicorn lux.wsgi:application
```

Antes del primer arranque se ejecutan:

```text
python manage.py migrate
python manage.py collectstatic --noinput
```

## PythonAnywhere

PythonAnywhere no instala automáticamente las dependencias de `requirements.txt` en el entorno virtual. En una consola Bash del servidor:

```bash
cd /home/Lux0/lux
mkvirtualenv --python=/usr/bin/python3.13 luxenv
workon luxenv
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

En el archivo WSGI de la pestaña **Web**, antes de `get_wsgi_application()`, configura las variables de producción. Sustituye el dominio por el que aparece en tu aplicación:

```python
import os
import sys

path = "/home/Lux0/lux"
if path not in sys.path:
	sys.path.append(path)

os.environ["DJANGO_ENV"] = "production"
os.environ["DEBUG"] = "False"
os.environ["SECRET_KEY"] = "pega-aqui-una-clave-larga-y-aleatoria"
os.environ["ALLOWED_HOSTS"] = "lux0.pythonanywhere.com"
os.environ["CSRF_TRUSTED_ORIGINS"] = "https://lux0.pythonanywhere.com"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lux.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Genera la clave una sola vez en una consola del servidor y pégala en el WSGI; no la subas a Git:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

En la configuración **Web**, selecciona `/home/Lux0/.virtualenvs/luxenv` como entorno virtual y pulsa **Reload**. Si usas PostgreSQL, añade también `DATABASE_URL` al WSGI; si no, el proyecto utilizará SQLite.

## Aplicación Android

Cuando exista el dominio HTTPS definitivo, se define temporalmente en PowerShell antes de crear el paquete Android:

```powershell
$env:LUX_WEB_URL = "https://tu-dominio.example"
npm run android:prepare
```

Ese valor no es una dependencia de Render: será la dirección del servidor Django que elijamos. Nunca se debe usar `localhost` en una aplicación que instalarán otras personas.
