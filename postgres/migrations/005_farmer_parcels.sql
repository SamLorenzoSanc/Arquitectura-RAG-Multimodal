-- Perfil operativo del agricultor: parcela + agua + fitosanitarios.
-- Idempotente.

ALTER TABLE public.crops
  ADD COLUMN IF NOT EXISTS organization_id uuid,
  ADD COLUMN IF NOT EXISTS ref_catastral character varying(64),
  ADD COLUMN IF NOT EXISTS superficie_ha double precision,
  ADD COLUMN IF NOT EXISTS variedad character varying(120),
  ADD COLUMN IF NOT EXISTS sistema_riego character varying(120),
  ADD COLUMN IF NOT EXISTS fuente_agua character varying(120),
  ADD COLUMN IF NOT EXISTS dotacion_m3_ha_anio double precision,
  ADD COLUMN IF NOT EXISTS comunidad_regantes character varying(180),
  ADD COLUMN IF NOT EXISTS certificaciones text,
  ADD COLUMN IF NOT EXISTS notas text;

CREATE TABLE IF NOT EXISTS public.crop_treatments (
    id character varying(36) PRIMARY KEY,
    crop_id character varying(36) NOT NULL REFERENCES public.crops(id) ON DELETE CASCADE,
    fecha date NOT NULL,
    producto character varying(180) NOT NULL,
    materia_activa character varying(180),
    dosis character varying(80),
    plaga_objetivo character varying(180),
    carencia_dias integer,
    observaciones text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_crop_treatments_crop_id ON public.crop_treatments(crop_id);
CREATE INDEX IF NOT EXISTS idx_crops_user_id ON public.crops(user_id);
CREATE INDEX IF NOT EXISTS idx_crops_organization_id ON public.crops(organization_id);

-- Enriquecer parcelas seed existentes (muestra TFM significativa)
UPDATE public.crops SET
  ref_catastral = '38026A01200045',
  superficie_ha = 3.2,
  variedad = 'Gran Enana',
  sistema_riego = 'Goteo',
  fuente_agua = 'Comunidad de regantes + desalada',
  dotacion_m3_ha_anio = 9500,
  comunidad_regantes = 'CR Tazacorte',
  certificaciones = 'IGP Plátano de Canarias; GlobalGAP',
  notas = 'Perfil demo TFM: plátano La Palma con riego goteo y trazabilidad fitosanitaria.'
WHERE id = 'dbcb6b2b-bf68-45cc-8149-44dd0577b343';

UPDATE public.crops SET
  ref_catastral = '35016A00800112',
  superficie_ha = 1.8,
  variedad = 'Daniela',
  sistema_riego = 'Goteo bajo invernadero',
  fuente_agua = 'Pozo + red pública',
  dotacion_m3_ha_anio = 6200,
  comunidad_regantes = 'CR Aldea de San Nicolás',
  certificaciones = 'GlobalGAP',
  notas = 'Tomate de exportación en costa oeste de Gran Canaria.'
WHERE id = '58041ead-c2ff-4de8-b2ba-487a097676ca';

UPDATE public.crops SET
  ref_catastral = '35014A00300077',
  superficie_ha = 4.5,
  variedad = 'Malvasía Volcánica',
  sistema_riego = 'Secano / enarenado',
  fuente_agua = 'Humedad retenida en lapilli',
  dotacion_m3_ha_anio = 800,
  comunidad_regantes = NULL,
  certificaciones = 'DOP Lanzarote',
  notas = 'Viña en La Geria; dotación hídrica mínima por enarenado.'
WHERE id = '51602692-142b-4d20-a913-202952ac711f';

UPDATE public.crops SET
  ref_catastral = '38023A01500201',
  superficie_ha = 0.9,
  variedad = 'Bonita',
  sistema_riego = 'Aspersión ocasional',
  fuente_agua = 'Galería / lluvia',
  dotacion_m3_ha_anio = 2800,
  comunidad_regantes = 'CR Medianías Norte',
  certificaciones = 'DOP Papas Antiguas de Canarias',
  notas = 'Papas antiguas en medianías de Tenerife.'
WHERE id = 'ffe88808-06a5-4452-9297-8b6c9867d98f';

UPDATE public.crops SET
  ref_catastral = '38026A01200088',
  superficie_ha = 2.4,
  variedad = 'Gruesa',
  sistema_riego = 'Goteo',
  fuente_agua = 'Balsa + comunidad de regantes',
  dotacion_m3_ha_anio = 8800,
  comunidad_regantes = 'CR Los Llanos',
  certificaciones = 'IGP Plátano de Canarias',
  notas = 'Segunda parcela de plátano (Finca Lorenzos).'
WHERE id = '7a8aff1f-0b97-40d4-a57d-ce3cab8f2c27';

-- Insertar parcela de aguacate si no existe (5º perfil)
INSERT INTO public.crops (
  id, user_id, nombre, cultivo, isla, lat, lon,
  temperatura, humedad, lluvia, viento, ndvi, sentinel_tile,
  ref_catastral, superficie_ha, variedad, sistema_riego, fuente_agua,
  dotacion_m3_ha_anio, comunidad_regantes, certificaciones, notas
)
SELECT
  'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
  'b41323cb-a9b6-45f1-802a-cf8f1d68852e',
  'Finca El Sauzal - Aguacate',
  'Aguacate',
  'Tenerife',
  28.4395,
  -16.4382,
  20.5,
  70,
  18,
  11,
  0.72,
  'T28RBS',
  '38038A00700033',
  2.1,
  'Hass',
  'Goteo',
  'Pozo privado',
  7500,
  'CR El Sauzal',
  'GlobalGAP',
  'Aguacate subtropical medianías norte Tenerife.'
WHERE NOT EXISTS (
  SELECT 1 FROM public.crops WHERE id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
);

-- Tratamientos fitosanitarios de muestra (solo si existe la parcela)
INSERT INTO public.crop_treatments (
  id, crop_id, fecha, producto, materia_activa, dosis, plaga_objetivo, carencia_dias, observaciones
)
SELECT v.id, v.crop_id, v.fecha::date, v.producto, v.materia_activa, v.dosis,
       v.plaga_objetivo, v.carencia_dias, v.observaciones
FROM (
  VALUES
  (
    't001-platano-lp-001', 'dbcb6b2b-bf68-45cc-8149-44dd0577b343',
    '2026-03-12', 'Oillette EC', 'Aceite de parafina', '1.5 L/ha',
    'Cochinilla / trips', 3, 'Tratamiento preventivo de primavera'
  ),
  (
    't001-platano-lp-002', 'dbcb6b2b-bf68-45cc-8149-44dd0577b343',
    '2026-05-02', 'Score 25 EC', 'Difenoconazol', '0.4 L/ha',
    'Sigatoka', 14, 'Aplicación foliar autorizada IGP'
  ),
  (
    't001-platano-lp-003', 'dbcb6b2b-bf68-45cc-8149-44dd0577b343',
    '2026-06-18', 'Karate Zeon', 'Lambda-cihalotrina', '0.1 L/ha',
    'Orugas defoliadoras', 7, NULL
  ),
  (
    't002-tomate-gc-001', '58041ead-c2ff-4de8-b2ba-487a097676ca',
    '2026-02-20', 'Confidor', 'Imidacloprid', '0.5 L/ha',
    'Mosca blanca', 3, 'Bajo invernadero'
  ),
  (
    't002-tomate-gc-002', '58041ead-c2ff-4de8-b2ba-487a097676ca',
    '2026-04-05', 'Switch', 'Ciprofinil + Fludioxonil', '0.8 kg/ha',
    'Botritis', 7, NULL
  ),
  (
    't003-vina-lz-001', '51602692-142b-4d20-a913-202952ac711f',
    '2026-01-15', 'Azufre micronizado', 'Azufre', '8 kg/ha',
    'Oídio', 0, 'Tratamiento tradicional La Geria'
  ),
  (
    't003-vina-lz-002', '51602692-142b-4d20-a913-202952ac711f',
    '2026-03-28', 'Cuproxyl', 'Oxicloruro de cobre', '2 kg/ha',
    'Mildiu', 21, NULL
  ),
  (
    't004-papa-tf-001', 'ffe88808-06a5-4452-9297-8b6c9867d98f',
    '2026-01-08', 'Ridomil Gold', 'Metalaxil-M + Mancozeb', '2.5 kg/ha',
    'Mildiu de la papa', 14, 'Ciclo de invierno'
  ),
  (
    't004-papa-tf-002', 'ffe88808-06a5-4452-9297-8b6c9867d98f',
    '2026-02-14', 'Actara', 'Tiametoxam', '0.2 kg/ha',
    'Pulgón / escarabajo', 7, NULL
  ),
  (
    't005-aguacate-001', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    '2026-04-10', 'Vertimec', 'Abamectina', '0.75 L/ha',
    'Ácaros', 14, NULL
  ),
  (
    't005-aguacate-002', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    '2026-05-22', 'Cuprocol', 'Hidróxido cúprico', '2 L/ha',
    'Antracnosis', 21, 'Post-floración'
  )
) AS v(
  id, crop_id, fecha, producto, materia_activa, dosis,
  plaga_objetivo, carencia_dias, observaciones
)
WHERE EXISTS (
  SELECT 1 FROM public.crops c WHERE c.id = v.crop_id
)
ON CONFLICT (id) DO NOTHING;
