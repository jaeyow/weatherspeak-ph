-- Simpler mock storm - ensures it's definitely active
-- Run this to replace the previous attempt

-- Clean up first (if exists)
DELETE FROM bulletins WHERE stem = 'PAGASA_26-TEST_TestStorm_SWB#01';
DELETE FROM storms WHERE storm_name = 'TestStorm';

-- Insert storm
INSERT INTO storms (storm_code, storm_name, international_name)
VALUES ('26-TEST', 'TestStorm', 'Kiko');

-- Insert bulletin with current timestamp (definitely within 24 hours)
INSERT INTO bulletins (
  storm_id,
  stem,
  bulletin_type,
  bulletin_number,
  issued_at,
  category,
  wind_signal,
  current_lat,
  current_lon,
  current_reference,
  pdf_url
)
SELECT
  id,
  'PAGASA_26-TEST_TestStorm_SWB#01',
  'SWB',
  1,
  CURRENT_TIMESTAMP,  -- Right now!
  'Typhoon',
  3,
  14.5,
  121.0,
  '450 km East of Manila',
  'https://example.com/mock.pdf'
FROM storms
WHERE storm_name = 'TestStorm';

-- Verify it's active
SELECT 
  storm_name,
  is_active,
  last_bulletin_at,
  current_signal,
  current_category
FROM storms_with_status
WHERE storm_name = 'TestStorm';
