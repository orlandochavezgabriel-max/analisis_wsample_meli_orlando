MELI Operations & Workforce Capacity Model 
Este repositorio contiene la solución analítica para el dimensionamiento de personal, control de capacidad y gestión de brechas (gaps) en los subprocesos logísticos (Inbound, Outbound y Sorting) bajo escenarios de operación normal y sobreventa.

Descripción del Proyecto
El proyecto automatiza el procesamiento y cruce de datos logísticos mediante scripts en Python y modelos relacionales, permitiendo auditar hora por hora la suficiencia de la plantilla fija (mediana de planta) frente a los picos de demanda real. Su objetivo principal es fundamentar la toma de decisiones operativas y presupuestales para la contratación de personal temporal (diaristas), protegiendo los niveles de servicio (SLA) sin incurrir en sobredimensionamientos de nómina estructural.

Estructura del Repositorio
datasets_analisis.xlsx – Archivo maestro de consolidación que integra las métricas por hora de volumen de paquetes, pallets, demanda de headcount (HC), oferta fija y brechas de diaristas.

Scripts de Procesamiento – Bloques lógicos en Python diseñados para la limpieza, estructuración y cálculo de productividades efectivas ponderadas.

Dashboard de Power BI – Modelos visuales que contrastan la Demanda Base, la Demanda con Sobreventa y la Oferta Fija para la identificación rápida de cuellos de botella operativos.

Funcionalidades Clave
Dimensionamiento por Suficiencia: Uso de criterios estadísticos robustos (mediana) para definir la oferta fija de planta por turno, evitando distorsiones por la media aritmética.

Análisis de Brechas (Gaps): Detección automatizada de las franjas horarias críticas donde la demanda supera la capacidad instalada, separando el requerimiento de personal temporal.

Optimización y Gestión de Desvíos: Enfoque gerencial para priorizar alternativas internas (traslape de turnos, priorización de flujos Small vs. Heavy) antes de recurrir a la contratación externa de diaristas.

Requisitos Técnicos y Dependencias
Python 3.x

Librerías principales: pandas, numpy, openpyxl

Entorno de visualización: Power BI / Microsoft Excel
