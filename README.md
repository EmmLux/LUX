# LUX

LUX es una plataforma Django server-rendered para explorar productos, servicios y oportunidades, conversar, crear acuerdos y registrar operaciones verificables.

## Desarrollo

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Tests:

```powershell
python manage.py check
python manage.py test
```

## Variables de entorno

- `SECRET_KEY`: obligatoria fuera de desarrollo.
- `DEBUG`: `True` solo localmente.
- `DATABASE_URL`: SQLite local por defecto o PostgreSQL.
- `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`: dominios públicos.
- `LUX_PLATFORM_FEE_PERCENT`: comisión de plataforma LUX, `10` por defecto. No representa utilidad neta: los costes del procesador se separan en la transacción.
- `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`: claves TEST de Stripe; nunca se guardan en el código.
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`: correo de producción.

## Flujos implementados

`Explorar -> publicación -> mensajes -> acuerdo -> aceptación -> Checkout Stripe TEST -> webhook firmado -> pago -> operación -> completado -> evaluación`.

Los precios usan `DecimalField` y `Decimal`. La comisión la absorbe el vendedor: el comprador paga el precio publicado y el resumen muestra comisión LUX y cantidad destinada al vendedor.

Los pagos usan Checkout alojado y cargos indirectos de Stripe Connect. Django no almacena tarjetas ni confirma pagos desde el navegador. El webhook `/webhooks/stripe/` valida `Stripe-Signature` y actualiza de forma idempotente la transacción.

La reputación solo se crea para transacciones completadas. Las operaciones externas no generan historial ni evaluaciones verificables. Reportes y advertencias se administran desde Django Admin.

## Stripe TEST

1. Instalar dependencias con `pip install -r requirements.txt`.
2. El vendedor entra en `Perfil > Configurar cobros`; LUX crea una cuenta Express y redirige al onboarding oficial de Stripe.
3. Al volver, LUX consulta `charges_enabled` y `payouts_enabled`; solo entonces muestra el estado `configurada`.
4. Configurar el endpoint `/webhooks/stripe/` con la clave `STRIPE_WEBHOOK_SECRET`.
5. Usar tarjetas de prueba oficiales de Stripe.

## Pendiente antes de producción

- Completar onboarding OAuth/Connect y requisitos legales/fiscales del marketplace.
- Configurar almacenamiento persistente para imágenes.
- Añadir recuperación/verificación de cuenta, rate limiting, disputas y controles antifraude revisados por moderación.
- Añadir evaluación visual completa y pruebas end-to-end del checkout con Stripe CLI.
- Revisar privacidad, Data Safety de Android, impuestos, reembolsos y términos de servicio.
- Usar PostgreSQL y ejecutar migraciones/collectstatic en el proveedor de despliegue.
