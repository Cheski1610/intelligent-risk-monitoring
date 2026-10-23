# Guion de demostración

## Detector de anomalías (8 minutos)

1. Explicar que PaySim es sintético y que step es una hora simulada.
2. Abrir la muestra y revisar su cobertura y calidad.
3. Ejecutar reglas robustas y GMM, explicando que el ajuste usa solo steps de referencia.
4. Seleccionar una alerta, leer sus valores y códigos de motivo.
5. Mostrar métricas retrospectivas con isFraud y discutir falsos positivos y falsos negativos.
6. Aclarar que el puntaje no es probabilidad de fraude.

## Monitor de riesgo (8 minutos)

1. Elegir indicadores por hora o día simulado.
2. Explicar los factores de expansión de la muestra.
3. Mostrar mediana y límites robustos ajustados con referencia.
4. Revisar una desviación persistente y sus periodos observados.
5. Exportar indicadores o compartir alertas con el asistente.

## Asistente de investigación (8 minutos)

1. Seleccionar una alerta compartida por las otras herramientas.
2. Mostrar fragmentos recuperados y sus referencias.
3. Revisar hipótesis, procedimientos y evidencia pendiente.
4. Generar el borrador con Ollama o usar la plantilla determinista.
5. Validar que una persona revise los datos, fuentes y limitaciones.

Si Ollama no está disponible, continúe con el expediente determinista. No se necesita descargar un modelo al iniciar la aplicación.
