# PrecioLLM

## Resumen de la plataforma

PrecioLLM es la plataforma de análisis económico y gestión de mercados de nivel empresarial de AgroLLM, diseñada para revolucionar la forma en que las cooperativas, organizaciones de productores (OPFH) y asesores técnicos gestionan la viabilidad comercial y los costes de las explotaciones agrícolas. Desde pequeñas parcelas de medianías hasta grandes consorcios de exportación, PrecioLLM proporciona herramientas integradas de análisis de precios, control de costes de producción y gestión del margen de beneficio neto en múltiples líneas de cultivo (incluyendo plátano, aguacate, papa y pimiento). Mediante el uso de arquitecturas de Inteligencia Artificial de vanguardia (RAG Multimodal local con Llama 3.2 y ChromaDB), PrecioLLM procesa boletines oficiales, documentos PDF y hojas de cálculo complejas para permitir a los agentes del sector evaluar costes reales, predecir márgenes de manera competitiva y defender el valor del producto local frente a la cadena de distribución.

## Características principales

### 1. Motor de ingesta multimodal de boletines de precios

Una avanzada plataforma de extracción documental capaz de procesar, mediante IA visual y segmentación semántica, los boletines de precios semanales emitidos en formato PDF o imagen por los mercados mayoristas de destino del archipiélago (**Mercatenerife y Mercalaspalmas**). El sistema transforma tablas densas de doble entrada en información estructurada en Markdown, libre de alucinaciones y lista para ser consultada.

### 2. Integración de inteligencia de mercados (origen vs. destino)

La plataforma recopila y analiza de forma automatizada los datos públicos del **Observatorio de Precios del Gobierno de Canarias** y de los registros del Ministerio (MAPA). Cruza instantáneamente los precios pagados en campo (origen) con los de venta al consumidor final (destino), identificando asimetrías en la cadena alimentaria y aportando transparencia en los márgenes de intermediación.

### 3. Módulo de análisis de costes de insumos (fertilizantes y energía)

Capacidades especializadas para el seguimiento de los costes de producción variables. Permite indexar de forma masiva facturas e informes de precios de abonos, fitosanitarios, semillas y costes energéticos asociados a la extracción de agua de pozos o galerías, calculando automáticamente el impacto de la inflación de los insumos en el coste final por kilo cosechado.

### 4. Optimizador de costes del cultivo de la papa

Herramientas integradas que analizan de forma específica los costes asociados a la papa en zonas de medianías (semilla certificada, preparación de tierras, horas de tractor, mano de obra y tratamientos fitosanitarios obligatorios contra la polilla guatemalteca). Detecta el umbral de rentabilidad mínimo por hectárea según la campaña (invierno, primavera o secano).

### 5. Evaluación de explotaciones de cultivo subtropical (aguacate y plátano)

Modelos avanzados de amortización de costes fijos específicos para cultivos plurianuales de alto valor en Canarias. Incorpora el análisis de costes de implantación (estructuras de cortavientos, sistemas de riego por goteo, desbroces en terrenos volcánicos) y mantenimiento, cruzándolos con la previsión de precios históricos por categoría del fruto.

### 6. Especialización en estructuras de invernadero (pimiento y tomate)

Cálculo pormenorizado de los costes de infraestructura y control ambiental bajo plástico en zonas costeras. Evalúa los costes de reposición de mallas, plásticos, fertirrigación mecanizada y mano de obra necesaria para el entutorado y recolección, adaptados a la normativa laboral y convenios del sector agrario español.

### 7. Cuadro de mando de gestión del margen comercial (cooperativas)

Métricas avanzadas a nivel de agregador para que las cooperativas evalúen el rendimiento económico del conjunto de sus socios: tasas de liquidación semanales, volúmenes comercializados por categorías de calidad, mermas logísticas durante el transporte marítimo o terrestre y concentraciones de oferta por zonas geográficas.

### 8. Portal para asesores técnicos y oficinas de extensión agraria

Un acceso dedicado para que los ingenieros agrónomos simulen planes de viabilidad económica antes de realizar una nueva plantación. Permite emitir informes de rentabilidad automáticos con citación y trazabilidad absoluta a las fuentes oficiales de costes de la comunidad autónoma, reduciendo la saturación de consultas burocráticas en los servicios públicos.

### 9. Integración con el módulo de subvenciones (PoseiLLM / PAC)

Conexión directa con el asistente normativo para deducir automáticamente las ayudas directas a la superficie o a la comercialización (por ejemplo, ayuda por hectárea de aguacate o plátano del POSEI) en el cálculo del beneficio neto total del agricultor, ofreciendo una simulación financiera real de la rentabilidad del negocio.

## Precios y planes de licenciamiento

La estructura de precios de PrecioLLM refleja la complejidad y el valor de las operaciones comerciales del sector primario en el mercado español:

- **Plan Cooperativa Local:** 6.000 €/mes para cooperativas agrícolas regionales u Oficinas de Extensión Agraria de ámbito insular que requieran el procesamiento de boletines básicos, gestión de costes para hasta 200 socios y acceso a la interfaz web estándar con citación automática.
- **Plan Federación Agraria:** 12.000 €/mes para grandes organizaciones de productores (OPFH), cooperativas de segundo grado o federaciones de exportadores multi-isla. Añade el procesador de imágenes/tablas basado en visión artificial avanzada, API de integración con sistemas ERP de almacén y analítica predictiva de márgenes.
- **Plan Gran Distribución / Corporativo:** precio personalizado bajo cotización para cadenas de supermercados, grandes comercializadoras mayoristas o instituciones públicas que requieran despliegues locales dedicados (servidores propios optimizados para hardware local bajo Ollama con control estricto de VRAM), personalizaciones completas con marca blanca y acceso API masivo.

*Todos los planes incluyen los servicios iniciales de despliegue, la indexación de los históricos de precios de la entidad y jornadas de capacitación técnica en campo.*

## Hoja de ruta de desarrollo (roadmap)

La planificación del desarrollo técnico de PrecioLLM incluye los siguientes hitos de ingeniería de software e inteligencia artificial:

- **Q2 2025:** lanzamiento de PrecioLLM versión 1.0 con el motor RAG de texto básico para la consulta de boletines de precios semanales e ingesta manual de fichas de costes de producción.
- **Q4 2025:** incorporación del modelo de visión multimodal (Llama 3.2 Vision) para la extracción automatizada de tablas de precios manuscritas o escaneadas desde tablones de anuncios físicos de las cooperativas.
- **Q2 2026:** integración nativa mediante herramientas de LangChain con sensores y software de gestión de almacén (ERP) para correlacionar picos de precios con la oferta real almacenada en tiempo real.
- **Q4 2026:** lanzamiento del módulo de seguros agrarios paramétricos en colaboración con Agroseguro, evaluando automáticamente la pérdida de rendimiento económico por inclemencias meteorológicas severas.
- **Q2 2027:** introducción de herramientas avanzadas de modelización del riesgo de transición climática, incorporando proyecciones del incremento del coste del agua desalada y su impacto a largo plazo en la rentabilidad de las medianías.
- **Q4 2027:** expansión del producto al mercado peninsular español e internacionalización del software hacia otras regiones ultraperiféricas de la Unión Europea con regímenes POSEI similares (por ejemplo, Madeira y Azores).

> PrecioLLM dota a los técnicos y gestores del sector primario de la capacidad de defender el valor real del producto en el mercado, garantizando que el agricultor reciba un precio justo basado en datos verídicos, transparentes y libres de especulación. ¡Transforma la gestión económica del campo con PrecioLLM!