-- sensor_readings: series temporales IoT (riego / reefer) vía telemetry-service
CREATE TABLE IF NOT EXISTS public.sensor_readings (
    id varchar(36) PRIMARY KEY,
    topic text NOT NULL,
    entity_type varchar(32) NOT NULL,
    entity_id varchar(64) NOT NULL,
    metric varchar(64) NOT NULL,
    value double precision NOT NULL,
    unit varchar(32),
    payload jsonb,
    recorded_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_entity
  ON public.sensor_readings (entity_type, entity_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_topic_time
  ON public.sensor_readings (topic, recorded_at DESC);
