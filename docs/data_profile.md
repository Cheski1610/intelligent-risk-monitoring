# Perfilamiento inicial de PaySim

## Fuente y cobertura

El archivo local PS_20174392719_1491204439457_log.csv se procesó en modo de solo lectura. Tiene 493,534,783 bytes, 6,362,620 filas y las 11 columnas originales esperadas. No se encontraron celdas vacías, valores numéricos no válidos ni filas duplicadas exactas. El orden de las filas es no decreciente por step.

El archivo contiene steps del 1 al 743, con 743 pasos presentes. La especificación maestra menciona 744; el archivo disponible no contiene el step 744. Step representa una hora simulada y no una fecha calendario.

## Hallazgos

| Indicador | Resultado |
|---|---:|
| Transacciones | 6,362,620 |
| Cuentas de origen únicas | 6,353,307 |
| Cuentas de destino únicas | 2,722,362 |
| Fraudes etiquetados | 8,213 (0.1291%) |
| Registros con isFlaggedFraud=1 | 16 |
| Transacciones por paso | de 2 a 51,352 |
| Importe mínimo / máximo | 0 / 92,445,516.64 |
| Importe promedio | 179,861.90 |
| Importe p50 / p95 / p99 | 73,494.75 / 523,943.58 / 1,657,533.17 |

Los cuantiles son aproximaciones obtenidas de un reservorio uniforme reproducible de 100,000 filas. Los conteos, extremos y promedio se calcularon sobre todas las filas.

| Tipo | Filas | Fraudes etiquetados |
|---|---:|---:|
| PAYMENT | 2,151,495 | 0 |
| TRANSFER | 532,909 | 4,097 |
| CASH_OUT | 2,237,500 | 4,116 |
| DEBIT | 41,432 | 0 |
| CASH_IN | 1,399,284 | 0 |

Las comprobaciones aritméticas simples de saldos difieren en 5,066,425 filas para el saldo de origen y 4,122,111 para el saldo de destino, con tolerancia de 0.01. Estas diferencias se conservaron como hallazgos de diagnóstico; no se corrigieron ni se usan como predictores.

## Muestra de demostración

La muestra local data/samples/paysim_demo.csv contiene 127,707 filas (2.007% del origen) y cubre los 743 pasos. Se seleccionan filas aleatoriamente dentro de cada step, con semilla 20261021 y un mínimo de una fila por paso. La selección no consulta etiquetas y conserva el orden original. La muestra añade _source_row_id, identificador local estable de la fila fuente; no es una columna original de PaySim.

reports/paysim_profile_by_step.csv contiene el total de origen, el tamaño de muestra y un factor de expansión por paso. Las cifras de volumen calculadas sobre la muestra deben ponderarse con ese factor. La muestra y el archivo fuente están excluidos de Git.

## Cortes temporales

Los límites se seleccionaron sin consultar etiquetas, ordenando por step y reservando periodos futuros. Los cortes dejan aproximadamente 70%, 15% y 14% de las filas originales:

| Uso | Steps | Filas del origen |
|---|---:|---:|
| Referencia y ajuste | 1–323 | 4,463,587 |
| Validación de parámetros y umbrales | 324–378 | 980,416 |
| Evaluación final | 379–743 | 918,617 |

El periodo final representa casi la mitad del eje temporal, aunque contiene alrededor del 14.4% de las filas. Esto refleja el perfil temporal irregular del conjunto. El periodo de prueba queda fuera de cualquier ajuste y selección de umbrales.

## Entorno local y Ollama

Python 3.13.13 está disponible. El equipo reporta 31.3 GB de RAM. El contenedor Docker llamado ollama contiene gemma4:12b (7.6 GB en la lista de modelos). El primer arranque del modelo tomó alrededor de 68 segundos según los registros del contenedor; después se observó ejecución parcial en CPU y GPU.

Ollama corre en Docker y publica su API en el host: `http://localhost:11434`. `GET /api/tags` confirmó que el contenedor ofrece `gemma4:12b`, y una generación breve desde el entorno virtual del proyecto confirmó la ruta HTTP `/api/generate`. La aplicación local usa ese endpoint por defecto; Docker CLI permanece disponible como alternativa y el modo determinista mantiene la demo disponible si el modelo no responde.

## Limitaciones

- PaySim es sintético; las métricas no estiman automáticamente el desempeño en sistemas reales.
- isFraud se reserva para evaluación retrospectiva e isFlaggedFraud para analizar la regla histórica.
- Los identificadores de cuenta no son variables continuas generalizables.
- Los saldos se tratan como diagnóstico separado; sus discrepancias pueden reflejar convenciones de la simulación.
- La muestra estratificada sobre-representa pasos con muy pocas filas. Use los factores de expansión para métricas de volumen; para otras métricas describa el diseño de muestreo.
- No se redistribuye el CSV original ni la muestra derivada.
