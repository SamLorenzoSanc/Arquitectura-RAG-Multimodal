# Perfiles operativos del agricultor (muestra TFM)

Hechos estructurados en Postgres (`crops` + `crop_treatments`) que el chat
inyecta en Hybrid y Agentic como `PERFIL_OPERATIVO_AGRICULTOR`.

| ID parcela | Nombre | Cultivo | Isla | ha | Riego / agua | Certificaciones |
|---|---|---|---|---:|---|---|
| `dbcb6b2b-...4343` | Finca La Palma - Sector Norte | Plátano Gran Enana | La Palma | 3.2 | Goteo / CR Tazacorte + desalada (9500 m³/ha·año) | IGP + GlobalGAP |
| `58041ead-...676ca` | Explotación Aldea San Nicolás | Tomate Daniela | Gran Canaria | 1.8 | Goteo invernadero / pozo+red (6200) | GlobalGAP |
| `51602692-...ac711f` | Viñedos de la Geria | Malvasía Volcánica | Lanzarote | 4.5 | Secano/enarenado (800) | DOP Lanzarote |
| `ffe88808-...67d98f` | Cultivo de Papas Bonitas | Papa Bonita | Tenerife | 0.9 | Aspersión / galería (2800) | DOP Papas Antiguas |
| `a1b2c3d4-...567890` | Finca El Sauzal - Aguacate | Aguacate Hass | Tenerife | 2.1 | Goteo / pozo (7500) | GlobalGAP |

## Preguntas de evaluación ligadas a hechos (10)

Usar con `crop_id` de la parcela correspondiente. La respuesta de referencia
debe anclarse al perfil estructurado (no solo a la KB genérica).

1. **direct_fact / plátano** — `dbcb6b2b-...`  
   *¿Cuál es la referencia catastral y la superficie de mi finca de plátano en La Palma?*  
   Ref: `38026A01200045`, 3.2 ha.

2. **direct_fact / agua** — `dbcb6b2b-...`  
   *¿Qué dotación hídrica anual tengo registrada y de dónde me llega el agua?*  
   Ref: 9500 m³/ha·año; comunidad CR Tazacorte + desalada; riego por goteo.

3. **relationship / fitosanitario** — `dbcb6b2b-...`  
   *¿Qué carencia tiene el último tratamiento de Score 25 EC que apliqué contra sigatoka?*  
   Ref: 14 días (difenoconazol, 0.4 L/ha, 2026-05-02).

4. **direct_fact / tomate** — `58041ead-...`  
   *¿Qué variedad de tomate cultivo en Aldea San Nicolás y bajo qué sistema de riego?*  
   Ref: Daniela; goteo bajo invernadero.

5. **regulatory_compliance / tomate** — `58041ead-...`  
   *Tras el tratamiento de Confidor del 20/02/2026, ¿cuántos días de carencia debo respetar?*  
   Ref: 3 días (imidacloprid, mosca blanca).

6. **direct_fact / viña** — `51602692-...`  
   *¿Por qué mi viña de La Geria tiene una dotación tan baja?*  
   Ref: secano/enarenado; humedad retenida en lapilli; ~800 m³/ha·año; DOP Lanzarote.

7. **temporal / papas** — `ffe88808-...`  
   *¿Qué tratamiento aplicé en enero 2026 a las papas Bonitas y contra qué?*  
   Ref: Ridomil Gold (metalaxil-M + mancozeb), mildiu, 14 días carencia (2026-01-08).

8. **direct_fact / aguacate** — `a1b2c3d4-...`  
   *¿Qué certificaciones y superficie tiene mi finca de aguacate Hass en El Sauzal?*  
   Ref: GlobalGAP; 2.1 ha; ref. `38038A00700033`.

9. **spanning / multi-parcela**  
   *¿Cuántas hectáreas de plátano tengo entre Sector Norte y Finca Lorenzos?*  
   Ref: 3.2 + 2.4 = 5.6 ha (ambas IGP Plátano de Canarias).

10. **traceability / perfil→KB** — `dbcb6b2b-...`  
    *Según mi perfil GlobalGAP e IGP, ¿qué requisitos de trazabilidad fitosanitaria debo documentar?*  
    Ref: cruzar hechos del perfil (tratamientos con producto, dosis, carencia, fecha)
    con normativa/manuales de la KB; no inventar dosis no registradas.

## Nota metodológica

Estas 10 preguntas complementan el banco normativo genérico. Demuestran que el
LLM dispone de **hechos del agricultor** (DB) además de **conocimiento documental** (RAG).
