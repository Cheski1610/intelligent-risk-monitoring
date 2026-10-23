# Metodología de datos y evaluación

Este documento describe los cortes temporales y los cálculos de la implementación actual. Los resultados orientan una revisión educativa; PaySim y sus etiquetas son sintéticos.

## Muestra reproducible

Ejecute `scripts/profile_paysim.py` desde la raíz del proyecto. El proceso valida el esquema y recorre la fuente sin modificarla; escribe la muestra en `data/samples/` y reportes en `reports/`.

La selección aleatoria es independiente dentro de cada `step`, con semilla `20261021` y tasa objetivo del 2%. Se conserva al menos una fila por paso para cubrir todo el intervalo, así que la fracción final puede variar ligeramente. La muestra mantiene el orden original. El reporte `paysim_profile_by_step.csv` contiene los factores de expansión que el monitor usa para aproximar conteos e importes.

## Cortes temporales y uso en la interfaz

Los cortes siguen el tiempo simulado `step`; no son fechas calendario:

| Steps | Uso en la app actual |
|---|---|
| 1–323 | Periodo de referencia para ajustar las transformaciones, GMM, la regla robusta de importe y el umbral de anomalía. |
| 324–378 | Bloque intermedio reservado en el diseño temporal; la interfaz actual no lo usa para ajustar componentes, seleccionar el cuantil ni calcular las métricas que presenta. |
| 379–743 | Periodo fuera de muestra para evaluación retrospectiva con `isFraud`. |

La interfaz selecciona la cantidad de componentes GMM con BIC calculado sobre la referencia. El cuantil de alerta configurable (0.995 por defecto) también se calcula sobre puntajes de referencia. La regla de importe se ajusta por `type`, usando percentil 99 y desviación absoluta mediana (MAD) con multiplicador 6. Los umbrales se establecen sin consultar las etiquetas de evaluación.

El corte intermedio 324–378 no interviene en esta ruta de ejecución, por lo que sus filas no deben describirse como conjunto de validación utilizado por la aplicación. Si una versión futura lo emplea para selección de hiperparámetros, este documento y las métricas deberán actualizarse junto con ese cambio.

## Variables y transformaciones

- Variables operativas iniciales: `step`, `type` y `amount` transformado con `log1p`.
- Estandarización de campos numéricos y codificación one-hot de `type`: se ajustan solo con el periodo de referencia.
- Identificadores `nameOrig` y `nameDest`: se conservan para trazabilidad y agregaciones, no como predictores numéricos.
- Saldos: diagnóstico de consistencia separado; no son predictores operativos.
- `isFraud`: etiqueta sintética consultada únicamente después de puntuar, para evaluación retrospectiva.
- `isFlaggedFraud`: indicador de una regla histórica del dataset; no es una etiqueta independiente de verdad ni un predictor.

## Detección y umbral

GMM modela las observaciones de referencia con covarianza diagonal. La interfaz compara de 1 hasta el máximo de componentes elegido y selecciona el menor BIC. El puntaje es la log-verosimilitud negativa (`-log-likelihood`): valores mayores indican menor ajuste estadístico a la referencia. El cuantil elegido en la pantalla fija el umbral de alerta sobre los puntajes del periodo de referencia.

La regla determinista de importes se estima por tipo transaccional usando cuantiles y MAD. Una alerta puede provenir de GMM, de la regla de importe o de ambas; los códigos de motivo explican esa procedencia. El puntaje de anomalía no es probabilidad de fraude.

## Evaluación retrospectiva

La pantalla compara métodos en steps 379–743. `isFraud` se usa aquí como etiqueta sintética retrospectiva, no como entrada del detector. Se muestran:

- **Precisión:** proporción de alertas que coincide con la etiqueta positiva.
- **Recall:** proporción de etiquetas positivas que recibieron alerta.
- **F1:** media armónica entre precisión y recall.
- **PR-AUC:** calidad de ordenamiento en la curva precisión–recall; resulta informativa ante clases muy desbalanceadas.
- **ROC-AUC:** métrica complementaria de ordenamiento entre positivos y negativos.
- **Precision@K y Recall@K:** desempeño en el 1% superior de puntajes; `K` es el techo de 1% de las filas evaluadas, con mínimo de una fila.

La precisión y el recall de la tabla se calculan con el umbral operativo indicado para cada método. PR-AUC y ROC-AUC usan los puntajes/rangos continuos cuando están disponibles. Para la regla robusta, que solo produce una señal binaria, las métricas de ordenamiento tienen menor granularidad. No se prioriza accuracy porque puede ocultar el comportamiento ante la clase minoritaria.

## Monitor temporal

La granularidad horaria agrupa por `step`. La diaria agrupa 24 steps consecutivos. Frecuencia e importe total se ponderan con factores por paso para aproximar el volumen del archivo original; media, percentil 95, originadores, concentración y tasa de alertas describen las filas seleccionadas de la muestra.

Para el indicador seleccionado, el monitor toma los periodos cuyo `end_step` termina en la referencia (hasta 323), calcula la mediana y una escala robusta `1.4826 × MAD`, y construye límites simétricos `mediana ± multiplicador × escala`. Si la MAD es cero o insuficiente, usa desviación estándar; si también es cero, los límites se sitúan en la mediana. El multiplicador inicial es 3.5. Una alerta requiere un cruce del límite durante el número mínimo de periodos consecutivos configurado.

El factor `1.4826` hace que MAD sea comparable a una desviación estándar bajo una distribución normal. La puntuación de desviación se calcula respecto de la mediana en unidades de escala robusta. La severidad del registro de revisión temporal se deriva de esa puntuación, no de una probabilidad ni de una pérdida esperada.

## Límites de interpretación

- PaySim no representa automáticamente a una institución, población o patrón de fraude real.
- La etiqueta `isFraud` no define una tasa real de fraude.
- La muestra cubre todos los steps, pero percentiles y concentración siguen describiendo la muestra; la ponderación de conteos e importes no convierte todas las estadísticas en estimaciones del universo.
- La evaluación fuera de muestra mide esta partición sintética y no demuestra generalización futura.
- El asistente recupera documentos ficticios y puede generar errores; revise evidencia, citas y contexto antes de registrar conclusiones.
