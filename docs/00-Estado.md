# 📍 Estado del proyecto YapeChecker

> Segunda memoria del proyecto (2026-08-27). Escrito porque el proyecto es grande y el contexto de la sesión de IA se agota — leer esto primero al retomar, en cualquier herramienta.

## Qué es esto, en una frase

Sistema para registrar automáticamente los pagos por Yape que recibe el negocio, para saber qué ingresó sin anotarlo a mano.

## Piezas que existen (confirmado por inspección directa del código, 2026-08-27)

1. **Backend Python (FastAPI)** — `FastApi.py`, en esta misma carpeta. Ya andaba, tiene Dockerfile y config de deploy a Fly.io (`fly.toml`, región `scl`/Santiago). Ver [[Backend-FastAPI]] para el detalle completo.
   - Expone `POST /api/payment` para RECIBIR un pago (monto, remitente, fecha, hora) y lo guarda en una hoja de **Google Sheets** (`YapeChecker_Pagos`) vía `gspread` + `credentials.json` (cuenta de servicio de Google — está en `.gitignore`, correctamente excluida de git, no la subas nunca a un repo).
   - Expone `GET /api/payments` (listar) y `PUT /api/payments/{id}` (actualizar tienda/estado).
   - **Esto es solo el receptor/registro.** No detecta nada por sí solo — necesita que algo más (la app Android) le mande el POST.
2. **App Android** — `C:\Users\mcg22\AndroidStudioProjects\YapeChecker2\` (carpeta separada). **Diagnóstico confirmado, ver [[App-Android]]:** el código está bien hecho (usa `NotificationListenerService`, la API oficial de Android — la hipótesis original de "Android mata el proceso en segundo plano" NO era la causa real). La causa real es mucho más simple: `ApiService.kt` tiene la URL del backend **hardcodeada a una IP local** (`http://192.168.1.61:8000`), así que solo funcionaba en la misma red WiFi que una laptop específica. El arreglo es desplegar el backend a Fly.io (ya hay `fly.toml` listo) y apuntar la app ahí — no hace falta reescribir nada.
3. **🎁 Hallazgo no esperado — calculadora de precios de fotocopias, ya construida:** dentro de este mismo `FastApi.py` hay una funcionalidad **completamente aparte** de Yape: `/api/calculate-price` y `/api/analyze-page`. Sube un PDF/Word/Excel/PPT/imagen, cuenta páginas, y para imágenes usa **OpenCV** para analizar cuánto color tiene cada hoja (saturación HSV + aproximación CMYK) y así cotizar B/N vs. color automáticamente. Tiene su propia tabla de precios base (`data/tabla_precios_A4_base.csv`) y ya está documentada en [`docs/CALCULADORA_A4_Y_TABLA_PRECIOS.md`](CALCULADORA_A4_Y_TABLA_PRECIOS.md) (nota preexistente, con los precios que definiste). Tiene hasta el logo de Copy-On en el frontend estático (`static/`). **Esto es directamente para Copy-On**, no para Yape — quedó anotado como idea en el vault de Copy-On (`docs/05-Ideas/Bandeja-de-Ideas.md`) para integrarlo ahí más adelante, no es parte del sprint de estos días.

## Seguridad — verificado

- `credentials.json` (clave de Google) **NO está trackeada por git** (confirmado con `git ls-files`) — correcto, seguí así. Nunca la pegues en el chat ni la subas a un repo público.
- **2026-08-31 — clave de servicio expuesta en el chat y rotada.** La clave original (`private_key_id` que empezaba con `dc08b9af...`) se pegó completa en una conversación con la IA para depurar el deploy. Se pidió rotarla de inmediato desde Google Cloud Console (borrar esa key, crear una nueva). **Si en algún momento el backend deja de poder autenticar con Google Sheets, lo primero a revisar es si la clave activa en la variable de entorno `GOOGLE_CREDENTIALS_JSON` de Render es la nueva (rotada) y no la vieja.**

## ✅ Deploy — funcionando en producción (2026-09-01)

Se eligió **Render** en vez de Fly.io (Fly pedía tarjeta de crédito; el usuario prefirió no cargarla). `render.yaml` en el repo. Dos problemas encontrados y resueltos en el camino: faltaba `python-multipart` en `requirements.txt` (rompía el arranque, nada que ver con credenciales), y la clave de servicio original quedó expuesta en el chat y se rotó (ver nota de seguridad arriba).

- **URL pública confirmada:** https://yapechecker.onrender.com
- **`/health`** responde 200 OK.
- **`/api/payment`** probado con un pago de prueba real → llegó a la Google Sheet en 2.4s (tras el primer "cold start" del plan gratuito, que puede tardar ~30-50s si el servicio estuvo dormido).
- **App Android actualizada:** `ApiService.kt` con la URL real, timeouts subidos de 10s a 45s (para cubrir el cold start sin que la app marque el envío como fallido innecesariamente — igual está cubierto por la cola de reintento si pasara). APK de debug recompilada.

**Pendiente:** instalar la APK nueva en el celular real y probar con un Yape de verdad (no solo el endpoint a mano).

## Idea para más adelante — cuentas de usuario propias (no ahora)

El usuario propuso (2026-08-31): que la app permita que cada negocio se registre y el sistema cree automáticamente su propia hoja de Google Sheets, en vez de usar una única cuenta de servicio compartida. Es una buena idea de producto (convierte esto en una herramienta multi-usuario/SaaS), pero implica un rediseño real: login con Google (OAuth), permisos de Drive para crear hojas, y almacenamiento seguro de credenciales por usuario — varias horas de trabajo, no un ajuste. **Explícitamente pospuesta** por el tiempo limitado del sprint; por ahora se usa la cuenta de servicio del usuario para todos (aceptado por él mismo como solución de prueba).

## Decisión pendiente — prioridad con el tiempo que queda

El usuario tiene **~2 días de Claude** antes de la pausa, repartidos entre esto y el sprint multi-negocio de Copy-On (que todavía no tiene el módulo de ventas terminado). Ver `Registro-de-Trabajos.md` en el vault de Copy-On para el estado de eso.

## Relacionados
- [[Backend-FastAPI]]
- [[Registro]]
- Proyecto hermano: `C:\Users\mcg22\Documents\PROYECTOS PROPIOS\Copyon\docs\04-Trabajo\Continuidad-y-Handoff.md` (ahí quedó la primera nota sobre este mismo problema, antes de que se retomara hoy)
