# PrecioLLM

## Resumen de la plataforma

**PrecioLLM** es la plataforma de análisis económico y gestión de mercados de nivel empresarial de AgroLLM, diseñada para revolucionar la forma en que las cooperativas, organizaciones de productores (OPFH) y asesores técnicos gestionan la viabilidad comercial y los costes de las explotaciones agrícolas. Desde pequeñas parcelas de medianías hasta grandes consorcios de exportación, PrecioLLM proporciona herramientas integradas de análisis de precios, control de costes de producción y gestión del margen de beneficio neto en múltiples líneas de cultivo (incluyendo plátano, aguacate, papa y pimiento). Mediante el uso de arquitecturas de Inteligencia Artificial (RAG Multimodal con Llama 3.2 y ChromaDB), PrecioLLM procesa boletines oficiales y hojas de cálculo complejas para permitir a los agentes del sector evaluar costes reales, predecir márgenes y optimizar la comercialización de manera competitiva.

## Características principales

### 1. Motor de ingesta multimodal de boletines de precios

Una avanzada plataforma de extracción documental capaz de procesar, mediante IA visual y segmentación semántica, los boletines de precios semanales emitidos en formato PDF o imagen por los mercados mayoristas de destino de las islas (**Mercatenerife y Mercalaspalmas**), transformando tablas complejas en información estructurada y libre de alucinaciones.

### 2. Integración de inteligencia de mercados (origen vs. destino)

La plataforma recopila de forma automatizada los datos públicos del **Observatorio de Precios del Gobierno de Canarias** y de los registros del Ministerio (MAPA). Cruza instantáneamente los precios pagados en campo (origen) con los de venta al consumidor final (destino), identificando asimetrías y márgenes de intermediación de la cadena alimentaria.

### 3. Módulo de análisis de costes de insumos (fertilizantes y energía)

Capacidades especializadas para el seguimiento de los costes de producción variables. Permite indexar facturas e informes de precios de abonos, fitosanitarios, semillas y costes energéticos de extracción de agua de pozos o galerías, calculando el impacto de la inflación de los insumos en el coste final por kilo cosechado.

### 4. Optimizador de costes del cultivo de la papa

Herramientas integradas que analizan de forma específica los costes asociados a la papa en medianías (semilla certificada, preparación de tierras, horas de tractor, mano de obra y tratamientos fitosanitarios obligatorios contra la polilla guatemalteca), detectando el umbral de rentabilidad mínimo por hectárea según la campaña (invierno o primavera).

### 5. Evaluación de explotaciones de cultivo subtropical (aguacate y plátano)

Modelos avanzados de amortización de costes fijos específicos para cultivos plurianuales de alto valor. Incorpora el análisis de costes de implantación (estructuras de cortavientos, sistemas de riego por goteo, desbroces en terrenos volcánicos) y mantenimiento, cruzándolos con la previsión de precios por categoría del fruto.

### 6. Especialización en estructuras de invernadero (pimiento y tomate)

Cálculo pormenorizado de los costes de infraestructura y control ambiental bajo plástico en zonas costeras. Evalúa costes de reposición de mallas, plásticos, fertirrigación mecanizada y mano de obra necesaria para el entutorado y recolección, adaptados a la normativa laboral y convenios del sector agrario español.

### 7. Cuadro de mando de gestión del margen comercial (cooperativas)

Métricas avanzadas a nivel de agregador para que las cooperativas evalúen el rendimiento económico del conjunto de sus socios: tasas de liquidación, volúmenes comercializados por categorías de calidad, mermas logísticas y concentraciones de oferta por zonas geográficas o municipios.

### 8. Portal para asesores técnicos y oficinas de extensión agraria

Un acceso dedicado para que los ingenieros agrónomos simulen planes de viabilidad económica antes de realizar una nueva plantación. Permite emitir informes de rentabilidad automáticos con citación y trazabilidad absoluta a las fuentes oficiales de costes de la comunidad autónoma.

### 9. Integración con el módulo de subvenciones (PoseiLLM / PAC)

Conexión directa con el asistente normativo para deducir automáticamente las ayudas directas a la superficie o a la comercialización (por ejemplo, ayuda por hectárea de aguacate o plátano del POSEI) en el cálculo del beneficio neto total del agricultor, ofreciendo una foto real de la rentabilidad del negocio.

## Precios y planes de licenciamiento

La estructura de precios de PrecioLLM refleja la escala y la complejidad de las operaciones agrícolas en el mercado español:

- **Plan Cooperativa Local:** 6.000 €/mes para cooperativas agrícolas regionales u Oficinas de Extensión Agraria de ámbito insular que requieran el procesamiento de boletines básicos, gestión de costes para hasta 200 socios y acceso a la interfaz web estándar.
- **Plan Federación Agraria:** 12.000 €/mes para grandes organizaciones de productores (OPFH), cooperativas de segundo grado o federaciones de exportadores multi-isla. Añade el procesador multimodal avanzado de imágenes/tablas, API de integración con sistemas ERP de almacén y analítica predictiva.
- **Plan Gran Distribución / Corporativo:** precio personalizado bajo cotización para cadenas de supermercados, grandes comercializadoras mayoristas o instituciones públicas que requieran despliegues locales dedicados (servidores con GPUs para hardware local bajo Ollama), personalizaciones completas con marca blanca y acceso API masivo.

*Todos los planes incluyen los servicios iniciales de despliegue, la indexación de los históricos de precios de la cooperativa y jornadas de capacitación técnica en campo.*

## Hoja de ruta de desarrollo (roadmap)

La planificación del desarrollo técnico de PrecioLLM incluye los siguientes hitos de ingeniería:

- **Q2 2025:** lanzamiento de PrecioLLM v1.0 con el motor RAG core para consulta de boletines de precios semanales e ingesta manual de fichas de costes.
- **Q4 2025:** incorporación del modelo de visión multimodal (Llama 3.2 Vision) para la extracción automatizada de tablas de precios manuscritas o escaneadas desde tablones de anuncios de cooperativas.
- **Q2 2026:** integración embebida con datos climáticos en tiempo real para correlacionar picos de precios con olas de calor, calimas o heladas en las islas.
- **Q4 2026:** lanzamiento del módulo de seguros agrarios paramétricos en colaboración con Agroseguro, evaluando la pérdida de rendimiento económico por inclemencias meteorológicas.
- **Q2 2027:** introducción de herramientas avanzadas de modelización del riesgo de transición climática (impacto a largo plazo del aumento del precio del agua desalada en la rentabilidad de las medianías).
- **Q4 2027:** expansión del producto al mercado peninsular español e internacionalización del software hacia regiones ultraperiféricas de la Unión Europea con regímenes POSEI similares (por ejemplo, Madeira y Azores).

> PrecioLLM dota a los técnicos y gestores del sector primario de la capacidad de defender el valor real del producto en el mercado, garantizando que el agricultor reciba un precio justo basado en datos verídicos, transparentes y libres de especulación. ¡Optimiza la rentabilidad del campo canario con PrecioLLM!
