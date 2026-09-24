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


## Alcance de esta revisión
La aplicación separa la cartelera parcial de TheSportsDB de los pronósticos verificados.
Los partidos mostrados en «Cartelera disponible» NO son selecciones +2.5 ni BTTS.
La API gratuita de TheSportsDB limita el calendario diario y no proporciona una
cartelera completa de Apostala ni las cuotas necesarias para calcular el Top 10.
El workflow se programa a las 08:00 Paraguay (11:00 UTC), sujeto a demoras de GitHub.

## Fuentes múltiples: alcance verificado

El motor combina TheSportsDB (cartelera parcial) con `data/fixture_sources.json`,
una **exportación aportada por el propietario con permiso de uso**. No extrae
automáticamente datos de Sofascore ni de Apostala: no se ha verificado una API
pública autorizada para esos servicios. Los diarios pueden aportar contexto,
pero sus noticias no equivalen a estadísticas ni cuotas. No inventar encuentros.

Formato opcional de `data/fixture_sources.json` (no se incluye un archivo con
partidos de ejemplo en producción):

```json
{"fecha":"AAAA-MM-DD","fuentes":[{"nombre":"Apostala (exportación autorizada)","partidos":[{"id":"ID_REAL","hora":"2026-09-24T18:00:00-03:00","liga":"Liga real","pais":"PY","local":"Equipo A","visitante":"Equipo B"}]}]}
```

Las fuentes se deduplican por local, visitante y hora UTC; la cartelera nunca
se presenta como pronóstico. Para publicar selecciones, el archivo opcional
`data/authorized_analysis.json` requiere probabilidades y cuotas fundamentadas.
No se prometen diez pronósticos si faltan datos. La automatización de GitHub
publica solo archivos ya accesibles en el repositorio: no puede leer un archivo
que permanezca exclusivamente en el celular.
