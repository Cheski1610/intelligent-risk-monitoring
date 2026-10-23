# Diccionario de datos

El archivo PaySim contiene las columnas originales siguientes. Se mantienen sus nombres para facilitar la comparación con la fuente.

| Columna | Tipo esperado | Significado | Disponibilidad analítica |
|---|---|---|---|
| step | Entero | Hora dentro de la simulación | Disponible al iniciar la transacción; no es fecha real |
| type | Categoría | Tipo de transacción: CASH_IN, CASH_OUT, DEBIT, PAYMENT o TRANSFER | Disponible al iniciar |
| amount | Número | Importe de la transacción | Disponible al iniciar |
| nameOrig | Texto | Identificador sintético de la cuenta de origen | Identificador; no usar como predictor numérico |
| oldbalanceOrg | Número | Saldo anterior del originador | Diagnóstico separado, sujeto a disponibilidad |
| newbalanceOrig | Número | Saldo posterior del originador | Información posterior; excluir de predictores operativos |
| nameDest | Texto | Identificador sintético del destino | Identificador; no usar como predictor numérico |
| oldbalanceDest | Número | Saldo anterior del destino | Diagnóstico separado, sujeto a disponibilidad |
| newbalanceDest | Número | Saldo posterior del destino | Información posterior; excluir de predictores operativos |
| isFraud | Binario | Etiqueta sintética para evaluación retrospectiva | Nunca predictor |
| isFlaggedFraud | Binario | Indicador de una regla histórica incluida en el dataset | Solo para analizar esa regla; nunca predictor |

Los predictores operativos iniciales se limitan a step, type, amount transformado y derivaciones temporales justificadas. Saldos, etiquetas e identificadores quedan fuera de ese conjunto. Una anomalía representa una desviación estadística; una alerta prioriza revisión; ninguna equivale por sí sola a fraude confirmado.
