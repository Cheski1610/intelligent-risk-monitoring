# Intelligent Risk Monitoring Lab

Laboratorio educativo en español para explorar transacciones PaySim, generar señales explicables, observar cambios en indicadores y preparar investigaciones respaldadas por evidencia documental.

> **Límite de uso:** PaySim y sus etiquetas son sintéticos. Una anomalía no es una probabilidad de fraude; una alerta solo prioriza una revisión. Ningún resultado confirma fraude ni sustituye la validación humana.

## Qué incluye

La aplicación tiene una página de inicio y tres herramientas conectadas mediante un contrato común de alertas:

1. **Detector de anomalías:** compara una regla robusta de importes con una mezcla gaussiana (GMM) no supervisada.
2. **Monitor de riesgo:** resume indicadores por hora o día simulado, muestra límites de referencia y permite reproducir la serie temporal.
3. **Asistente de investigación:** busca fragmentos en documentos ficticios y genera un expediente preliminar con Ollama o una plantilla determinista.

Las alertas se guardan localmente para que el asistente pueda recibirlas. Los documentos, procedimientos y citas del asistente son educativos; no son políticas regulatorias ni asesoría legal.

## Requisitos e instalación

- Python 3.11 o superior.
- Windows y PowerShell en los comandos de esta guía. En otros sistemas, active el entorno virtual equivalente y use su intérprete.
- El CSV PaySim se obtiene por separado desde su fuente Kaggle; este proyecto no lo redistribuye.
- Ollama es opcional. Sin él, el asistente genera el expediente determinista.

Descargue `PS_20174392719_1491204439457_log.csv` y colóquelo en la raíz del proyecto. Para usar otra ubicación, configure `IRML_DATA_PATH` como se explica en [Configuración](#configuración).

Desde PowerShell, en la raíz del proyecto:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts/profile_paysim.py
.\.venv\Scripts\python.exe -m streamlit run apps/home.py
```

El perfilador recorre el CSV original sin modificarlo y genera la muestra reproducible, los reportes y los factores de expansión usados por el monitor. La muestra se guarda en `data/samples/paysim_demo.csv`; los reportes, en `reports/`. Si ya existen y quiere regenerarlos, vuelva a ejecutar el perfilador.

La aplicación abre en `http://localhost:8501`. Use la navegación lateral para ir a **Inicio**, **Detector de anomalías**, **Monitor de riesgo** y **Asistente de investigación**. Se recomienda iniciar desde `apps/home.py`, que integra las páginas y el intercambio local de alertas.

También es posible abrir una página por separado:

```powershell
.\.venv\Scripts\python.exe -m streamlit run apps/01_anomaly_detection.py
.\.venv\Scripts\python.exe -m streamlit run apps/02_risk_monitoring.py
.\.venv\Scripts\python.exe -m streamlit run apps/03_ai_audit_assistant.py
```

## Datos y fuente de transacciones

En el detector y el monitor, el selector **Fuente de transacciones** permite elegir:

- **Muestra reproducible:** opción inicial recomendada para demostraciones. Selecciona aproximadamente el 2% dentro de cada `step`, conserva al menos una fila por paso y respeta el orden del archivo. La tasa de selección puede variar ligeramente por redondeo.
- **CSV completo:** procesa el archivo local completo. Puede consumir más memoria y tardar más; úselo cuando necesite analizar todos los registros.

Si la muestra no existe, la app avisa y puede usar el CSV completo. El perfil inicial informa 6,362,620 filas y 743 pasos; vuelva a generar el perfil si utiliza otra versión del archivo.

Todas las páginas que cargan transacciones muestran un estado de calidad. Si encuentra nulos, valores numéricos o etiquetas inválidas, tipos inesperados o duplicados, los informa y conserva las filas: no las elimina silenciosamente. Los valores no interpretables se convierten en faltantes y pueden quedar fuera de un cálculo que los requiera. Revise el detalle antes de interpretar los resultados.

El diccionario campo por campo está en [docs/data_dictionary.md](./docs/data_dictionary.md); el perfil del archivo analizado, en [docs/data_profile.md](./docs/data_profile.md).

## Configuración

Copie `.env.example` a `.env` y ajuste las rutas si hace falta. `.env` es local y no debe subirse al repositorio.

| Variable | Predeterminado | Uso |
|---|---|---|
| `IRML_DATA_PATH` | `PS_20174392719_1491204439457_log.csv` | Ruta del CSV fuente. |
| `IRML_SAMPLE_PATH` | `data/samples/paysim_demo.csv` | Ruta de la muestra reproducible. |
| `IRML_ALERT_STORE_PATH` | `data/processed/alerts.json` | Almacenamiento local compartido por las herramientas. |
| `IRML_SAMPLE_SEED` | `20261021` | Semilla para reproducir selección y ajustes deterministas. |
| `OLLAMA_MODE` | `http` | `http`, `docker` para Docker CLI o `disabled`. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | API Ollama publicada en el host; modo HTTP. |
| `OLLAMA_DOCKER_CONTAINER` | `ollama` | Nombre del contenedor para la alternativa Docker CLI. |
| `OLLAMA_MODEL` | `gemma4:12b` | Etiqueta exacta del modelo Ollama. |
| `OLLAMA_TIMEOUT_SECONDS` | `180` | Tiempo máximo de espera para la generación. |

### Ollama en Docker

La configuración predeterminada supone que Streamlit corre en el equipo local y Ollama en Docker. Publique el puerto del contenedor en el host (por ejemplo, `11434:11434`), asegúrese de que el modelo `gemma4:12b` esté disponible y deje estos valores en `.env`:

```dotenv
OLLAMA_MODE=http
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:12b
OLLAMA_TIMEOUT_SECONDS=180
```

La aplicación no descarga ni carga el modelo al abrirse; solo hace la solicitud cuando se elige **Ollama en Docker** y se presiona **Generar expediente preliminar**. Si la app también corre dentro de un contenedor, `localhost` apunta a ese contenedor; en ese caso configure `OLLAMA_BASE_URL` con el nombre del servicio Ollama en la red de Docker.

## Cómo usar cada herramienta

### Inicio

La portada indica si encontró el CSV y la muestra, cuántas filas tiene el perfil y resume la calidad del dataset: cantidad de pasos, faltantes, filas duplicadas y proporción de la etiqueta sintética `isFraud`. Esa proporción describe PaySim, no la tasa de fraude de una organización real.

### Detector de anomalías

1. Elija **Muestra reproducible** o **CSV completo** en la barra lateral.
2. Defina los parámetros y presione **Ajustar y puntuar**. El ajuste puede tomar tiempo, sobre todo con el CSV completo.
3. Revise el resumen del modelo, la evaluación retrospectiva y las alertas. Use **Inspeccionar una fila señalada** para ver una transacción y sus motivos.
4. Descargue el CSV de alertas o presione **Compartir alertas con el asistente** para guardarlas localmente.

| Elemento | Qué significa |
|---|---|
| **Máximo de componentes GMM** | Cantidad máxima de mezclas que se comparan. El BIC elige entre ellas; un BIC menor equilibra mejor ajuste y complejidad dentro del periodo de referencia. |
| **Cuantil de referencia para alertas** | Percentil de los puntajes del periodo de referencia que fija el umbral. El valor inicial es 0.995; aumentarlo suele reducir señales y bajarlo suele aumentarlas. |
| **Máximo de alertas a mostrar** | Límite de alertas con mayor puntaje que se preparan para la tabla, descarga y transferencia. No modifica el umbral del modelo. |
| **Componentes GMM** | Número de componentes que obtuvo el menor BIC entre los candidatos. |
| **Umbral de anomalía** | Puntaje de baja verosimilitud a partir del cual GMM señala una fila. El puntaje es `-log-verosimilitud`, no una probabilidad de fraude. |
| **Filas inválidas para GMM** | Filas del periodo de referencia que no tenían campos operativos válidos para ajustar el modelo. |
| **BIC por número de componentes** | Comparación de BIC para las mezclas candidatas; se prefiere el menor valor. |

GMM usa `step`, `type` y `log1p(amount)`. Estandarización y codificación categórica se ajustan solo con referencia. El detector compara ese resultado con una regla de importes por tipo basada en percentil 99 y desviación absoluta mediana (MAD). Los identificadores, saldos y etiquetas no son predictores. La regla de importes está fijada en el código y no se ajusta desde la pantalla.

La tabla **Evaluación retrospectiva** compara GMM y la regla robusta usando `isFraud` únicamente en steps 379–743, después del ajuste. Sus columnas se leen así:

| Métrica | Lectura |
|---|---|
| **Filas** | Registros válidos incluidos en la evaluación. |
| **Alertas** | Filas que superan el umbral operativo de cada método. |
| **Precisión** | Proporción de las filas señaladas que tienen etiqueta `isFraud=1` en esta evaluación sintética. |
| **Recall** | Proporción de las filas con etiqueta positiva que el método señaló. |
| **F1** | Equilibrio entre precisión y recall mediante su media armónica. |
| **PR-AUC** | Calidad del ordenamiento según la curva precisión–recall; es especialmente útil con clases muy desbalanceadas. |
| **ROC-AUC** | Capacidad de ordenar positivos por encima de negativos; se muestra como métrica complementaria. |
| **Precision@K / Recall@K** | Precisión y cobertura entre el 1% superior de puntajes (`K = ceil(1% de las filas evaluadas)`). |

La regla robusta genera una señal binaria, por lo que sus métricas de ordenamiento tienen menos granularidad que las de GMM. Una evaluación retrospectiva sobre PaySim no demuestra desempeño futuro ni en datos reales.

Las alertas se ordenan por puntaje y reciben severidad relativa al conjunto priorizado. La severidad ayuda a ordenar la revisión; no representa un nivel calibrado de pérdida ni una decisión de fraude. Los códigos de motivo indican qué regla generó la señal, por ejemplo baja verosimilitud GMM o importe fuera de referencia.

### Monitor de riesgo

1. Seleccione la fuente y elija **Granularidad** e **Indicador**.
2. Ajuste el **Límite robusto (multiplicador)** y los **Periodos consecutivos para alertar**.
3. Reproduzca la serie con **Reiniciar**, **Anterior**, **Reproducir/Pausar**, **Siguiente** o el control **Último periodo reproducido**.
4. Revise la mediana y los límites de referencia. Si hay cambios señalados, descargue sus alertas o compártalas con el asistente. **Descargar indicadores CSV** exporta la serie agregada.

`step` es una hora simulada, no una fecha del calendario. **Por día simulado** agrupa 24 steps consecutivos. El replay presenta el orden histórico; no es streaming.

| Indicador | Qué mide |
|---|---|
| **Frecuencia estimada** | Conteo aproximado ponderado por los factores de expansión de la muestra. |
| **Importe total estimado** | Suma aproximada de importes, también ponderada por expansión. |
| **Importe promedio de la muestra** | Media de los importes seleccionados en el periodo, sin factor de expansión. |
| **Percentil 95 del importe** | Umbral que deja aproximadamente el 95% de importes de la muestra del periodo por debajo. |
| **Originadores distintos observados** | Número de IDs de origen distintos presentes en la muestra del periodo. |
| **Concentración en el destino principal** | Proporción de filas muestreadas que se dirigen al destino más frecuente. |
| **Tasa de alertas** | Proporción de filas muestreadas asociadas a alertas transaccionales compartidas desde el detector. Sin alertas compartidas, será cero. |

La **Mediana de referencia** resume el comportamiento de referencia. Los límites se calculan como mediana ± multiplicador × MAD escalada por 1.4826; si la MAD no permite estimar escala, se usa la desviación estándar. El valor inicial del multiplicador es 3.5. Una alerta requiere el número configurado de periodos consecutivos fuera del intervalo. La **puntuación de desviación** expresa cuántas escalas robustas separan el valor de la mediana; la severidad de una alerta monitorizada se asigna a partir de esa desviación (media, alta o crítica).

El control **Velocidad de reproducción** ofrece cuatro ritmos: cuatro periodos por segundo, dos por segundo, uno por segundo o un periodo cada dos segundos. **Último periodo reproducido** permite saltar directamente en la serie. La línea vertical marca el final de la referencia temporal.

Los conteos e importes estimados usan factores por step. Promedio, percentil 95, originadores, concentración y tasa de alertas describen las filas observadas de la muestra; no son estimaciones ponderadas del universo completo.

En el gráfico, las líneas horizontales discontinuas son los límites inferior y superior; la línea vertical punteada marca el fin del periodo de referencia. El valor de la métrica sobre el gráfico corresponde al último periodo visible del replay.

### Asistente de investigación

1. En el detector o el monitor, seleccione **Compartir alertas con el asistente**. También puede cargar un JSON exportado con una lista de alertas.
2. Seleccione una alerta y revise **Datos recibidos** para confirmar sus valores, puntaje, motivos y referencias.
3. Revise **Consulta documental**. Por defecto combina la categoría y los códigos de motivo de la alerta; puede editarla.
4. Inspeccione los **Fragmentos recuperados** y sus referencias. Luego elija **Plantilla determinista** o **Ollama en Docker** y presione **Generar expediente preliminar**.
5. Revise el borrador, compruebe sus fuentes y descargue el expediente Markdown.

La recuperación local usa TF-IDF y similitud léxica sobre documentos Markdown ficticios. Presenta como máximo cinco fragmentos con coincidencia positiva. **Relevancia** es similitud textual, no confianza factual; si no hay coincidencias, la pantalla lo indica. La opción de subir JSON sirve para esa sesión de la página y debe contener una lista válida de alertas.

Al expandir **Datos recibidos**, los campos principales se interpretan así:

| Campo | Significado |
|---|---|
| `alert_id` | Identificador único del registro de alerta. |
| `source_tool` | Herramienta que generó la señal: detector o monitor. |
| `event_step` | Step simulado relacionado con la alerta, cuando aplica. |
| `transaction_id` | ID local de fila para trazabilidad; no es una identidad comercial ni el ID de cuenta PaySim. Las alertas agregadas del monitor pueden no tenerlo. |
| `risk_category` | Categoría descriptiva de la señal. |
| `score_type` y `score_value` | Nombre y valor del puntaje. Un `anomaly_score` no es probabilidad de fraude; `review_priority` expresa prioridad de revisión. |
| `severity` | Prioridad relativa (`low`, `medium`, `high` o `critical`), no una conclusión. |
| `reason_codes` | Reglas o motivos técnicos que contribuyeron a crear la señal. |
| `observed_values` | Valores observados que ayudan a contextualizar la alerta. |
| `reference_values` | Umbral o resumen de referencia usado para compararla. |
| `evidence_refs` | Referencias de evidencia que ya acompañan la alerta, si las hay. |
| `status` y `created_at` | Estado inicial de revisión y fecha de creación del registro. |

El expediente determinista o generado contiene diez apartados: resumen de la alerta, datos observados, motivo de generación, criterios documentales, hipótesis, procedimientos, evidencia adicional requerida, limitaciones y explicaciones alternativas, referencias y validación humana. El modelo puede equivocarse; revise cada afirmación y cita. La pantalla avisa si el texto generado menciona referencias que no estaban entre los fragmentos recuperados.

Si Ollama falla o vence el tiempo de espera, la aplicación conserva la plantilla determinista. Elegir **Plantilla determinista** no llama a ningún modelo. La generación se solicita solo al presionar el botón.

## Alertas y exportaciones

El detector y el monitor escriben alertas en `IRML_ALERT_STORE_PATH`, normalmente `data/processed/alerts.json`, cuando se pulsa **Compartir alertas con el asistente**. La operación agrega o actualiza registros por `alert_id`; no envía la información a un servicio externo. Las alertas del detector incluyen una fila de transacción, mientras que las de cambios agregados del monitor describen un periodo e indicador.

Los CSV permiten revisar los registros fuera de la interfaz. El expediente se descarga en Markdown. Las exportaciones y el almacenamiento local pueden contener datos del CSV elegido; compártalos solo conforme a las reglas de su entorno.

## Metodología y términos

La muestra se selecciona reproduciblemente por `step`, conserva el orden y no usa etiquetas para el muestreo. El detector ajusta codificadores, escaladores, GMM, regla robusta y umbral de anomalía con steps 1–323. GMM compara componentes con BIC en ese periodo; el cuantil elegido en la pantalla también se calcula ahí. Steps 324–378 no participan en el ajuste ni en las métricas presentadas por la interfaz actual. Steps 379–743 se usan para la evaluación retrospectiva con etiquetas.

| Término | Significado en esta app |
|---|---|
| **Anomalía** | Observación con baja verosimilitud o fuera de una regla robusta; no implica causa ni fraude. |
| **Alerta** | Registro que prioriza una revisión humana. |
| **Severidad** | Orden relativo de revisión dentro de las señales generadas; no es probabilidad ni monto de pérdida. |
| **`step`** | Índice de hora simulada de PaySim. |
| **`isFraud`** | Etiqueta sintética usada después del puntaje para evaluación retrospectiva; nunca es predictor operativo. |
| **`isFlaggedFraud`** | Indicador histórico del dataset; sirve para analizar esa regla, no como etiqueta independiente de verdad. |
| **MAD** | Mediana de las desviaciones absolutas respecto de la mediana; medida robusta de dispersión. |
| **Factor de expansión** | Peso por step para aproximar conteos e importes del archivo completo a partir de la muestra. |

Los identificadores se conservan para trazabilidad y no se tratan como magnitudes numéricas. Los saldos posteriores se reservan para diagnósticos separados. Consulte [docs/methodology.md](./docs/methodology.md), [docs/data_dictionary.md](./docs/data_dictionary.md), [docs/data_profile.md](./docs/data_profile.md), [docs/architecture.md](./docs/architecture.md) y [docs/limitations.md](./docs/limitations.md) para más detalle técnico y de uso responsable.

## Solución de problemas

- **No aparece la muestra:** compruebe que el CSV original está en la ruta configurada y ejecute `.\.venv\Scripts\python.exe scripts/profile_paysim.py` desde la raíz.
- **No se encuentra PaySim:** revise `IRML_DATA_PATH`; la muestra y el CSV completo son rutas configurables distintas.
- **El monitor estima conteos iguales a la muestra:** compruebe que exista `reports/paysim_profile_by_step.csv`; sin pesos, la agregación usa peso 1.
- **No hay alertas en el asistente:** comparta alertas desde el detector o el monitor, o cargue una lista JSON válida.
- **No se recuperan documentos:** pruebe términos presentes en los documentos educativos o revise `data/synthetic_documents/`.
- **Ollama no responde:** compruebe que el contenedor esté activo, que publique el puerto 11434 en el host y que `gemma4:12b` esté disponible; confirme `OLLAMA_BASE_URL` y el tiempo de espera.
- **Resultados tardan o consumen mucha memoria:** comience con la muestra reproducible. El ajuste GMM limita a 250,000 filas la submuestra de referencia cuando esta es mayor, pero puntuar el CSV completo sigue siendo más costoso.

## Pruebas

Desde el entorno virtual del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Las pruebas usan datos sintéticos pequeños y no requieren descargar PaySim completo ni tener Ollama activo.

## Licencias y atribución

PaySim se obtiene por separado desde su fuente Kaggle y no se redistribuye desde este repositorio. Revise las condiciones de uso aplicables antes de compartir código o datos. Las dependencias mantienen sus propias licencias.
