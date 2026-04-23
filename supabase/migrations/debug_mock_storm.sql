-- Debug: Check if mock storm data exists
-- Run these queries one by one in Supabase SQL Editor

-- 1. Check if the storm was created
SELECT id, storm_code, storm_name, international_name, created_at
FROM storms
WHERE storm_name = 'TestStorm';

-- 2. Check if the bulletin was created
SELECT id, storm_id, stem, issued_at, category, wind_signal, current_reference
FROM bulletins
WHERE stem = 'PAGASA_26-TEST_TestStorm_SWB#01';

-- 3. Check the storms_with_status view (this is what the web app queries)
SELECT *
FROM storms_with_status
WHERE storm_name = 'TestStorm';

-- 4. Check what getActiveStorms() would return
SELECT *
FROM storms_with_status
WHERE is_active = true
ORDER BY current_signal DESC NULLS LAST, last_bulletin_at DESC;

-- 5. If nothing shows, check the issued_at timestamp
SELECT 
  storm_name,
  last_bulletin_at,
  NOW() as current_time,
  NOW() - INTERVAL '24 hours' as active_threshold,
  last_bulletin_at > NOW() - INTERVAL '24 hours' as should_be_active
FROM storms_with_status
WHERE storm_name = 'TestStorm';
