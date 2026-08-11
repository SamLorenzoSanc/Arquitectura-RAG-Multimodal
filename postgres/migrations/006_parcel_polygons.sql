-- Geometría de parcela: polígono GeoJSON + código de parcela.
-- Idempotente. lat/lon siguen siendo el centroide.

ALTER TABLE public.crops
  ADD COLUMN IF NOT EXISTS poligono jsonb,
  ADD COLUMN IF NOT EXISTS parcela_codigo character varying(64);

COMMENT ON COLUMN public.crops.poligono IS
  'GeoJSON Polygon: {"type":"Polygon","coordinates":[[[lon,lat],...]]}';
COMMENT ON COLUMN public.crops.parcela_codigo IS
  'Identificador de parcela dentro de la finca (ej. P-01)';

-- Polígonos demo (~cuadrados) alrededor de las fincas seed
UPDATE public.crops SET
  parcela_codigo = 'P-01',
  poligono = '{
    "type":"Polygon",
    "coordinates":[[
      [-17.7650,28.6825],[-17.7634,28.6825],[-17.7634,28.6845],[-17.7650,28.6845],[-17.7650,28.6825]
    ]]
  }'::jsonb
WHERE id = 'dbcb6b2b-bf68-45cc-8149-44dd0577b343';

UPDATE public.crops SET
  parcela_codigo = 'P-01',
  poligono = '{
    "type":"Polygon",
    "coordinates":[[
      [-15.7832,27.9802],[-15.7816,27.9802],[-15.7816,27.9820],[-15.7832,27.9820],[-15.7832,27.9802]
    ]]
  }'::jsonb
WHERE id = '58041ead-c2ff-4de8-b2ba-487a097676ca';

UPDATE public.crops SET
  parcela_codigo = 'P-01',
  poligono = '{
    "type":"Polygon",
    "coordinates":[[
      [-13.6850,28.9864],[-13.6832,28.9864],[-13.6832,28.9882],[-13.6850,28.9882],[-13.6850,28.9864]
    ]]
  }'::jsonb
WHERE id = '51602692-142b-4d20-a913-202952ac711f';

UPDATE public.crops SET
  parcela_codigo = 'P-01',
  poligono = '{
    "type":"Polygon",
    "coordinates":[[
      [-16.5249,28.3574],[-16.5233,28.3574],[-16.5233,28.3590],[-16.5249,28.3590],[-16.5249,28.3574]
    ]]
  }'::jsonb
WHERE id = 'ffe88808-06a5-4452-9297-8b6c9867d98f';

UPDATE public.crops SET
  parcela_codigo = 'P-02',
  poligono = '{
    "type":"Polygon",
    "coordinates":[[
      [-17.9442,28.6808],[-17.9426,28.6808],[-17.9426,28.6824],[-17.9442,28.6824],[-17.9442,28.6808]
    ]]
  }'::jsonb
WHERE id = '7a8aff1f-0b97-40d4-a57d-ce3cab8f2c27';

UPDATE public.crops SET
  parcela_codigo = 'P-01',
  poligono = '{
    "type":"Polygon",
    "coordinates":[[
      [-16.4390,28.4387],[-16.4374,28.4387],[-16.4374,28.4403],[-16.4390,28.4403],[-16.4390,28.4387]
    ]]
  }'::jsonb
WHERE id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
