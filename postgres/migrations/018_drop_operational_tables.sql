-- Retira el módulo operativo (fincas, sensores, logística, SAT/ISTAC).
-- El producto conserva auth, RAG, evaluación, datasets y cuaderno de campo.
-- Idempotente: DROP IF EXISTS.

ALTER TABLE IF EXISTS public.field_notebook_entries
  DROP CONSTRAINT IF EXISTS field_notebook_entries_crop_id_fkey;

DROP INDEX IF EXISTS public.idx_field_notebook_crop;
DROP INDEX IF EXISTS public.idx_crops_user_id;
DROP INDEX IF EXISTS public.idx_crops_organization_id;
DROP INDEX IF EXISTS public.idx_crop_treatments_crop_id;
DROP INDEX IF EXISTS public.idx_sensor_readings_entity;
DROP INDEX IF EXISTS public.idx_sensor_readings_topic_time;
DROP INDEX IF EXISTS public.idx_shipments_tenant;
DROP INDEX IF EXISTS public.idx_shipments_container;
DROP INDEX IF EXISTS public.idx_sat_societies_municipio;
DROP INDEX IF EXISTS public.idx_sat_societies_situacion;
DROP INDEX IF EXISTS public.idx_istac_observations_series;

DROP TABLE IF EXISTS public.crop_treatments;
DROP TABLE IF EXISTS public.crops;
DROP TABLE IF EXISTS public.sensor_readings;
DROP TABLE IF EXISTS public.shipments;
DROP TABLE IF EXISTS public.logistics_containers;
DROP TABLE IF EXISTS public.logistics_vessels;
DROP TABLE IF EXISTS public.istac_observations;
DROP TABLE IF EXISTS public.istac_series;
DROP TABLE IF EXISTS public.sat_societies;
