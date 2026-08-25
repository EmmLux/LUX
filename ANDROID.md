# Lux para Android

Lux es un backend Django con páginas server-rendered. La app Android usa Capacitor como un contenedor nativo seguro para la misma experiencia web, base de datos, autenticación, publicaciones y mensajes. No replica ni migra la lógica de Django a un cliente distinto.

## Requisitos de compilación

- Node.js LTS y Android Studio con Android SDK API 36.
- JDK 17 (el compatible con Android Gradle Plugin).
- Una URL de producción HTTPS para este despliegue de Lux; el dispositivo no puede alcanzar el servidor de desarrollo local sin una red/túnel explícito.

## Primera generación

En PowerShell, desde la raíz del repositorio:

```powershell
npm install
$env:LUX_WEB_URL = "https://tu-dominio-lux.example"
npm run android:prepare
```

`capacitor.config.ts` rechaza una URL sin HTTPS. Capacitor crea `android/` con el package ID `com.emmlux.app`, el nombre **Lux**, iconos y splash propios. Antes de repetir `android:assets`, verifica visualmente los recursos en Android Studio.

`android:prepare` crea `android/`, genera los iconos/splash y deja estos valores en `android/app/build.gradle`:

```gradle
namespace "com.emmlux.app"
compileSdk 36
defaultConfig {
    applicationId "com.emmlux.app"
    minSdk 23
    targetSdk 36
    versionCode 1
    versionName "1.0.0"
}
```

El manifest generado sólo debe conservar el permiso `android.permission.INTERNET`; Lux no utiliza ubicación, cámara, contactos, archivos, Bluetooth ni notificaciones. Capacitor gestiona correctamente volver atrás con el historial de navegación del WebView y sale de la app al agotarse.

## Builds

Con un emulador/dispositivo conectado:

```powershell
npm run android:debug
```

Para release, crea una keystore de subida que no se comitea y exporta sus valores antes de ejecutar el bundle:

```powershell
$env:LUX_UPLOAD_STORE_FILE = "C:\ruta-segura\lux-upload.keystore"
$env:LUX_UPLOAD_STORE_PASSWORD = "..."
$env:LUX_UPLOAD_KEY_ALIAS = "lux-upload"
$env:LUX_UPLOAD_KEY_PASSWORD = "..."
npm run android:bundle
```

El resultado esperado es `android/app/build/outputs/bundle/release/app-release.aab`. Google Play firma la distribución final con Play App Signing; guarda la keystore de subida y sus contraseñas fuera del repositorio.

## Checklist de publicación

- Configurar `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` en producción; nunca usar la clave de desarrollo.
- Desplegar el backend exclusivamente por HTTPS y probar login, registro, creación/edición/borrado de publicaciones y mensajes desde un teléfono real.
- Crear una política de privacidad pública: Lux procesa correo, teléfono opcional, perfil, publicaciones y mensajes privados. Enlazarla desde Lux y declararla en Play Console.
- Completar en Play Console la ficha, clasificación de contenido, declaración de Data safety, correo de soporte, capturas de móvil e identidad de desarrollador.
- Sustituir `com.emmlux.app` sólo si ya existe otra aplicación con ese ID; cambiarlo antes del primer lanzamiento es seguro, después no se puede cambiar.
