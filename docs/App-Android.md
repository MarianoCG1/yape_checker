# App Android — YapeChecker2

> Ubicación real: `C:\Users\mcg22\AndroidStudioProjects\YapeChecker2\` (carpeta separada del backend Python, que vive en `C:\Users\mcg22\Documents\PROYECTOS PROPIOS\YapeChecker\`). Encontrada y revisada el 2026-08-27.

## Diagnóstico: por qué "quedó demasiado en stand by"

**No hace falta reconstruir la app.** El código ya está bien planteado:

- `NotificationListener.kt` usa `NotificationListenerService`, la API **oficial** de Android para leer notificaciones — no un hack de accesibilidad ni captura de pantalla. Filtra correctamente por el paquete de Yape (`com.bcp.innovacxion.yapeapp`), y parsea monto + remitente con varios patrones de regex (cubre "te envió un pago por S/", "recibiste S/ de", "te yapeó S/", y un genérico de respaldo).
- `AndroidManifest.xml` declara el servicio y los permisos correctamente (`BIND_NOTIFICATION_LISTENER_SERVICE`, `INTERNET`, `POST_NOTIFICATIONS`).
- `MainActivity.kt` verifica si el permiso de notificaciones está concedido y tiene un botón de prueba de conexión.

**La causa real, encontrada en `ApiService.kt` línea 16:**

```kotlin
private const val BASE_URL = "http://192.168.1.61:8000"
```

Está **hardcodeado a la IP local de una laptop específica** en un momento específico. Esto solo funciona si:
1. El celular está en la misma red WiFi que esa laptop, Y
2. Esa laptop tiene el backend FastAPI corriendo en ese momento, Y
3. Esa laptop conserva esa misma IP (las IPs de DHCP cambian).

En cuanto el celular sale de esa red (o la laptop se apaga, o cambia de IP), cada intento de `sendPayment()` falla en silencio — el error se loguea pero no hay reintento ni cola local, así que el pago simplemente se pierde. Esto explica perfectamente la sensación de "quedó en stand by": probablemente funcionó durante la prueba en vivo con la laptop prendida al lado, y dejó de hacer nada útil apenas se alejó.

## El arreglo (pequeño, no una reescritura)

1. **Desplegar el backend a un lugar siempre accesible.** Se intentó Fly.io primero, pero pide tarjeta de crédito antes de permitir cualquier deploy (verificación anti-abuso) — el usuario prefirió no cargarla. **Se cambió a Render** (2026-08-31), consistente con el plan de hosting de Copy-On. `render.yaml` ya listo en el repo del backend.
2. **Cambiar `BASE_URL`** en `ApiService.kt` a la URL pública de Render (previsiblemente `https://yapechecker.onrender.com`, se confirma al desplegar) en vez de la IP local.
3. **Recompilar la APK** (`./gradlew assembleDebug` o similar) e instalarla en el celular reemplazando la versión vieja.
4. **Probar con un Yape real** (o simulando la notificación) para confirmar que el pago llega a la Google Sheet.

### Pasos de deploy en Render (acción del usuario)

`credentials.json` (la clave de Google) está gitignoreada a propósito — no se sube al repo. El código ya soporta leerla desde una variable de entorno (`GOOGLE_CREDENTIALS_JSON`) además del archivo local.

1. Entrar a [render.com](https://render.com) y crear cuenta (o loguearse) — con GitHub es lo más directo, ya que el repo está ahí.
2. **New → Blueprint** → elegir el repo `MarianoCG1/yape_checker` → Render detecta `render.yaml` automáticamente.
3. Cuando pida la variable `GOOGLE_CREDENTIALS_JSON`: abrir `credentials.json` en esta carpeta, copiar **todo** el contenido tal cual, pegarlo como valor de esa variable en el formulario de Render.
4. Confirmar el deploy. Al terminar, Render muestra la URL pública (`https://yapechecker.onrender.com` o similar) — avisar esa URL exacta para actualizar `ApiService.kt`.

### Mejora recomendada, no bloqueante
Agregar una cola local simple (ej. guardar en `SharedPreferences` o una tabla SQLite local si el POST falla, y reintentar) para que un corte de señal no pierda el pago silenciosamente. No es necesario para la primera versión funcional — se puede sumar después.

## Stack técnico
- Kotlin, sin frameworks de red externos (usa `HttpURLConnection` plano — funciona, aunque una librería como Retrofit simplificaría reintentos a futuro).
- Backend: ver `../../YapeChecker/docs/00-Estado.md` (proyecto hermano, carpeta separada).

## Relacionados
- `../../YapeChecker/docs/00-Estado.md` (backend + hallazgo de la calculadora de Copy-On)
