# GOLES HOY — corrección del proyecto subido a GitHub

## Qué corrige
- El motor **ya no depende de API-FOOTBALL ni solicita ninguna clave**.
- Consulta TheSportsDB con clave pública `123` y publica estado actual con fecha válida, incluso si hay cero pronósticos o falla una fuente.
- No muestra pronósticos antiguos como si fueran de hoy ni inventa cuotas, tarjetas o probabilidades.
- Mantiene historial y protección contra fuentes caídas.
- `update.yml` y `android.yml` están exclusivamente en `.github/workflows/`; no hay carpeta `workflows/` duplicada.
- Las cuotas no se muestran en la APK.

## Limitación importante
TheSportsDB gratuito limita `eventsday` a **3 eventos** y no proporciona datos suficientes de cuotas e historial para elegir diez partidos. Aposta.LA y Sofascore no tienen integración autorizada verificada en este proyecto. No afirmamos que haya 10 pronósticos automáticos ni que el motor haga un cruce que no puede hacer. El archivo `data/authorized_analysis.json` es un **formato opcional para un proveedor autorizado** con datos verificables; no se suministran datos inventados.

## Puesta en marcha
1. Sustituir los archivos del repositorio por el contenido de este ZIP **conservando `.github`**; no arrastrar el ZIP directamente a GitHub.
2. Ejecutar Actions → GOLES HOY - Actualizar pronosticos → Run workflow.
3. Comprobar `data/latest.json`: fecha/hora actuales y estado explícito. No hace falta volver a compilar APK para actualizar el JSON remoto.
4. La compilación APK está configurada en `.github/workflows/android.yml`, pero **esta entrega no ha sido compilada en GitHub**.

La programación usa 10:00 y 20:00 UTC = 07:00 y 17:00 en Paraguay; GitHub puede retrasar ejecuciones. No se garantiza ejecución al minuto.
