# Arquitectura

El proyecto separa las aplicaciones Streamlit de los módulos de datos, análisis y configuración. El paquete instalable se encuentra en src/irml.

```text
apps/                         Interfaces Streamlit en español
src/irml/common/              Configuración, contrato de alertas, exportación y almacenamiento local
src/irml/data/                 Carga por bloques, tipado, calidad y perfilamiento
src/irml/anomaly_detection/    Reglas robustas, GMM, puntajes y evaluación
src/irml/risk_monitoring/      Agregación temporal, umbrales y alertas de cambio
src/irml/audit_assistant/      Documentos sintéticos, recuperación, proveedor y expediente
data/synthetic_documents/      Fuentes educativas versionadas
```

Las herramientas comparten el modelo Pydantic Alert. Un archivo local de alertas permite que el asistente consuma señales generadas por las otras aplicaciones. El almacenamiento es explícito y queda excluido de Git.

PaySim se carga desde un CSV local o desde una muestra determinista. La muestra mantiene un ID local de fila, el orden de origen y factores de expansión por step. El replay es una reproducción simulada; no es streaming ni usa una fecha real.

El asistente recupera Markdown con TF-IDF local y conserva referencias por documento, versión y sección. Ollama puede usarse por HTTP o mediante Docker CLI; el modo determinista no requiere proveedor.
