# PoseiLLM

## Resumen de la plataforma

PoseiLLM es la plataforma de inteligencia jurídica y gestión de subvenciones de nivel empresarial de AgroLLM, diseñada para automatizar la interpretación, cálculo y tramitación de ayudas directas al sector primario bajo los marcos regulatorios más complejos de la Unión Europea y España. Dirigida a Oficinas de Extensión Agraria, gestorías rurales y Organizaciones de Productores (OPFH), PoseiLLM especializa su arquitectura en desgranar la normativa de la Política Agrícola Común (PAC) y el Programa de Opciones Específicas por la Lejanía e Insularidad (POSEI) propio de las regiones ultraperiféricas. Mediante una arquitectura de Inteligencia Artificial avanzada (RAG Multimodal local con Llama 3.2 y ChromaDB), PoseiLLM procesa los densos boletines oficiales (BOC/BOE), bases de datos de resoluciones y manuales de solicitud para resolver de forma instantánea y libre de alucinaciones los requisitos técnicos por hectárea o cultivo, reduciendo drásticamente la saturación burocrática del sector.

## Características principales

### 1. Motor RAG normativo avanzado (PAC y POSEI)

Un sistema de recuperación documental optimizado para el lenguaje legal y administrativo. Es capaz de indexar las publicaciones del Boletín Oficial de Canarias (BOC) y el Boletín Oficial del Estado (BOE), permitiendo a los técnicos realizar consultas complejas sobre las bases reguladoras de las ayudas sin necesidad de buscar manualmente entre cientos de páginas de anexos jurídicos.

### 2. Calculadora inteligente de ayudas por superficie (módulo subtrópicos)

Herramienta especializada en la formulación de ayudas directas basadas en el marco del POSEI. Permite calcular el importe estimado de la subvención por hectárea cultivada de frutales subtropicales (como el aguacate, plátano o papaya) cruzando en tiempo real las reglas de elegibilidad del terreno, estado de producción y superficies mínimas requeridas.

### 3. Trazabilidad estricta y citación automática de fuentes

Para garantizar la seguridad jurídica del asesoramiento, PoseiLLM incorpora un sistema de metadatos de grano fino en ChromaDB. Cada respuesta generada por el backend local bajo Ollama incluye la citación exacta del documento base, número de boletín, artículo y página, erradicando por completo el riesgo de alucinación legal y facilitando las auditorías.

### 4. Gestor documental para la PAC y condicionalidad reforzada

Asistente especializado en la interpretación de las exigencias del cuaderno de explotación y las Buenas Condiciones Agrarias y Medioambientales (BCAM) de la PAC en España. Resuelve consultas sobre la rotación obligatoria de cultivos, el mantenimiento de cubiertas vegetales en pendientes o las restricciones de abonado en zonas vulnerables.

### 5. Intérprete multimodal de formularios y fichas catastrales (SIGPAC)

Capacidades de visión por computadora mediante Llama 3.2 Vision que permiten procesar capturas de pantalla, planos o PDFs del visor SIGPAC (Sistema de Información Geográfica de Parcelas Agrícolas). La IA extrae los coeficientes de admisibilidad, las referencias de polígono/parcela y la región climática, asociándolos a la normativa de ayudas que les aplica de forma inmediata.

### 6. Módulo de ayudas específicas a la papa de medianías

Herramientas configuradas para desglosar las subvenciones del POSEI dedicadas a la producción de papa de mesa y papa de semilla local. El sistema evalúa los requisitos de entrega a cooperativas, las densidades de siembra y las cantidades mínimas comercializadas que el agricultor debe justificar para consolidar el derecho al cobro.

### 7. Optimizador de expedientes y alertas de concurrencia

Cuadro de mando analítico para gestorías y cooperativas que supervisa el estado de todos los expedientes de sus socios. La plataforma detecta posibles incompatibilidades entre diferentes líneas de ayuda y genera alertas tempranas antes del cierre de plazos sobre documentación faltante o incumplimiento de umbrales técnicos.

### 8. Portal de asistencia a la incorporación de jóvenes agricultores

Módulo especializado en la normativa y bases reguladoras para el relevo generacional en el campo y la modernización de explotaciones. Proporciona planes empresariales tipo, listas de control de requisitos y guías paso a paso para la justificación de las inversiones subvencionadas.

### 9. Simulador de impacto financiero de modificaciones de cultivo

Un motor de simulación para que los técnicos agrarios proyecten el cambio de ingresos por subvenciones si una explotación decide cambiar de cultivo (por ejemplo, pasar de hortalizas a aguacates). Evalúa el periodo de transición, las ayudas a la reconversión y la variación del derecho a cobro de la PAC.

## Precios y planes de licenciamiento

La estructura de precios de PoseiLLM se adapta a los volúmenes de expedientes y la complejidad jurídica de las entidades del sector agropecuario español:

- **Plan Oficina Rural / Asesoría:** 6.000 €/mes para gestorías agrarias, cooperativas locales u Oficinas de Extensión Agraria comarcales. Incluye el motor de búsqueda normativa básico de la PAC/POSEI, gestión de expedientes para hasta 200 productores y acceso a la interfaz web con citación automática.
- **Plan Organización de Productores (OPFH):** 12.000 €/mes para grandes cooperativas de segundo grado o agrupaciones nacionales de productores. Añade el procesador de documentos e imágenes SIGPAC mediante visión artificial, la API para cruzar datos con sistemas de gestión interna de socios y actualizaciones normativas prioritarias.
- **Plan Institucional / Gran Consorcio:** precio personalizado bajo cotización para consejos insulares, consejerías de agricultura o grandes firmas agroindustriales que requieran un despliegue dedicado en servidores propios (hardware local robusto con GPUs dedicadas bajo Ollama para garantizar la estricta privacidad de los datos personales), adaptaciones a medida de marca blanca y acceso API masivo.

*Todos los planes contemplan los servicios iniciales de configuración, la pre-carga e indexación de los históricos normativos de la región y talleres de capacitación para el equipo técnico.*

## Hoja de ruta de desarrollo (roadmap)

La hoja de ruta tecnológica para el desarrollo evolutivo de PoseiLLM define las siguientes fases de ingeniería de software e IA:

- **Q2 2025:** lanzamiento de PoseiLLM versión 1.0 con el motor RAG core de texto para consultas de las bases reguladoras vigentes de la PAC y el POSEI canario.
- **Q4 2025:** incorporación de Llama 3.2 Vision para el procesamiento automatizado de planos del SIGPAC, ortofotos de las parcelas y solicitudes de ayuda escaneadas en papel.
- **Q2 2026:** integración nativa a través de LangChain Tools con las plataformas y sedes electrónicas de las administraciones públicas para la verificación automatizada del estado de tramitación de los expedientes.
- **Q4 2026:** lanzamiento del módulo predictivo de asignación presupuestaria, estimando posibles coeficientes de reducción o prorrateo en las ayudas de concurrencia competitiva basándose en históricos de solicitudes.
- **Q2 2027:** introducción de herramientas avanzadas de auditoría de ecorregímenes, analizando si las prácticas agrarias declaradas mediante fotografía georreferenciada cumplen con las exigencias verdes de la UE.
- **Q4 2027:** expansión del producto para dar cobertura completa a los regímenes POSEI del resto de Regiones Ultraperiféricas (RUP) de la Unión Europea, traduciendo e indexando la normativa agrícola propia de Francia (Reunión, Martinica, Guadalupe) y Portugal (Madeira y Azores).

> PoseiLLM transforma la compleja y farragosa burocracia comunitaria en una herramienta clara, rápida y con absoluta seguridad jurídica para el asesoramiento de campo. ¡Asegura y optimiza las ayudas del sector primario con PoseiLLM!
    