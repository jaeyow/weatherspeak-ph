-- Mock Active Storm Data for Local Testing
-- Run this in your Supabase SQL Editor or via psql

-- Insert a mock storm
INSERT INTO storms (storm_code, storm_name, international_name)
VALUES ('26-TEST', 'TestStorm', 'Kiko')
ON CONFLICT (storm_code, storm_name) DO NOTHING
RETURNING id;

-- Get the storm ID (if you need it for reference)
-- You can run this separately after the insert:
-- SELECT id FROM storms WHERE storm_name = 'TestStorm';

-- Insert a recent bulletin (makes the storm "active")
WITH storm_id_cte AS (
  SELECT id FROM storms WHERE storm_name = 'TestStorm' LIMIT 1
)
INSERT INTO bulletins (
  storm_id,
  stem,
  bulletin_type,
  bulletin_number,
  issued_at,
  valid_until,
  category,
  wind_signal,
  max_sustained_winds_kph,
  gusts_kph,
  movement_direction,
  movement_speed_kph,
  current_lat,
  current_lon,
  current_reference,
  affected_areas,
  chart_path,
  pdf_url
)
SELECT
  id,
  'PAGASA_26-TEST_TestStorm_SWB#01',
  'SWB',
  1,
  NOW() - INTERVAL '2 hours',  -- 2 hours ago = definitely active
  NOW() + INTERVAL '6 hours',
  'Typhoon',
  3,  -- Signal 3 (orange badge)
  120,
  150,
  'West Northwest',
  15,
  14.5,
  121.0,
  '450 km East of Manila',
  '{"signal_1": ["Quezon", "Rizal"], "signal_2": ["Laguna", "Batangas"], "signal_3": ["Metro Manila", "Cavite"]}'::jsonb,
  'charts/mock_storm/chart.png',
  'https://example.com/mock_bulletin.pdf'
FROM storm_id_cte
ON CONFLICT (stem) DO UPDATE SET
  issued_at = NOW() - INTERVAL '2 hours',
  valid_until = NOW() + INTERVAL '6 hours';

-- Optional: Insert mock bulletin_media rows (for audio player to show)
WITH storm_id_cte AS (
  SELECT id FROM storms WHERE storm_name = 'TestStorm' LIMIT 1
),
bulletin_id_cte AS (
  SELECT id FROM bulletins WHERE stem = 'PAGASA_26-TEST_TestStorm_SWB#01' LIMIT 1
)
INSERT INTO bulletin_media (bulletin_id, language, audio_path, script_path, tts_path, audio_duration_seconds, status)
SELECT
  bulletin_id_cte.id,
  lang::language_code,  -- Cast to enum type
  'mock_storm/audio_' || lang || '.mp3',
  'mock_storm/radio_' || lang || '.md',
  'mock_storm/tts_' || lang || '.txt',
  180,  -- 3 minutes
  'ready'
FROM bulletin_id_cte, unnest(ARRAY['en', 'tl', 'ceb']) AS lang
ON CONFLICT (bulletin_id, language) DO UPDATE SET
  status = 'ready';

-- Verify the mock storm is active
SELECT 
  storm_name,
  current_category,
  current_signal,
  current_reference,
  is_active,
  last_bulletin_at
FROM storms_with_status
WHERE storm_name = 'TestStorm';
