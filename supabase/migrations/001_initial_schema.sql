-- WeatherSpeak PH — initial schema
-- Run once against your Supabase project.

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------

CREATE TYPE language_code AS ENUM ('en', 'tl', 'ceb');

CREATE TYPE bulletin_type AS ENUM ('SWB', 'TCA', 'TCB', 'other');

CREATE TYPE storm_category AS ENUM (
  'Tropical Depression',
  'Tropical Storm',
  'Severe Tropical Storm',
  'Typhoon',
  'Super Typhoon'
);

CREATE TYPE media_status AS ENUM ('pending', 'ready', 'failed');

-- ---------------------------------------------------------------------------
-- storms
-- One row per named storm. ETL creates/upserts on first bulletin for a storm.
-- ---------------------------------------------------------------------------

CREATE TABLE storms (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  storm_code         text NOT NULL,          -- "19W", "TC02"
  storm_name         text NOT NULL,          -- "Pepito", "Basyang"
  international_name text,                   -- international name if any
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),

  UNIQUE (storm_code, storm_name)
);

-- Keep updated_at current whenever a new bulletin references this storm
CREATE OR REPLACE FUNCTION touch_storm_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  UPDATE storms SET updated_at = now() WHERE id = NEW.storm_id;
  RETURN NEW;
END;
$$;

-- ---------------------------------------------------------------------------
-- bulletins
-- One row per PAGASA PDF (one ETL run). Inserted after Step 1 OCR completes.
-- ---------------------------------------------------------------------------

CREATE TABLE bulletins (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  storm_id                uuid NOT NULL REFERENCES storms(id) ON DELETE CASCADE,
  stem                    text NOT NULL UNIQUE,   -- "PAGASA_20-19W_Pepito_SWB#01"
  bulletin_type           bulletin_type NOT NULL,
  bulletin_number         int,
  issued_at               timestamptz,
  valid_until             timestamptz,

  -- Storm state snapshot at this bulletin
  category                storm_category,
  wind_signal             int,                    -- 1–5, null if no signal
  max_sustained_winds_kph int,
  gusts_kph               int,
  movement_direction      text,
  movement_speed_kph      int,
  current_lat             float,
  current_lon             float,
  current_reference       text,                   -- "850 km east of Catanduanes"

  -- Rich structured data
  affected_areas          jsonb,  -- {signal_1:[...], signal_2:[...], ...}
  forecast_positions      jsonb,  -- [{hour:24, lat:..., lon:..., label:...}]

  -- Storage asset paths (relative to public bucket root)
  chart_path              text,   -- "charts/{stem}/chart.png"
  pdf_url                 text,   -- original PAGASA PDF URL

  created_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX bulletins_storm_id_idx   ON bulletins (storm_id);
CREATE INDEX bulletins_issued_at_idx  ON bulletins (issued_at DESC);

CREATE TRIGGER trg_touch_storm_updated_at
AFTER INSERT ON bulletins
FOR EACH ROW EXECUTE FUNCTION touch_storm_updated_at();

-- ---------------------------------------------------------------------------
-- bulletin_media
-- One row per bulletin × language. Inserted after Step 3 TTS completes.
-- ---------------------------------------------------------------------------

CREATE TABLE bulletin_media (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  bulletin_id            uuid NOT NULL REFERENCES bulletins(id) ON DELETE CASCADE,
  language               language_code NOT NULL,
  audio_path             text,   -- "audio/{stem}/audio_en.mp3"
  script_path            text,   -- "{stem}/radio_en.md"
  tts_path               text,   -- "{stem}/tts_en.txt"
  audio_duration_seconds int,
  status                 media_status NOT NULL DEFAULT 'pending',
  created_at             timestamptz NOT NULL DEFAULT now(),

  UNIQUE (bulletin_id, language)
);

CREATE INDEX bulletin_media_bulletin_id_idx ON bulletin_media (bulletin_id);

-- ---------------------------------------------------------------------------
-- storms_with_status view
-- is_active is derived — never a stale flag if a cron misses during a typhoon.
-- Surfaces current_signal and current_category for the home screen cards.
-- ---------------------------------------------------------------------------

CREATE VIEW storms_with_status AS
SELECT
  s.*,
  MAX(b.issued_at)                                                  AS last_bulletin_at,
  MAX(b.issued_at) > NOW() - INTERVAL '24 hours'                   AS is_active,
  (SELECT b2.wind_signal
   FROM   bulletins b2
   WHERE  b2.storm_id = s.id
   ORDER  BY b2.issued_at DESC LIMIT 1)                            AS current_signal,
  (SELECT b2.category::text
   FROM   bulletins b2
   WHERE  b2.storm_id = s.id
   ORDER  BY b2.issued_at DESC LIMIT 1)                            AS current_category,
  (SELECT b2.current_reference
   FROM   bulletins b2
   WHERE  b2.storm_id = s.id
   ORDER  BY b2.issued_at DESC LIMIT 1)                            AS current_reference
FROM  storms s
LEFT  JOIN bulletins b ON b.storm_id = s.id
GROUP BY s.id;

-- ---------------------------------------------------------------------------
-- Row Level Security
-- All data is public read. Writes are service-role only (no anon policy).
-- ---------------------------------------------------------------------------

ALTER TABLE storms         ENABLE ROW LEVEL SECURITY;
ALTER TABLE bulletins      ENABLE ROW LEVEL SECURITY;
ALTER TABLE bulletin_media ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read storms"         ON storms         FOR SELECT USING (true);
CREATE POLICY "public read bulletins"      ON bulletins      FOR SELECT USING (true);
CREATE POLICY "public read bulletin_media" ON bulletin_media FOR SELECT USING (true);
