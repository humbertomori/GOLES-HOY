# GOLES HOY + EMPATES HOY — reconstrucción funcional

## Ejecutar
`pip install -r requirements.txt && python app.py`; abrir `http://localhost:8080`.
Servidor persistente necesario para ejecución desatendida a las 07:00 America/Asuncion. **No funciona si el servidor duerme**, se reinicia a esa hora, o el hosting no permite procesos persistentes. Desplegar una sola réplica (SQLite + scheduler) con disco persistente; en múltiples réplicas mover el scheduler a un cron externo y usar base de datos compartida.

## Automatización real y fuente Apostala
Configurar `APOSTALA_FEED_URL` apuntando a una integración **autorizada y verificable** que devuelva JSON de encuentros confirmados en la cartelera oficial de Apostala. Opcional `APOSTALA_FEED_TOKEN`. **Este paquete no contiene ni afirma tener una API oficial de Apostala**; sin integración, a las 07:00 se ejecuta pero reporta `NO_FEED` y NO inventa partidos. No usar scraping que eluda autenticación, restricciones ni términos de servicio. La disponibilidad y cuotas cambian: volver a confirmar antes de apostar.

JSON: array o `{"fixtures":[...]}`. Cada objeto debe tener:
`id,day,home,away,league,country,kickoff,source,apostala_confirmed,odd_o25,odd_btts,odd_draw,home_scored,home_conceded,away_scored,away_conceded,n_home,n_away,red_risk`.
`day` en YYYY-MM-DD Paraguay, `apostala_confirmed` boolean true, `source` referencia verificable Apostala, `kickoff` hora Paraguay; medias de goles local/visitante con al menos cinco partidos en cada muestra; `red_risk` de 0 a 1 (si no hay datos, 0 no significa ausencia de riesgo: marcar falta de información en fuente). Cuotas decimales >1. Los mercados ausentes pueden ser null. Fuente y fecha de verificación se guardan.

## Carga alternativa
POST `/api/import` con el mismo JSON o CSV con cabecera `Content-Type: text/csv` y las mismas columnas; no acepta partidos sin `apostala_confirmed=true`. Ejemplo con archivo `cartelera.json`:
`curl -X POST http://localhost:8080/api/import -H 'Content-Type: application/json' --data-binary @cartelera.json`

POST `/api/refresh` ejecuta el feed y reconstruye selección; GET `/api/status`; GET `/api/picks`; POST `/api/result` JSON `{"fixture_id":"ID","home":2,"away":1}` para registrar marcador. Proteger rutas POST con autenticación en un despliegue público: el prototipo no tiene panel de administración ni control de acceso.

## Método
Poisson independiente: λ local = 1.07*(goles local a favor + goles visitante recibidos)/2; λ visitante = .94*(goles visitante a favor + goles local recibidos)/2. P(+2.5), P(ambos), P(empate) derivadas; penalización conservadora por muestra y riesgo de roja; edge = probabilidad modelo - 1/cuota. GOLES: máximo 10, probabilidad >=62% y edge >=1.5 puntos; EMPATES máximo 5 y edge >=1.5 puntos. Máximo dos por liga y cuatro por país, un mercado por encuentro dentro de cada ranking. No se completan cupos. No se afirma que estos coeficientes estén calibrados ni que reproduzcan el supuesto 90% anterior; hace falta historial auditado y backtesting fuera de muestra. No se dispone de xG, bajas o alineaciones en el feed base; para producción deben incorporarse como fuentes verificadas y recalibrarse.

## Limitaciones explícitas
No publica en los dos dominios antiguos ni crea nuevos dominios por sí solo. Requiere hosting activo, configuración de feed autorizado y despliegue. SQLite almacena el historial en disco persistente. Los resultados se ingresan por `/api/result`; integrar un proveedor de resultados con identificadores fiables para cierre automático. Las selecciones quedan congeladas al crearse; una actualización no sobrescribe cuotas ni probabilidades históricas. No garantiza ganancias ni tasa de aciertos.

## Interfaz móvil unificada (23/09/2026)
Una sola pantalla con pestañas GOLES HOY / EMPATES HOY, estado de fuente, historial y botón de actualización. Manifest PWA para añadir a pantalla de inicio desde Chrome en Android una vez desplegada con HTTPS. **No es APK**, no funciona offline, y no habilita el feed por sí sola. Los dos enlaces públicos antiguos permanecen sin modificar.
