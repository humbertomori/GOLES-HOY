# GOLES HOY — entrega técnica (no APK verificada)

## Qué se probó
- Pruebas unitarias del motor y simulaciones de caída de fuentes (ver `tests/`).
- Modo sin cuenta: TheSportsDB `eventsday.php`, clave pública 123, publica cartelera consultada **sin inventar pronósticos**.
- Modo API-FOOTBALL: requiere `API_FOOTBALL_KEY` en Secrets de GitHub; usa fixtures, odds y estadísticas. Sin esa clave NO se generan pronósticos.

## Instalación
1. Crear repositorio **público** `humbertomori/GOLES-HOY` (o cambiar `web/config.js` y `android/app/src/main/assets/config.js`). Subir los archivos de este ZIP a la raíz del repositorio.
2. Settings → Actions → General → Workflow permissions → Read and write permissions.
3. Actions → GOLES HOY - Actualizar pronosticos → Run workflow. Verificar ejecución verde y archivos `data/latest.json`, `data/history.json`. Sin clave, el resultado esperado es **cero pronósticos**, no un fallo.
4. Para activar pronósticos, registrar clave API-FOOTBALL como secreto `API_FOOTBALL_KEY` (nunca enviarla por chat). Probar que el plan incluya odds y estadísticas de las ligas elegidas.
5. Actions → Compilar APK GOLES HOY → Run workflow. Descargar artefacto `GOLES-HOY-APK`; instalar y comparar fecha y contenido con `data/latest.json`.

## Limitaciones reales
- Sofascore y Apostala **NO están integrados**: no se dispone de una API autorizada y verificada de esas fuentes. Noticias locales tampoco están integradas.
- TheSportsDB gratis limita `eventsday` a tres eventos y `eventslast` a uno: no permite analizar toda la cartelera ni calcular probabilidades fiables por sí sola.
- El modo API-FOOTBALL evalúa hasta 12 candidatos por ejecución; no garantiza diez pronósticos ni cobertura exhaustiva.
- El riesgo de expulsión es un filtro estadístico de tarjetas rojas, no predicción individual.
- GitHub Actions puede retrasar tareas programadas; no se garantiza ejecución al minuto.
- Sin desplegar el repositorio ni compilar/instalar la APK, **no se puede afirmar que el producto completo funciona**.

## Ajuste de seguridad de la revisión 2
- TheSportsDB es respaldo y no sustituye pronósticos publicados con una lista vacía. `data/source_health.json` registra el estado del respaldo.
- El flujo ejecuta las pruebas unitarias antes de publicar datos.
- El máximo de partidos a analizar depende del presupuesto de llamadas (`(MAX_API_CALLS-4)//3`), por lo que el plan gratuito NO permite prometer análisis exhaustivo ni 10 pronósticos.
- Sofascore no ofrece API pública para desarrolladores. Apostala y noticias locales requieren fuentes/permiso y formato verificables: NO se simula que están integradas.
- Una clave API-FOOTBALL por sí sola NO garantiza acceso a cuotas. Confirmar cobertura y plan antes de activar predicciones.

## Ajustes de esta entrega
- La interfaz ya NO muestra cuotas, casas ni valor de cuota; se usan solo internamente en el motor cuando se obtienen.
- Un pronóstico de otra fecha NO aparece como pronóstico de hoy; sigue en el historial.
- El workflow Android instala Gradle 8.9 explícitamente.
- Pruebas de regresión verifican ocultación de cuotas y sincronización de interfaz web/Android.
- **No es una APK ya compilada ni un servicio desplegado.** Sin clave autorizada de cuotas y estadísticas suficientes, la aplicación mostrará cero pronósticos verificados.
- No hay integración automatizada de Apostala, Sofascore ni prensa; sus accesos deben verificarse antes de incluirlos.

## Importante para cargar en GitHub desde el navegador
Este ZIP conserva `.github/workflows/android.yml` y `.github/workflows/update.yml`. Sin embargo, GitHub **no importa automáticamente un ZIP** y la carga por arrastrar carpetas puede omitir `.github` porque comienza con un punto. Volver a comprimir el proyecto NO cambia esa limitación del navegador. Para conservar la estructura, subir mediante Git (por ejemplo GitHub Desktop) o crear los dos archivos en la ruta exacta desde el editor web. No subir `workflows/` a la raíz.

Programación corregida: 07:00 y 17:00 Paraguay = 10:00 y 20:00 UTC (GitHub Actions puede retrasarse).
