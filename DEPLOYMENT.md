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

## Aplicación Android

Cuando exista el dominio HTTPS definitivo, se define temporalmente en PowerShell antes de crear el paquete Android:

```powershell
$env:LUX_WEB_URL = "https://tu-dominio.example"
npm run android:prepare
```

Ese valor no es una dependencia de Render: será la dirección del servidor Django que elijamos. Nunca se debe usar `localhost` en una aplicación que instalarán otras personas.
