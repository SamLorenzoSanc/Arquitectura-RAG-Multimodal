---
source: BOE legislación agricultura
url: https://www.boe.es/legislacion/eli.php
category: normativa
---

El Identificador Europeo de Legislación-ELI (European Legislation Identifier) es un estándar europeo de identificación y descripción de la normativa publicada en los diarios y las bases de datos oficiales, que permite acceder online a la legislación en un formato normalizado, de manera que pueda localizarse, intercambiarse y reutilizarse por encima de las fronteras.
El estándar ELI incluye especificaciones técnicas sobre:
La implementación de este identificador en España se está abordando de forma coordinada, a través de la Comisión Sectorial de Administración Electrónica, que es un órgano técnico de cooperación del Estado, las Comunidades Autónomas y las Administraciones Locales. Por ello, esta Comisión decidió crear en el año 2017 un "Grupo de Trabajo ELI" para estudiar la forma de aplicar este estándar a la legislación española.
A partir del trabajo realizado por este grupo, la Comisión Sectorial de Administración Electrónica aprobó en su reunión de 13 de marzo de 2018 la "Especificación técnica para la implementación del Identificador Europeo de Legislación en España (fase 1)", aplicable a la normativa estatal y autonómica. Posteriormente, el 24 de febrero de 2022 se aprobó una nueva versión de la Especificación ELI que incluye las adaptaciones necesarias para aplicar el ELI también a la normativa local.
La Especificación tiene como objetivo establecer las directrices comunes que requiere la implementación del ELI en el contexto español, de manera que la identificación y descripción de las normas estatales, autonómicas y locales se realice de manera coordinada y coherente por las distintas Administraciones.
De esta manera, España se suma a la lista de países europeos que ya aplican el estándar ELI (entre otros Dinamarca, Finlandia, Francia, Irlanda, Italia, Luxemburgo, Noruega, Portugal, Austria, Bélgica, Polonia y Reino Unido), además de la propia Unión Europea.
Más información sobre ELI en el portal común https://www.elidata.es
Las Administraciones estatal y autonómicas están trabajando para aplicar el ELI a la normativa que ofrecen en sus distintas bases de datos, utilizando como base la Especificación Técnica para la implementación del Identificador Europeo de Legislación .
Por parte de la Administración General del Estado, la Agencia Estatal BOE (AEBOE) comenzó a aplicar el ELI en diciembre de 2018, y ya se cuenta con más de 90.000 normas identificadas y descritas con arreglo al estándar europeo.
Conforme a la especificación técnica, la AEBOE aplica el ELI a:
Cada recurso legal cuenta con una URI (Uniform Resource Identifier) que la identifica de manera unívoca y permanente en internet.
Las URIs se construyen conforme a la plantilla definida por la especificación técnica para las normas estatales y autonómicas, que se muestra a continuación:
/eli/{jurisdiction}/{type}/{year}/{month}/{day}/{number}/{version}/{version\_date}/{language}/{format}
También se identifican con ELI las correcciones de errores de las normas publicadas en el BOE, con la siguiente estructura que se basa en la URI de la norma corregida:
/eli/{jurisdiction}/{type}/{year}/{month}/{day}/{number}/{corrigendum}/{pubdate}/{dof}{/language}/{format}
Las normas se describen adaptándose al modelo FRBR (Functional Requirements for Bibliographic Records), distinguiendo diferentes niveles:
La especificación técnica establece que se tendrán en consideración para cada norma, dos niveles de recursos legales:
Todos estos recursos se relacionan entre si mediante distintas "propiedades eli".
Más información en el apartado 5 de la "Especificación técnica para la implementación del Identificador Europeo de Legislación en España ".
Al consultar la base de datos de Legislación encontrará en la cabecera de cada norma, el enlace "Permalink ELI" que contiene la URI del recurso legal abstracto.
Estos son algunos ejemplos de URI para los distintos tipos de rangos existentes en las bases de datos del BOE:
A partir de la URI del recurso legal abstracto se generan las URIs de los recursos legales que agrupa, así como de sus expresiones y formatos.
Ejemplo: Ley 40/2015, de 1 de octubre, de Régimen Jurídico del Sector Público
La especificación técnica ha seleccionado los metadatos de la ontología ELI que como mínimo deben compartir todas las Administraciones, para describir las normas estatales y autonómicas de sus bases de datos (metadatos mínimos comunes).
La relación de metadatos mínimos comunes puede consultarse en https://www.elidata.es/mdr/metadata/
La AEBOE, en aplicación de los tres pilares del ELI ofrece los metadatos mínimos comunes en formato RDF: en las páginas HTML de la disposición está disponible en RDFa y en las páginas XML en RDF/XML.
En cuanto a los metadatos que definen las relaciones entre las normas publicadas en el BOE y en los diarios autonómicos, el metadato eli:is another\_publication está disponible para las normas de aquellas Comunidades Autónomas que han implementado el identificador.
Además, la AEBOE ofrece el metadato eli:is\_about que describe la materia o temática a la que hace referencia un recurso legal. Consulte los valores que puede tomar el metadato eli:is\_about y su correspondiente descripción.
Uno de los objetivos principales del ELI es facilitar la reutilización de la información legal, mediante la configuración de URIs y la generación de metadatos expresados en RDF para cada norma, basándose en un estándar compartido entre los distintos diarios y bases de datos oficiales.
No obstante, la consecución de este objetivo se ve reforzada si además se ofrece a los reutilizadores una lista completa y actualizada de los recursos legales que cada proveedor de información legal identifica mediante el ELI. Por ello, la Agencia Estatal BOE pone a disposición de los usuarios una serie de archivos que han sido específicamente diseñados para facilitar la reutilización de la información legislativa en base al estándar ELI .
Estos archivos contienen la lista completa de todas las normas a las que la Agencia Estatal BOE ha aplicado el ELI, las cuales aparecen identificadas mediante las URIs correspondientes al recurso legal abstracto.
Estas URIs apuntan a las páginas HTML que un reutilizador necesitaría recorrer para descargar por completo el conjunto de metadatos ELI disponibles en la web de la AEBOE.
Ha de tenerse en cuenta que entre los metadatos ELI de cada norma se incluyen las URIs de las distintas versiones expresiones y formatos, lo que permite que desde las correspondientes URLs, el reutilizador pueda descargar el texto inicial o consolidado de la norma y hacerlo en el formato que prefiera de entre los que se encuentren disponibles
https://boe.es/eli/sitemap.xml
Esta página muestra el índice de archivos sitemaps disponibles en cada momento
Mensual.
Se complementa con un fichero ATOM en el que se recogen las actualizaciones (últimos 60 días).
Según el protocolo Sitemap .
Cada entrada se conforma con los siguientes elementos:
Contiene la lista de nuevos recursos legales y de aquellos que han experimentado algún tipo de actualización, ya sea por cambios en sus metadatos ELI o por generación de una nueva versión consolidada.
Los recursos se identificación mediante la URI del recurso legal abstracto
Diaria.
Además, contiene un histórico de las actualizaciones de los últimos 60 días.
Según el protocolo Atom .
Cada entrada se conforma con los siguientes elementos XML:
Agencia Estatal Boletín Oficial del Estado
Avda. de Manoteras, 54 - 28050 Madrid
