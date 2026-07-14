# AguaLLM

## Resumen de la plataforma

AguaLLM es la plataforma de gestión hídrica y optimización del riego de precisión de nivel empresarial de AgroLLM, diseñada específicamente para dar respuesta a uno de los desafíos más críticos del sector primario en regiones con recursos limitados y suelos de origen volcánico: la escasez, el coste y la calidad del agua de riego. Desde pequeños cultivos de medianías hasta grandes comunidades de regantes y heredamientos tradicionales, AguaLLM proporciona herramientas avanzadas para el cálculo exacto de la necesidad hídrica, el control de la salinidad y la gestión eficiente de las infraestructuras de distribución. Mediante una arquitectura de Inteligencia   avanzada (RAG Multimodal local con Llama 3.2 y ChromaDB), AguaLLM procesa históricos de consumo, analíticas químicas complejos y guías técnicas para ofrecer recomendaciones de riego automatizadas, trazables y libres de alucinaciones.

## Características principales

### 1. Calculadora inteligente de evapotranspiración (ETc)

Un motor RAG especializado que extrae las fórmulas y coeficientes de cultivo ($K_c$) de los manuales oficiales de la FAO y los cruza semánticamente con las lecturas climáticas diarias de las redes agrometeorológicas locales. Permite calcular con exactitud milimétrica cuántos litros de agua necesita cada parcela según el microclima del día.

### 2. Intérprete multimodal de analíticas de agua y salinidad

Capacidad basada en visión por computadora (Llama 3.2 Vision) para que el técnico o agricultor suba una fotografía o PDF de un análisis químico de laboratorio de su pozo, galería o planta desaladora. La IA extrae las tablas de conductividad eléctrica (CE), niveles de sodio, cloruros y boro, emitiendo alertas inmediatas si el agua supera los umbrales de tolerancia de cultivos sensibles como el aguacate.

### 3. Módulo de gestión de suelos volcánicos y "picón"

Un sistema de recomendación adaptado a las propiedades de los andosoles y suelos de origen volcánico. El asistente indexa guías de manejo de suelos del ICIA y centros de investigación para asesorar sobre la frecuencia de riego óptima y el uso de cubiertas de lapilli (picón) para minimizar la evaporación y maximizar la retención de humedad en las raíces.

### 4. Asistente burocrático para comunidades de regantes

Estructura RAG especializada en la normativa de aguas, estatutos de heredamientos y reglamentos de las comunidades de usuarios. Resuelve consultas recurrentes sobre turnos de agua ("dulas"), derechos de aprovechamiento, solicitudes de contadores y normativas de seguridad en balsas y estanques agrícolas.

### 5. Optimización de redes de riego por goteo y aspersión

Manuales técnicos y esquemas de ingeniería hidráulica integrados en ChromaDB para el mantenimiento de los sistemas de fertirrigación. Ayuda a diagnosticar problemas de caída de presión, cálculo de caudales por emisor, pautas para la limpieza de filtros y dosificación de ácidos para evitar la obstrucción por cal o algas.

### 6. Historial de consumos y auditoría hídrica cooperativa

Cuadros de mando y analítica de datos para que los administradores de las cooperativas o comunidades monitoricen los volúmenes de agua distribuidos, detecten fugas ocultas mediante anomalías en los patrones de consumo y emitan informes de eficiencia hídrica exigidos por las auditorías medioambientales y sellos de calidad.

### 7. Integración con el cuaderno de campo digital (SIEX)

Conexión directa con la normativa del cuaderno de explotación digital en España. AguaLLM registra automáticamente los volúmenes de agua aportados y las fechas de riego por parcela, asegurando que la explotación cumpla estrictamente con las inspecciones de la condicionalidad reforzada de la PAC.

### 8. Portal de alertas por estrés hídrico y calima

Módulo que cruza las predicciones meteorológicas de intrusión de polvo sahariano (calima) u olas de calor con la base de datos de cultivos. Envía recomendaciones automáticas de riego preventivo para evitar la caída del fruto o el estrés irreversible en plantaciones sensibles.

### 9. Simulador de eficiencia energética en bombeos

Herramienta analítica que evalúa los costes eléctricos asociados al bombeo de agua desde pozos profundos o redes presurizadas. Sugiere los horarios de riego más económicos basándose en las tarifas eléctricas indexadas del mercado español y la disponibilidad de almacenamiento en estanques propios.

## Precios y planes de licenciamiento

La estructura de precios de AguaLLM se adapta a la escala de las infraestructuras hídricas y agrícolas:

- **Plan Heredamiento / Comunidad Local:** 6.000 €/mes para comunidades de regantes tradicionales u oficinas técnicas de gestión de agua locales. Incluye soporte para la gestión de turnos de riego de hasta 150 comuneros, ingesta de analíticas químicas básicas y acceso web estándar con citación automática.
- **Plan Consorcio Hídrico / Red Insular:** 12.000 €/mes para grandes comunidades de usuarios, empresas públicas de gestión de agua o cooperativas de segundo grado. Añade el procesador multimodal de analíticas por visión artificial, API para la integración con sensores de humedad de suelo (IoT) y analítica predictiva de demanda hídrica.
- **Plan Corporación / Desaladoras:** precio personalizado bajo cotización para grandes operadoras de agua industrial desolada, consejos insulares de aguas o corporaciones que requieran un despliegue dedicado en servidores propios (hardware local con GPUs dedicadas para Ollama), soporte de marca blanca y acceso API masivo.

## Hoja de ruta de desarrollo (roadmap)

La hoja de ruta tecnológica de AguaLLM contempla los siguientes hitos de ingeniería de software e inteligencia artificial:

- **Q2 2025:** lanzamiento de AguaLLM versión 1.0 con el motor RAG core para consultas regulatorias de agua y cálculo manual de necesidades hídricas basándose en la metodología FAO.
- **Q4 2025:** incorporación de Llama 3.2 Vision para la lectura automatizada de analíticas de agua en papel y diagramas de redes de riego por goteo escaneados.
- **Q2 2026:** integración nativa mediante herramientas de LangChain con sensores IoT de humedad del suelo (sondas capacitivas) para contrastar las recomendaciones de la IA con datos reales del terreno.
- **Q4 2026:** lanzamiento del módulo de alertas tempranas frente a olas de calor y calima, calculando el incremento de riego preventivo necesario para evitar el estrés hídrico y la caída del fruto en subtrópicos.
- **Q2 2027:** introducción de herramientas avanzadas de simulación económica del agua, calculando el impacto de la subida del coste energético de la desalinización en el margen de beneficio por hectárea del cultivo.
- **Q4 2027:** adaptación y expansión de la plataforma a cuencas hidrográficas de la península ibérica con problemas severos de sequía (por ejemplo, cuencas del Segura, Júcar o Guadalquivir).

> AguaLLM transforma la gestión del agua de un desafío diario de supervivencia a una ciencia exacta, asegurando que cada gota se aproveche al máximo mediante respuestas verídicas, trazables y adaptadas a la realidad del suelo de las islas. ¡Maximiza la eficiencia de tu riego con AguaLLM!
