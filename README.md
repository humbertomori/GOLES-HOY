# GOLES HOY — versión sin API pagada

Motor automático para +2.5 y Ambos Marcan.

- No usa TheSportsDB.
- No usa SportMonks.
- No requiere API key, token ni suscripción.
- Usa OpenFootball (datos públicos CC0) como base de fixtures/resultados históricos.
- Calcula estimaciones con hasta 8 partidos recientes por equipo, mezcla tasa empírica + Poisson y penaliza muestra incompleta.
- No inventa cuotas: si no existe una fuente pública verificable de cuotas, la app no muestra una cuota.
- No completa artificialmente un Top 10: solo publica candidatos >=62% calculados con muestra suficiente.
- Diagnóstico: recibidos, analizados, seleccionados y errores de fuente.
- Zona: America/Asuncion.

Limitación conocida: OpenFootball no garantiza cobertura diaria completa de todas las ligas del mundo. Si no hay partidos en las ligas cubiertas, la interfaz debe informar cobertura insuficiente y no afirmar “no hay fútbol”.
