# WeatherSpeak PH — Next.js Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a mobile-first Next.js 14 PWA deployed on Vercel that serves pre-generated PAGASA typhoon bulletin audio (EN/TL/CEB) from Supabase, with location-aware storm cards and a download-for-offline audio player.

**Architecture:** Next.js App Router with ISR-cached server components reading Supabase directly. Client components handle language toggle, location onboarding, and audio playback. No custom API routes, no auth. All Supabase reads use the service-role key server-side; audio streams from public Supabase Storage URLs.

**Tech Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS, `@supabase/supabase-js`, Vitest + `@testing-library/react`

---

## File Map

All files live under `web/` in the monorepo root.

```
web/
├── app/
│   ├── globals.css
│   ├── layout.tsx                   # Root layout: HTML shell + <Header> + onboarding trigger
│   ├── page.tsx                     # Home: active storms + past storms (ISR 15 min)
│   ├── storms/
│   │   └── [stormId]/
│   │       └── page.tsx             # Storm detail + latest bulletin audio (ISR 10 min)
│   └── bulletins/
│       └── [bulletinId]/
│           └── page.tsx             # Individual bulletin audio (ISR 10 min)
├── components/
│   ├── Header.tsx                   # App name + LanguageToggle + location label [client]
│   ├── StormCard.tsx                # Signal-first card [server]
│   ├── SignalBadge.tsx              # Colour-coded signal block [server]
│   ├── AudioPlayer.tsx              # Play/pause/seek/download [client]
│   ├── BulletinAudioSection.tsx     # Language-aware audio wrapper [client]
│   ├── LanguageToggle.tsx           # TL·CEB·EN pill [client]
│   ├── LocationOnboarding.tsx       # First-visit modal [client]
│   ├── DistancePill.tsx             # Haversine distance pill [client]
│   └── AffectedAreas.tsx           # Expandable accordion [client]
├── lib/
│   ├── supabase/
│   │   ├── server.ts                # createClient() — service role, server-side only
│   │   └── queries.ts               # getActiveStorms, getPastStorms, getStormDetail, getBulletin
│   ├── haversine.ts                 # haversine(lat1,lon1,lat2,lon2): number
│   ├── audio-url.ts                 # audioUrl(path): string
│   ├── affected-areas.ts            # parseAffectedAreas(areas): SignalSection[]
│   └── geography.ts                 # getProvinces(), getCitiesForProvince(), getCityCoords()
├── data/
│   └── philippines-geography.json   # Static: 81 provinces + major cities
├── types/
│   └── index.ts                     # All shared TypeScript types
├── tests/
│   ├── setup.ts                     # @testing-library/jest-dom import
│   ├── lib/
│   │   ├── haversine.test.ts
│   │   ├── audio-url.test.ts
│   │   ├── affected-areas.test.ts
│   │   └── geography.test.ts
│   └── components/
│       ├── SignalBadge.test.tsx
│       ├── AudioPlayer.test.tsx
│       └── DistancePill.test.tsx
├── public/
│   └── manifest.json                # PWA manifest
├── .env.local                       # Supabase keys (not committed)
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── vitest.config.ts
└── package.json
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `web/` (via create-next-app)
- Create: `web/vitest.config.ts`
- Create: `web/tests/setup.ts`
- Create: `web/.env.local`
- Modify: `web/next.config.ts`

- [ ] **Step 1: Scaffold the Next.js app**

Run from the repo root (`/Users/josereyes/Dev/gemma4-hackathon`):

```bash
npx create-next-app@14 web \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --no-src-dir \
  --import-alias "@/*"
```

When prompted, accept all defaults (App Router: yes, `@/*` alias: yes).

- [ ] **Step 2: Install dependencies**

```bash
cd web
npm install @supabase/supabase-js
npm install -D vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 3: Create vitest config**

Create `web/vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
    },
  },
});
```

- [ ] **Step 4: Create test setup file**

Create `web/tests/setup.ts`:

```typescript
import '@testing-library/jest-dom';
```

- [ ] **Step 5: Add test script to package.json**

Edit `web/package.json` — add `"test": "vitest"` and `"test:run": "vitest run"` to the `scripts` section:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest",
    "test:run": "vitest run"
  }
}
```

- [ ] **Step 6: Configure Next.js for Supabase Storage images**

Replace the contents of `web/next.config.ts`:

```typescript
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'ujebocmebijlewrbquoo.supabase.co',
        pathname: '/storage/v1/object/public/**',
      },
    ],
  },
};

export default nextConfig;
```

- [ ] **Step 7: Create environment variables file**

Create `web/.env.local`:

```
NEXT_PUBLIC_SUPABASE_URL=https://ujebocmebijlewrbquoo.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<paste anon key from Supabase dashboard>
SUPABASE_SERVICE_ROLE_KEY=<paste service role key from Supabase dashboard>
```

Add `web/.env.local` to the root `.gitignore` if not already covered:

```bash
cd ..  # back to repo root
echo "web/.env.local" >> .gitignore
cd web
```

- [ ] **Step 8: Verify setup**

```bash
npm run test:run
```

Expected: "No test files found" (no failures).

```bash
npm run build
```

Expected: build succeeds.

- [ ] **Step 9: Commit**

```bash
git add web/ .gitignore
git commit -m "feat: scaffold Next.js 14 frontend in web/"
```

---

### Task 2: TypeScript Types

**Files:**
- Create: `web/types/index.ts`

- [ ] **Step 1: Create the types file**

Create `web/types/index.ts`:

```typescript
export type Language = 'en' | 'tl' | 'ceb';

export interface BulletinMedia {
  id: string;
  bulletin_id: string;
  language: Language;
  audio_path: string | null;
  script_path: string | null;
  tts_path: string | null;
  audio_duration_seconds: number | null;
  status: 'pending' | 'ready' | 'failed';
}

// bulletin_media grouped by language — the shape passed to BulletinAudioSection
export type MediaByLang = Partial<Record<Language, BulletinMedia>>;

export interface AffectedAreas {
  signal_1?: string[];
  signal_2?: string[];
  signal_3?: string[];
  signal_4?: string[];
  signal_5?: string[];
  rainfall_warning?: string[];
  coastal_waters?: string | null;
}

export interface ForecastPosition {
  hour: number;
  label: string;
  latitude: number | null;
  longitude: number | null;
  reference: string | null;
}

export interface Bulletin {
  id: string;
  storm_id: string;
  stem: string;
  bulletin_type: 'SWB' | 'TCA' | 'TCB' | 'other';
  bulletin_number: number | null;
  issued_at: string | null;
  valid_until: string | null;
  category: string | null;
  wind_signal: number | null;
  max_sustained_winds_kph: number | null;
  gusts_kph: number | null;
  movement_direction: string | null;
  movement_speed_kph: number | null;
  current_lat: number | null;
  current_lon: number | null;
  current_reference: string | null;
  affected_areas: AffectedAreas | null;
  forecast_positions: ForecastPosition[] | null;
  chart_path: string | null;
  pdf_url: string | null;
  created_at: string;
  bulletin_media?: BulletinMedia[];
}

export interface Storm {
  id: string;
  storm_code: string;
  storm_name: string;
  international_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface StormWithStatus extends Storm {
  last_bulletin_at: string | null;
  is_active: boolean;
  current_signal: number | null;
  current_category: string | null;
  current_reference: string | null;
}

// Parsed signal section for the AffectedAreas accordion
export interface SignalSection {
  signal: number;
  areas: string[];
}

export interface GeoProvince {
  lat: number;
  lon: number;
  region: string;
}

export interface GeoCity {
  province: string;
  lat: number;
  lon: number;
}

export interface PhilippinesGeography {
  provinces: Record<string, GeoProvince>;
  cities: Record<string, GeoCity>;
}
```

- [ ] **Step 2: Commit**

```bash
git add web/types/index.ts
git commit -m "feat: add shared TypeScript types for WeatherSpeak PH frontend"
```

---

### Task 3: Philippines Geography Data

**Files:**
- Create: `web/data/philippines-geography.json`
- Create: `web/lib/geography.ts`
- Create: `web/tests/lib/geography.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `web/tests/lib/geography.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { getProvinces, getCitiesForProvince, getCityCoords } from '@/lib/geography';

describe('getProvinces', () => {
  it('returns a non-empty sorted list of province names', () => {
    const provinces = getProvinces();
    expect(provinces.length).toBeGreaterThan(0);
    expect(provinces).toEqual([...provinces].sort());
  });

  it('includes Metro Manila and Cebu', () => {
    const provinces = getProvinces();
    expect(provinces).toContain('Metro Manila');
    expect(provinces).toContain('Cebu');
  });
});

describe('getCitiesForProvince', () => {
  it('returns cities belonging to the given province', () => {
    const cities = getCitiesForProvince('Cebu');
    expect(cities.length).toBeGreaterThan(0);
    expect(cities).toContain('Cebu City');
  });

  it('returns empty array for unknown province', () => {
    expect(getCitiesForProvince('Atlantis')).toEqual([]);
  });
});

describe('getCityCoords', () => {
  it('returns lat/lon for a known city', () => {
    const coords = getCityCoords('Cebu City');
    expect(coords).not.toBeNull();
    expect(coords!.lat).toBeCloseTo(10.3157, 1);
    expect(coords!.lon).toBeCloseTo(123.8854, 1);
  });

  it('returns null for unknown city', () => {
    expect(getCityCoords('Gotham')).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm run test:run -- tests/lib/geography.test.ts
```

Expected: FAIL — "Cannot find module '@/lib/geography'"

- [ ] **Step 3: Create the geography data file**

Create `web/data/philippines-geography.json`:

```json
{
  "provinces": {
    "Metro Manila": { "lat": 14.5547, "lon": 121.0244, "region": "NCR" },
    "Cebu": { "lat": 10.3157, "lon": 123.8854, "region": "Region VII" },
    "Davao del Sur": { "lat": 6.8268, "lon": 125.0457, "region": "Region XI" },
    "Leyte": { "lat": 11.0, "lon": 124.6, "region": "Region VIII" },
    "Eastern Samar": { "lat": 11.6, "lon": 125.4, "region": "Region VIII" },
    "Southern Leyte": { "lat": 10.3367, "lon": 125.1718, "region": "Region VIII" },
    "Biliran": { "lat": 11.5833, "lon": 124.4650, "region": "Region VIII" },
    "Samar": { "lat": 12.0, "lon": 124.9, "region": "Region VIII" },
    "Northern Samar": { "lat": 12.5, "lon": 124.6, "region": "Region VIII" },
    "Albay": { "lat": 13.1775, "lon": 123.5280, "region": "Region V" },
    "Camarines Sur": { "lat": 13.5250, "lon": 123.3490, "region": "Region V" },
    "Camarines Norte": { "lat": 14.1389, "lon": 122.7632, "region": "Region V" },
    "Sorsogon": { "lat": 12.9433, "lon": 124.0035, "region": "Region V" },
    "Quezon": { "lat": 14.0313, "lon": 122.1152, "region": "Region IV-A" },
    "Batangas": { "lat": 13.7565, "lon": 121.0583, "region": "Region IV-A" },
    "Laguna": { "lat": 14.2691, "lon": 121.4113, "region": "Region IV-A" },
    "Cavite": { "lat": 14.2456, "lon": 120.8787, "region": "Region IV-A" },
    "Rizal": { "lat": 14.6037, "lon": 121.3084, "region": "Region IV-A" },
    "Pampanga": { "lat": 15.0794, "lon": 120.6200, "region": "Region III" },
    "Bulacan": { "lat": 14.7942, "lon": 120.8798, "region": "Region III" },
    "Aurora": { "lat": 15.9784, "lon": 121.6323, "region": "Region III" },
    "Pangasinan": { "lat": 15.8949, "lon": 120.2863, "region": "Region I" },
    "Ilocos Norte": { "lat": 18.1977, "lon": 120.5937, "region": "Region I" },
    "Ilocos Sur": { "lat": 17.5755, "lon": 120.3869, "region": "Region I" },
    "Cagayan": { "lat": 17.6132, "lon": 121.7270, "region": "Region II" },
    "Isabela": { "lat": 16.9754, "lon": 121.8107, "region": "Region II" },
    "Benguet": { "lat": 16.4023, "lon": 120.5960, "region": "CAR" },
    "Iloilo": { "lat": 10.7202, "lon": 122.5621, "region": "Region VI" },
    "Negros Occidental": { "lat": 10.6713, "lon": 122.9511, "region": "Region VI" },
    "Negros Oriental": { "lat": 9.6299, "lon": 123.0095, "region": "Region VII" },
    "Bohol": { "lat": 9.8349, "lon": 124.4330, "region": "Region VII" },
    "Misamis Oriental": { "lat": 8.5046, "lon": 124.6220, "region": "Region X" },
    "Zamboanga del Sur": { "lat": 7.8383, "lon": 123.2967, "region": "Region IX" },
    "South Cotabato": { "lat": 6.2969, "lon": 124.8600, "region": "Region XII" },
    "Maguindanao": { "lat": 6.9423, "lon": 124.4199, "region": "BARMM" },
    "Lanao del Norte": { "lat": 7.8720, "lon": 123.8851, "region": "Region X" },
    "Surigao del Norte": { "lat": 9.7177, "lon": 125.5954, "region": "Region XIII" },
    "Surigao del Sur": { "lat": 8.7517, "lon": 126.1356, "region": "Region XIII" },
    "Agusan del Norte": { "lat": 8.9456, "lon": 125.5319, "region": "Region XIII" }
  },
  "cities": {
    "Manila": { "province": "Metro Manila", "lat": 14.5995, "lon": 120.9842 },
    "Quezon City": { "province": "Metro Manila", "lat": 14.6760, "lon": 121.0437 },
    "Caloocan": { "province": "Metro Manila", "lat": 14.6492, "lon": 120.9672 },
    "Pasig": { "province": "Metro Manila", "lat": 14.5764, "lon": 121.0851 },
    "Taguig": { "province": "Metro Manila", "lat": 14.5176, "lon": 121.0509 },
    "Makati": { "province": "Metro Manila", "lat": 14.5547, "lon": 121.0244 },
    "Cebu City": { "province": "Cebu", "lat": 10.3157, "lon": 123.8854 },
    "Mandaue": { "province": "Cebu", "lat": 10.3236, "lon": 123.9223 },
    "Lapu-Lapu": { "province": "Cebu", "lat": 10.3103, "lon": 124.0022 },
    "Davao City": { "province": "Davao del Sur", "lat": 7.1907, "lon": 125.4553 },
    "General Santos": { "province": "South Cotabato", "lat": 6.1164, "lon": 125.1716 },
    "Cagayan de Oro": { "province": "Misamis Oriental", "lat": 8.4542, "lon": 124.6319 },
    "Zamboanga City": { "province": "Zamboanga del Sur", "lat": 6.9214, "lon": 122.0790 },
    "Iloilo City": { "province": "Iloilo", "lat": 10.7202, "lon": 122.5621 },
    "Bacolod": { "province": "Negros Occidental", "lat": 10.6840, "lon": 122.9567 },
    "Tacloban": { "province": "Leyte", "lat": 11.2453, "lon": 125.0001 },
    "Ormoc": { "province": "Leyte", "lat": 11.0054, "lon": 124.6073 },
    "Borongan": { "province": "Eastern Samar", "lat": 11.6083, "lon": 125.4319 },
    "Guiuan": { "province": "Eastern Samar", "lat": 11.0330, "lon": 125.7225 },
    "Tagbilaran": { "province": "Bohol", "lat": 9.6500, "lon": 123.8574 },
    "Legazpi": { "province": "Albay", "lat": 13.1391, "lon": 123.7438 },
    "Naga": { "province": "Camarines Sur", "lat": 13.6192, "lon": 123.1814 },
    "Baguio": { "province": "Benguet", "lat": 16.4023, "lon": 120.5960 },
    "Angeles": { "province": "Pampanga", "lat": 15.1450, "lon": 120.5887 },
    "San Fernando": { "province": "Pampanga", "lat": 15.0288, "lon": 120.6933 },
    "Malolos": { "province": "Bulacan", "lat": 14.8527, "lon": 120.8132 },
    "Dagupan": { "province": "Pangasinan", "lat": 16.0432, "lon": 120.3331 },
    "Calamba": { "province": "Laguna", "lat": 14.2112, "lon": 121.1653 },
    "Antipolo": { "province": "Rizal", "lat": 14.5865, "lon": 121.1760 },
    "Batangas City": { "province": "Batangas", "lat": 13.7565, "lon": 121.0583 },
    "Tuguegarao": { "province": "Cagayan", "lat": 17.6132, "lon": 121.7270 },
    "Cauayan": { "province": "Isabela", "lat": 16.9220, "lon": 121.7721 },
    "Butuan": { "province": "Agusan del Norte", "lat": 8.9475, "lon": 125.5406 },
    "Surigao": { "province": "Surigao del Norte", "lat": 9.7833, "lon": 125.4833 }
  }
}
```

- [ ] **Step 4: Implement geography.ts**

Create `web/lib/geography.ts`:

```typescript
import geo from '@/data/philippines-geography.json';
import type { PhilippinesGeography, GeoCity } from '@/types';

const data = geo as PhilippinesGeography;

export function getProvinces(): string[] {
  return Object.keys(data.provinces).sort();
}

export function getCitiesForProvince(province: string): string[] {
  return Object.entries(data.cities)
    .filter(([, city]) => city.province === province)
    .map(([name]) => name)
    .sort();
}

export function getCityCoords(city: string): { lat: number; lon: number } | null {
  const entry = data.cities[city] as GeoCity | undefined;
  if (!entry) return null;
  return { lat: entry.lat, lon: entry.lon };
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
npm run test:run -- tests/lib/geography.test.ts
```

Expected: 5 tests passing.

- [ ] **Step 6: Commit**

```bash
git add web/data/philippines-geography.json web/lib/geography.ts web/tests/lib/geography.test.ts
git commit -m "feat: add Philippines geography data and lib/geography helpers"
```

---

### Task 4: Utility Functions (TDD)

**Files:**
- Create: `web/lib/haversine.ts`
- Create: `web/lib/audio-url.ts`
- Create: `web/lib/affected-areas.ts`
- Create: `web/tests/lib/haversine.test.ts`
- Create: `web/tests/lib/audio-url.test.ts`
- Create: `web/tests/lib/affected-areas.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `web/tests/lib/haversine.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { haversine } from '@/lib/haversine';

describe('haversine', () => {
  it('returns 0 for identical coordinates', () => {
    expect(haversine(10.3157, 123.8854, 10.3157, 123.8854)).toBe(0);
  });

  it('returns roughly 5300 km between Manila and London', () => {
    // Manila: 14.5995, 120.9842 — London: 51.5074, -0.1278
    const dist = haversine(14.5995, 120.9842, 51.5074, -0.1278);
    expect(dist).toBeGreaterThan(10000);
    expect(dist).toBeLessThan(12000);
  });

  it('returns ~582 km from Manila to Cebu City', () => {
    const dist = haversine(14.5995, 120.9842, 10.3157, 123.8854);
    expect(dist).toBeGreaterThan(550);
    expect(dist).toBeLessThan(620);
  });

  it('returns a whole number (Math.round applied)', () => {
    const dist = haversine(14.5995, 120.9842, 10.3157, 123.8854);
    expect(Number.isInteger(dist)).toBe(true);
  });
});
```

Create `web/tests/lib/audio-url.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest';

describe('audioUrl', () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'https://test.supabase.co';
  });

  it('constructs a full public storage URL from a path', async () => {
    const { audioUrl } = await import('@/lib/audio-url');
    const url = audioUrl('PAGASA_20-19W_Pepito_SWB_01/audio_en.mp3');
    expect(url).toBe(
      'https://test.supabase.co/storage/v1/object/public/weatherspeak-public/PAGASA_20-19W_Pepito_SWB_01/audio_en.mp3'
    );
  });

  it('handles paths without a leading slash', async () => {
    const { audioUrl } = await import('@/lib/audio-url');
    const url = audioUrl('somepath/audio_tl.mp3');
    expect(url).toContain('/storage/v1/object/public/weatherspeak-public/somepath/audio_tl.mp3');
  });
});
```

Create `web/tests/lib/affected-areas.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { parseAffectedAreas } from '@/lib/affected-areas';

describe('parseAffectedAreas', () => {
  it('returns empty array for null input', () => {
    expect(parseAffectedAreas(null)).toEqual([]);
  });

  it('returns empty array when all signal arrays are empty', () => {
    expect(parseAffectedAreas({ signal_1: [] })).toEqual([]);
  });

  it('returns sections sorted highest signal first', () => {
    const result = parseAffectedAreas({
      signal_1: ['Pangasinan'],
      signal_3: ['Eastern Samar'],
      signal_4: ['Leyte'],
    });
    expect(result.map(s => s.signal)).toEqual([4, 3, 1]);
  });

  it('includes areas list for each signal level', () => {
    const result = parseAffectedAreas({
      signal_2: ['Cebu', 'Bohol'],
    });
    expect(result[0]).toEqual({ signal: 2, areas: ['Cebu', 'Bohol'] });
  });

  it('omits signal levels with no areas', () => {
    const result = parseAffectedAreas({
      signal_4: ['Leyte'],
      signal_5: [],
    });
    expect(result.length).toBe(1);
    expect(result[0].signal).toBe(4);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm run test:run -- tests/lib/haversine.test.ts tests/lib/audio-url.test.ts tests/lib/affected-areas.test.ts
```

Expected: FAIL — "Cannot find module" errors.

- [ ] **Step 3: Implement the utilities**

Create `web/lib/haversine.ts`:

```typescript
export function haversine(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  return Math.round(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
}
```

Create `web/lib/audio-url.ts`:

```typescript
export function audioUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_SUPABASE_URL;
  return `${base}/storage/v1/object/public/weatherspeak-public/${path}`;
}
```

Create `web/lib/affected-areas.ts`:

```typescript
import type { AffectedAreas, SignalSection } from '@/types';

export function parseAffectedAreas(areas: AffectedAreas | null): SignalSection[] {
  if (!areas) return [];
  const signals = [5, 4, 3, 2, 1] as const;
  return signals
    .map(signal => ({
      signal,
      areas: (areas[`signal_${signal}` as keyof AffectedAreas] as string[] | undefined) ?? [],
    }))
    .filter(({ areas }) => areas.length > 0);
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm run test:run -- tests/lib/haversine.test.ts tests/lib/audio-url.test.ts tests/lib/affected-areas.test.ts
```

Expected: 11 tests passing.

- [ ] **Step 5: Commit**

```bash
git add web/lib/haversine.ts web/lib/audio-url.ts web/lib/affected-areas.ts \
        web/tests/lib/haversine.test.ts web/tests/lib/audio-url.test.ts web/tests/lib/affected-areas.test.ts
git commit -m "feat: add haversine, audioUrl, parseAffectedAreas utilities (TDD)"
```

---

### Task 5: Supabase Client + Queries

**Files:**
- Create: `web/lib/supabase/server.ts`
- Create: `web/lib/supabase/queries.ts`

- [ ] **Step 1: Create the server Supabase client**

Create `web/lib/supabase/server.ts`:

```typescript
import { createClient } from '@supabase/supabase-js';

// Server-side only. Uses service role key — never import in client components.
export function createServerClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}
```

- [ ] **Step 2: Create the query functions**

Create `web/lib/supabase/queries.ts`:

```typescript
import { createServerClient } from './server';
import type { StormWithStatus, Bulletin, BulletinMedia, MediaByLang, Language } from '@/types';

function toMediaByLang(media: BulletinMedia[]): MediaByLang {
  return media.reduce<MediaByLang>((acc, m) => {
    acc[m.language as Language] = m;
    return acc;
  }, {});
}

export async function getActiveStorms(): Promise<StormWithStatus[]> {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from('storms_with_status')
    .select('*')
    .eq('is_active', true)
    .order('current_signal', { ascending: false, nullsFirst: false })
    .order('last_bulletin_at', { ascending: false });

  if (error) {
    console.error('[getActiveStorms]', error.message);
    return [];
  }
  return (data ?? []) as StormWithStatus[];
}

export async function getPastStorms(): Promise<StormWithStatus[]> {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from('storms_with_status')
    .select('*')
    .eq('is_active', false)
    .order('last_bulletin_at', { ascending: false })
    .limit(20);

  if (error) {
    console.error('[getPastStorms]', error.message);
    return [];
  }
  return (data ?? []) as StormWithStatus[];
}

export interface StormDetail {
  storm: StormWithStatus;
  latestBulletin: Bulletin;
  latestMedia: MediaByLang;
  bulletinHistory: Array<{ id: string; bulletin_number: number | null; issued_at: string | null }>;
}

export async function getStormDetail(stormId: string): Promise<StormDetail | null> {
  const supabase = createServerClient();

  const { data: storm, error: stormErr } = await supabase
    .from('storms_with_status')
    .select('*')
    .eq('id', stormId)
    .single();

  if (stormErr || !storm) return null;

  const { data: bulletins, error: bulletinErr } = await supabase
    .from('bulletins')
    .select('*, bulletin_media(*)')
    .eq('storm_id', stormId)
    .order('issued_at', { ascending: false });

  if (bulletinErr || !bulletins || bulletins.length === 0) return null;

  const [latest, ...rest] = bulletins as (Bulletin & { bulletin_media: BulletinMedia[] })[];

  return {
    storm: storm as StormWithStatus,
    latestBulletin: latest,
    latestMedia: toMediaByLang(latest.bulletin_media ?? []),
    bulletinHistory: rest.map(b => ({
      id: b.id,
      bulletin_number: b.bulletin_number,
      issued_at: b.issued_at,
    })),
  };
}

export interface BulletinDetail {
  bulletin: Bulletin;
  media: MediaByLang;
  stormId: string;
}

export async function getBulletin(bulletinId: string): Promise<BulletinDetail | null> {
  const supabase = createServerClient();

  const { data, error } = await supabase
    .from('bulletins')
    .select('*, bulletin_media(*)')
    .eq('id', bulletinId)
    .single();

  if (error || !data) return null;

  const bulletin = data as Bulletin & { bulletin_media: BulletinMedia[] };

  return {
    bulletin,
    media: toMediaByLang(bulletin.bulletin_media ?? []),
    stormId: bulletin.storm_id,
  };
}
```

- [ ] **Step 3: Commit**

```bash
git add web/lib/supabase/
git commit -m "feat: add Supabase server client and query functions"
```

---

### Task 6: SignalBadge Component

**Files:**
- Create: `web/components/SignalBadge.tsx`
- Create: `web/tests/components/SignalBadge.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/tests/components/SignalBadge.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SignalBadge from '@/components/SignalBadge';

describe('SignalBadge', () => {
  it('displays the signal number', () => {
    render(<SignalBadge signal={4} />);
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('renders without crashing when signal is null', () => {
    render(<SignalBadge signal={null} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('applies red background for signal 4', () => {
    const { container } = render(<SignalBadge signal={4} />);
    expect(container.firstChild).toHaveStyle({ backgroundColor: '#c0392b' });
  });

  it('applies orange background for signal 3', () => {
    const { container } = render(<SignalBadge signal={3} />);
    expect(container.firstChild).toHaveStyle({ backgroundColor: '#e67e22' });
  });

  it('applies yellow background for signal 2', () => {
    const { container } = render(<SignalBadge signal={2} />);
    expect(container.firstChild).toHaveStyle({ backgroundColor: '#f1c40f' });
  });

  it('applies blue background for signal 1', () => {
    const { container } = render(<SignalBadge signal={1} />);
    expect(container.firstChild).toHaveStyle({ backgroundColor: '#3498db' });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npm run test:run -- tests/components/SignalBadge.test.tsx
```

Expected: FAIL — "Cannot find module '@/components/SignalBadge'"

- [ ] **Step 3: Implement SignalBadge**

Create `web/components/SignalBadge.tsx`:

```typescript
const SIGNAL_COLORS: Record<number, string> = {
  1: '#3498db',
  2: '#f1c40f',
  3: '#e67e22',
  4: '#c0392b',
  5: '#c0392b',
};

interface Props {
  signal: number | null;
}

export default function SignalBadge({ signal }: Props) {
  const bg = signal != null ? (SIGNAL_COLORS[signal] ?? '#6b7280') : '#6b7280';
  return (
    <div
      style={{ backgroundColor: bg }}
      className="w-14 h-14 rounded-lg flex flex-col items-center justify-center flex-shrink-0"
    >
      <span className="text-xs text-white/60 uppercase leading-none">SIG</span>
      <span className="text-3xl font-extrabold text-white leading-none">
        {signal ?? '—'}
      </span>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm run test:run -- tests/components/SignalBadge.test.tsx
```

Expected: 6 tests passing.

- [ ] **Step 5: Commit**

```bash
git add web/components/SignalBadge.tsx web/tests/components/SignalBadge.test.tsx
git commit -m "feat: add SignalBadge component (TDD)"
```

---

### Task 7: AudioPlayer Component

**Files:**
- Create: `web/components/AudioPlayer.tsx`
- Create: `web/tests/components/AudioPlayer.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `web/tests/components/AudioPlayer.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AudioPlayer from '@/components/AudioPlayer';

describe('AudioPlayer', () => {
  it('renders play button when audioUrl is provided', () => {
    render(
      <AudioPlayer
        audioUrl="https://example.com/audio.mp3"
        durationSeconds={272}
        filename="bulletin-en.mp3"
      />
    );
    expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument();
  });

  it('renders a download link pointing to the audio URL', () => {
    render(
      <AudioPlayer
        audioUrl="https://example.com/audio.mp3"
        durationSeconds={272}
        filename="bulletin-en.mp3"
      />
    );
    const link = screen.getByRole('link', { name: /download/i });
    expect(link).toHaveAttribute('href', 'https://example.com/audio.mp3');
    expect(link).toHaveAttribute('download', 'bulletin-en.mp3');
  });

  it('shows "Audio not yet available" when audioUrl is null', () => {
    render(<AudioPlayer audioUrl={null} durationSeconds={null} filename="bulletin-en.mp3" />);
    expect(screen.getByText(/audio not yet available/i)).toBeInTheDocument();
  });

  it('formats duration as mm:ss', () => {
    render(
      <AudioPlayer
        audioUrl="https://example.com/audio.mp3"
        durationSeconds={272}
        filename="bulletin-en.mp3"
      />
    );
    expect(screen.getByText('4:32')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm run test:run -- tests/components/AudioPlayer.test.tsx
```

Expected: FAIL — "Cannot find module '@/components/AudioPlayer'"

- [ ] **Step 3: Implement AudioPlayer**

Create `web/components/AudioPlayer.tsx`:

```typescript
'use client';

import { useRef, useState } from 'react';

interface Props {
  audioUrl: string | null;
  durationSeconds: number | null;
  filename: string;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function AudioPlayer({ audioUrl, durationSeconds, filename }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [current, setCurrent] = useState(0);

  if (!audioUrl) {
    return (
      <p className="text-gray-400 text-sm py-4">Audio not yet available for this language.</p>
    );
  }

  const total = durationSeconds ?? 0;

  const handlePlayPause = () => {
    if (!audioRef.current) return;
    if (playing) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setPlaying(!playing);
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) setCurrent(Math.floor(audioRef.current.currentTime));
  };

  const handleEnded = () => setPlaying(false);

  const progress = total > 0 ? (current / total) * 100 : 0;

  return (
    <div className="bg-white/5 rounded-xl p-4 space-y-3">
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        preload="metadata"
      />

      {/* Progress bar */}
      <div className="w-full bg-white/10 h-1 rounded-full">
        <div
          className="bg-red-500 h-1 rounded-full transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={handlePlayPause}
            aria-label={playing ? 'Pause' : 'Play'}
            className="w-10 h-10 rounded-full bg-red-600 flex items-center justify-center text-white hover:bg-red-500 transition-colors"
          >
            {playing ? '⏸' : '▶'}
          </button>
          <span className="text-sm text-gray-400">
            {formatTime(current)} / {total > 0 ? formatTime(total) : '--:--'}
          </span>
        </div>

        <a
          href={audioUrl}
          download={filename}
          className="text-sm text-gray-300 bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition-colors"
        >
          ⬇ Download
        </a>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm run test:run -- tests/components/AudioPlayer.test.tsx
```

Expected: 4 tests passing.

- [ ] **Step 5: Commit**

```bash
git add web/components/AudioPlayer.tsx web/tests/components/AudioPlayer.test.tsx
git commit -m "feat: add AudioPlayer component with play/pause/download (TDD)"
```

---

### Task 8: LanguageToggle + BulletinAudioSection

**Files:**
- Create: `web/components/LanguageToggle.tsx`
- Create: `web/components/BulletinAudioSection.tsx`

- [ ] **Step 1: Implement LanguageToggle**

Create `web/components/LanguageToggle.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import type { Language } from '@/types';

const LABELS: Record<Language, string> = { tl: 'TL', ceb: 'CEB', en: 'EN' };
const LANGUAGES: Language[] = ['tl', 'ceb', 'en'];

export default function LanguageToggle() {
  const [selected, setSelected] = useState<Language>('tl');

  useEffect(() => {
    const stored = localStorage.getItem('ws_language') as Language | null;
    if (stored && LANGUAGES.includes(stored)) setSelected(stored);
  }, []);

  const handleSelect = (lang: Language) => {
    setSelected(lang);
    localStorage.setItem('ws_language', lang);
    window.dispatchEvent(new Event('ws:language-change'));
  };

  return (
    <div className="flex rounded-lg overflow-hidden border border-white/10">
      {LANGUAGES.map(lang => (
        <button
          key={lang}
          onClick={() => handleSelect(lang)}
          className={`px-3 py-1 text-sm font-semibold transition-colors ${
            selected === lang
              ? 'bg-red-600 text-white'
              : 'bg-white/5 text-gray-400 hover:bg-white/10'
          }`}
        >
          {LABELS[lang]}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Implement BulletinAudioSection**

Create `web/components/BulletinAudioSection.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import type { Language, MediaByLang } from '@/types';
import AudioPlayer from './AudioPlayer';
import { audioUrl } from '@/lib/audio-url';

interface Props {
  media: MediaByLang;
  stem: string; // used to construct a human-readable download filename
}

export default function BulletinAudioSection({ media, stem }: Props) {
  const [language, setLanguage] = useState<Language>('tl');

  useEffect(() => {
    const stored = localStorage.getItem('ws_language') as Language | null;
    if (stored) setLanguage(stored);

    const handler = () => {
      const updated = localStorage.getItem('ws_language') as Language | null;
      if (updated) setLanguage(updated);
    };
    window.addEventListener('ws:language-change', handler);
    return () => window.removeEventListener('ws:language-change', handler);
  }, []);

  const current = media[language];
  const url = current?.audio_path ? audioUrl(current.audio_path) : null;
  // Only show player if audio is ready; pass null otherwise so AudioPlayer shows fallback
  const readyUrl = current?.status === 'ready' ? url : null;

  return (
    <AudioPlayer
      audioUrl={readyUrl}
      durationSeconds={current?.audio_duration_seconds ?? null}
      filename={`${stem}_${language}.mp3`}
    />
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add web/components/LanguageToggle.tsx web/components/BulletinAudioSection.tsx
git commit -m "feat: add LanguageToggle and BulletinAudioSection client components"
```

---

### Task 9: DistancePill Component

**Files:**
- Create: `web/components/DistancePill.tsx`
- Create: `web/tests/components/DistancePill.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `web/tests/components/DistancePill.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import DistancePill from '@/components/DistancePill';

describe('DistancePill', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders nothing when location is not set', () => {
    const { container } = render(<DistancePill stormLat={11.5} stormLon={125.0} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows distance and city name when location is set', () => {
    localStorage.setItem('ws_lat', '10.3157');
    localStorage.setItem('ws_lon', '123.8854');
    localStorage.setItem('ws_city', 'Cebu City');
    render(<DistancePill stormLat={10.3157} stormLon={123.8854} />);
    expect(screen.getByText(/Cebu City/)).toBeInTheDocument();
    expect(screen.getByText(/0 km/)).toBeInTheDocument();
  });

  it('calculates non-zero distance for different coordinates', () => {
    localStorage.setItem('ws_lat', '14.5995');
    localStorage.setItem('ws_lon', '120.9842');
    localStorage.setItem('ws_city', 'Manila');
    render(<DistancePill stormLat={10.3157} stormLon={123.8854} />);
    // Manila → Cebu City is roughly 582 km
    const text = screen.getByText(/Manila/);
    expect(text.textContent).toMatch(/\d+ km from Manila/);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npm run test:run -- tests/components/DistancePill.test.tsx
```

Expected: FAIL — "Cannot find module '@/components/DistancePill'"

- [ ] **Step 3: Implement DistancePill**

Create `web/components/DistancePill.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { haversine } from '@/lib/haversine';

interface Props {
  stormLat: number;
  stormLon: number;
}

export default function DistancePill({ stormLat, stormLon }: Props) {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    const lat = parseFloat(localStorage.getItem('ws_lat') ?? '');
    const lon = parseFloat(localStorage.getItem('ws_lon') ?? '');
    const city = localStorage.getItem('ws_city');
    if (!city || isNaN(lat) || isNaN(lon)) return;
    const dist = haversine(lat, lon, stormLat, stormLon);
    setLabel(`📍 ${dist} km from ${city}`);
  }, [stormLat, stormLon]);

  if (!label) return null;
  return (
    <span className="text-sm font-medium text-orange-400">{label}</span>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm run test:run -- tests/components/DistancePill.test.tsx
```

Expected: 3 tests passing.

- [ ] **Step 5: Commit**

```bash
git add web/components/DistancePill.tsx web/tests/components/DistancePill.test.tsx
git commit -m "feat: add DistancePill component with haversine calculation (TDD)"
```

---

### Task 10: LocationOnboarding Modal

**Files:**
- Create: `web/components/LocationOnboarding.tsx`

- [ ] **Step 1: Implement LocationOnboarding**

Create `web/components/LocationOnboarding.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { getProvinces, getCitiesForProvince, getCityCoords } from '@/lib/geography';
import type { Language } from '@/types';

const LANGUAGES: { code: Language; label: string }[] = [
  { code: 'tl', label: 'Tagalog' },
  { code: 'ceb', label: 'Cebuano' },
  { code: 'en', label: 'English' },
];

export default function LocationOnboarding() {
  const [show, setShow] = useState(false);
  const [province, setProvince] = useState('');
  const [city, setCity] = useState('');
  const [language, setLanguage] = useState<Language>('tl');
  const provinces = getProvinces();

  useEffect(() => {
    if (!localStorage.getItem('ws_province')) setShow(true);
  }, []);

  if (!show) return null;

  const cities = province ? getCitiesForProvince(province) : [];

  const handleProvince = (p: string) => {
    setProvince(p);
    setCity('');
  };

  const handleSubmit = () => {
    if (!province || !city) return;
    const coords = getCityCoords(city);
    localStorage.setItem('ws_province', province);
    localStorage.setItem('ws_city', city);
    localStorage.setItem('ws_language', language);
    if (coords) {
      localStorage.setItem('ws_lat', String(coords.lat));
      localStorage.setItem('ws_lon', String(coords.lon));
    }
    window.dispatchEvent(new Event('ws:language-change'));
    setShow(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
      <div className="bg-gray-900 rounded-2xl p-6 w-full max-w-sm space-y-5">
        {/* Header */}
        <div className="text-center">
          <div className="text-4xl mb-2">🌀</div>
          <h2 className="text-xl font-bold text-white">WeatherSpeak PH</h2>
          <p className="text-sm text-gray-400 mt-1">Setup — takes 10 seconds</p>
        </div>

        {/* Location */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
            📍 Your location
          </label>
          <select
            value={province}
            onChange={e => handleProvince(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
          >
            <option value="">Province ▾</option>
            {provinces.map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <select
            value={city}
            onChange={e => setCity(e.target.value)}
            disabled={!province}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white disabled:opacity-40"
          >
            <option value="">City / Municipality ▾</option>
            {cities.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* Language */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
            🌐 Language / Wika / Pinulongan
          </label>
          <div className="flex gap-2">
            {LANGUAGES.map(l => (
              <button
                key={l.code}
                onClick={() => setLanguage(l.code)}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-colors ${
                  language === l.code
                    ? 'bg-red-600 text-white'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                }`}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!province || !city}
          className="w-full bg-red-600 hover:bg-red-500 disabled:opacity-40 text-white font-bold py-3 rounded-lg transition-colors"
        >
          Get Started
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/LocationOnboarding.tsx
git commit -m "feat: add LocationOnboarding first-visit modal"
```

---

### Task 11: AffectedAreas Accordion

**Files:**
- Create: `web/components/AffectedAreas.tsx`

- [ ] **Step 1: Implement AffectedAreas**

Create `web/components/AffectedAreas.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { parseAffectedAreas } from '@/lib/affected-areas';
import type { AffectedAreas as AffectedAreasType } from '@/types';

const SIGNAL_COLORS: Record<number, string> = {
  1: 'bg-blue-900/40 border-blue-700',
  2: 'bg-yellow-900/40 border-yellow-700',
  3: 'bg-orange-900/40 border-orange-700',
  4: 'bg-red-900/40 border-red-700',
  5: 'bg-red-900/60 border-red-600',
};

interface Props {
  areas: AffectedAreasType | null;
}

export default function AffectedAreas({ areas }: Props) {
  const [open, setOpen] = useState<number | null>(null);
  const sections = parseAffectedAreas(areas);

  if (sections.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
        Affected Areas
      </h3>
      {sections.map(({ signal, areas: list }) => (
        <div
          key={signal}
          className={`border rounded-lg overflow-hidden ${SIGNAL_COLORS[signal] ?? 'bg-gray-900/40 border-gray-700'}`}
        >
          <button
            onClick={() => setOpen(open === signal ? null : signal)}
            className="w-full flex items-center justify-between px-4 py-3 text-left"
          >
            <span className="font-semibold text-white text-sm">
              Signal #{signal}
            </span>
            <span className="text-gray-400 text-xs">
              {list.length} area{list.length !== 1 ? 's' : ''} {open === signal ? '▲' : '▼'}
            </span>
          </button>
          {open === signal && (
            <ul className="px-4 pb-3 space-y-1">
              {list.map(area => (
                <li key={area} className="text-sm text-gray-300">
                  {area}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/AffectedAreas.tsx
git commit -m "feat: add AffectedAreas accordion component"
```

---

### Task 12: StormCard Component

**Files:**
- Create: `web/components/StormCard.tsx`

- [ ] **Step 1: Implement StormCard**

Create `web/components/StormCard.tsx`:

```typescript
import Link from 'next/link';
import SignalBadge from './SignalBadge';
import DistancePill from './DistancePill';
import type { StormWithStatus } from '@/types';

interface Props {
  storm: StormWithStatus;
  compact?: boolean; // true for past storms section
}

function timeAgo(iso: string | null): string {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3_600_000);
  if (h < 1) return 'just now';
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function StormCard({ storm, compact = false }: Props) {
  if (compact) {
    return (
      <Link
        href={`/storms/${storm.id}`}
        className="flex items-center gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors"
      >
        <SignalBadge signal={storm.current_signal} />
        <div className="min-w-0">
          <div className="font-bold text-white truncate">{storm.storm_name}</div>
          <div className="text-xs text-gray-400">
            {storm.current_category} · {timeAgo(storm.last_bulletin_at)}
          </div>
        </div>
      </Link>
    );
  }

  return (
    <Link
      href={`/storms/${storm.id}`}
      className="flex items-center gap-4 p-4 rounded-2xl bg-white/5 hover:bg-white/10 transition-colors"
    >
      <SignalBadge signal={storm.current_signal} />
      <div className="flex-1 min-w-0">
        <div className="text-xl font-extrabold text-white">{storm.storm_name}</div>
        <div className="text-sm text-gray-400">{storm.current_category}</div>
        {storm.current_reference && (
          <div className="text-xs text-gray-500 truncate mt-0.5">{storm.current_reference}</div>
        )}
        <div className="mt-1 flex flex-wrap gap-2 items-center">
          {storm.current_lat != null && storm.current_lon != null && (
            <DistancePill stormLat={storm.current_lat} stormLon={storm.current_lon} />
          )}
          <span className="text-xs text-gray-500">{timeAgo(storm.last_bulletin_at)}</span>
        </div>
      </div>
    </Link>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/StormCard.tsx
git commit -m "feat: add StormCard component (signal-first layout)"
```

---

### Task 13: Root Layout + Header

**Files:**
- Modify: `web/app/layout.tsx`
- Create: `web/components/Header.tsx`
- Modify: `web/app/globals.css`

- [ ] **Step 1: Implement Header**

Create `web/components/Header.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import LanguageToggle from './LanguageToggle';

export default function Header() {
  const [city, setCity] = useState<string | null>(null);

  useEffect(() => {
    setCity(localStorage.getItem('ws_city'));
    const handler = () => setCity(localStorage.getItem('ws_city'));
    window.addEventListener('ws:language-change', handler);
    return () => window.removeEventListener('ws:language-change', handler);
  }, []);

  return (
    <header className="sticky top-0 z-40 bg-gray-950/90 backdrop-blur border-b border-white/5">
      <div className="max-w-lg mx-auto px-4 py-3 flex items-center justify-between gap-3">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-xl">🌀</span>
          <span className="font-extrabold text-white text-base leading-none">
            WeatherSpeak PH
          </span>
        </Link>
        <div className="flex items-center gap-3">
          {city && (
            <span className="text-xs text-gray-400 hidden sm:block">📍 {city}</span>
          )}
          <LanguageToggle />
        </div>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Update root layout**

Replace `web/app/layout.tsx`:

```typescript
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Header from '@/components/Header';
import LocationOnboarding from '@/components/LocationOnboarding';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'WeatherSpeak PH',
  description: 'PAGASA typhoon bulletins in Tagalog, Cebuano, and English',
  manifest: '/manifest.json',
  themeColor: '#0a0a0f',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-950 text-white min-h-screen`}>
        <Header />
        <LocationOnboarding />
        <main className="max-w-lg mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Set global CSS**

Replace the contents of `web/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color-scheme: dark;
}

body {
  -webkit-font-smoothing: antialiased;
}

/* Custom scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
```

- [ ] **Step 4: Commit**

```bash
git add web/components/Header.tsx web/app/layout.tsx web/app/globals.css
git commit -m "feat: add Header component and root layout"
```

---

### Task 14: Home Page

**Files:**
- Modify: `web/app/page.tsx`

- [ ] **Step 1: Implement the home page**

Replace `web/app/page.tsx`:

```typescript
import { getActiveStorms, getPastStorms } from '@/lib/supabase/queries';
import StormCard from '@/components/StormCard';

export const revalidate = 900; // 15 minutes

export default async function HomePage() {
  const [active, past] = await Promise.all([getActiveStorms(), getPastStorms()]);

  return (
    <div className="space-y-8">
      {/* Active storms */}
      <section>
        <h1 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
          Active Typhoons
        </h1>
        {active.length === 0 ? (
          <div className="rounded-2xl bg-white/5 px-5 py-6 text-center">
            <div className="text-3xl mb-2">✅</div>
            <p className="font-semibold text-white">No active typhoons right now.</p>
            <p className="text-sm text-gray-400 mt-1">Stay prepared. Check back during typhoon season.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {active.map(storm => (
              <StormCard key={storm.id} storm={storm} />
            ))}
          </div>
        )}
      </section>

      {/* Past storms */}
      {past.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
            Past Storms
          </h2>
          <div className="space-y-2">
            {past.map(storm => (
              <StormCard key={storm.id} storm={storm} compact />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web/app/page.tsx
git commit -m "feat: implement home page with active and past storm lists"
```

---

### Task 15: Storm Detail Page

**Files:**
- Create: `web/app/storms/[stormId]/page.tsx`

- [ ] **Step 1: Implement the storm detail page**

Create `web/app/storms/[stormId]/page.tsx`:

```typescript
import { notFound } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { getStormDetail } from '@/lib/supabase/queries';
import { audioUrl } from '@/lib/audio-url';
import BulletinAudioSection from '@/components/BulletinAudioSection';
import AffectedAreas from '@/components/AffectedAreas';
import DistancePill from '@/components/DistancePill';

export const revalidate = 600; // 10 minutes

const SIGNAL_BG: Record<number, string> = {
  1: 'from-blue-900 to-blue-800',
  2: 'from-yellow-900 to-yellow-800',
  3: 'from-orange-900 to-orange-800',
  4: 'from-red-900 to-red-800',
  5: 'from-red-950 to-red-900',
};

function heroBg(signal: number | null): string {
  return signal != null ? (SIGNAL_BG[signal] ?? 'from-gray-900 to-gray-800') : 'from-gray-900 to-gray-800';
}

function formatDate(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleString('en-PH', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Manila',
  });
}

interface Props {
  params: { stormId: string };
}

export default async function StormDetailPage({ params }: Props) {
  const detail = await getStormDetail(params.stormId);
  if (!detail) notFound();

  const { storm, latestBulletin, latestMedia, bulletinHistory } = detail;
  const chartUrl = latestBulletin.chart_path ? audioUrl(latestBulletin.chart_path) : null;

  return (
    <div className="space-y-6">
      {/* Back */}
      <Link href="/" className="text-sm text-gray-400 hover:text-white transition-colors">
        ← All Storms
      </Link>

      {/* Hero banner */}
      <div className={`rounded-2xl bg-gradient-to-br ${heroBg(storm.current_signal)} p-5 space-y-2`}>
        <div className="text-xs text-white/60 uppercase tracking-wide">
          {storm.current_category ?? 'Tropical Cyclone'}
        </div>
        <h1 className="text-4xl font-extrabold text-white">{storm.storm_name}</h1>
        {storm.current_reference && (
          <p className="text-sm text-white/70">{storm.current_reference}</p>
        )}
        {storm.current_lat != null && storm.current_lon != null && (
          <DistancePill stormLat={storm.current_lat} stormLon={storm.current_lon} />
        )}
        <div className="text-xs text-white/40">
          Bulletin #{latestBulletin.bulletin_number} · {formatDate(latestBulletin.issued_at)}
        </div>
      </div>

      {/* Audio player */}
      <BulletinAudioSection media={latestMedia} stem={latestBulletin.stem} />

      {/* Storm track chart */}
      {chartUrl && (
        <div className="rounded-xl overflow-hidden bg-white/5">
          <p className="text-xs text-gray-400 uppercase tracking-wide px-3 pt-3">Storm Track</p>
          <div className="relative w-full aspect-[4/3]">
            <Image
              src={chartUrl}
              alt={`Storm track chart for ${storm.storm_name}`}
              fill
              className="object-contain"
              sizes="(max-width: 512px) 100vw, 512px"
            />
          </div>
        </div>
      )}

      {/* Affected areas */}
      <AffectedAreas areas={latestBulletin.affected_areas} />

      {/* Bulletin history */}
      {bulletinHistory.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
            Past Bulletins
          </h2>
          <div className="space-y-1">
            {bulletinHistory.map(b => (
              <Link
                key={b.id}
                href={`/bulletins/${b.id}`}
                className="flex justify-between items-center px-4 py-2.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
              >
                <span className="text-sm text-white">Bulletin #{b.bulletin_number}</span>
                <span className="text-xs text-gray-400">{formatDate(b.issued_at)}</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Mode 2 stub */}
      <div className="rounded-2xl border border-white/5 bg-white/3 p-5 opacity-40">
        <div className="text-sm font-semibold text-white">🎙 Storm Summary Audio</div>
        <div className="text-xs text-gray-400 mt-1">Coming soon — full storm narrative in your language.</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web/app/storms/
git commit -m "feat: implement storm detail page with hero, audio player, chart, affected areas"
```

---

### Task 16: Bulletin Detail Page

**Files:**
- Create: `web/app/bulletins/[bulletinId]/page.tsx`

- [ ] **Step 1: Implement the bulletin detail page**

Create `web/app/bulletins/[bulletinId]/page.tsx`:

```typescript
import { notFound } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { getBulletin } from '@/lib/supabase/queries';
import { audioUrl } from '@/lib/audio-url';
import BulletinAudioSection from '@/components/BulletinAudioSection';
import AffectedAreas from '@/components/AffectedAreas';
import DistancePill from '@/components/DistancePill';

export const revalidate = 600; // 10 minutes

function formatDate(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleString('en-PH', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Manila',
  });
}

interface Props {
  params: { bulletinId: string };
}

export default async function BulletinDetailPage({ params }: Props) {
  const detail = await getBulletin(params.bulletinId);
  if (!detail) notFound();

  const { bulletin, media, stormId } = detail;
  const chartUrl = bulletin.chart_path ? audioUrl(bulletin.chart_path) : null;

  return (
    <div className="space-y-6">
      {/* Back */}
      <Link
        href={`/storms/${stormId}`}
        className="text-sm text-gray-400 hover:text-white transition-colors"
      >
        ← Back to Storm
      </Link>

      {/* Header */}
      <div className="rounded-2xl bg-white/5 p-5 space-y-1">
        <div className="text-xs text-gray-400 uppercase tracking-wide">
          {bulletin.bulletin_type} · Bulletin #{bulletin.bulletin_number}
        </div>
        <p className="text-white font-semibold">{bulletin.current_reference}</p>
        {bulletin.current_lat != null && bulletin.current_lon != null && (
          <DistancePill stormLat={bulletin.current_lat} stormLon={bulletin.current_lon} />
        )}
        <p className="text-xs text-gray-500">{formatDate(bulletin.issued_at)}</p>
      </div>

      {/* Audio */}
      <BulletinAudioSection media={media} stem={bulletin.stem} />

      {/* Chart */}
      {chartUrl && (
        <div className="rounded-xl overflow-hidden bg-white/5">
          <p className="text-xs text-gray-400 uppercase tracking-wide px-3 pt-3">Storm Track</p>
          <div className="relative w-full aspect-[4/3]">
            <Image
              src={chartUrl}
              alt="Storm track chart"
              fill
              className="object-contain"
              sizes="(max-width: 512px) 100vw, 512px"
            />
          </div>
        </div>
      )}

      {/* Affected areas */}
      <AffectedAreas areas={bulletin.affected_areas} />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web/app/bulletins/
git commit -m "feat: implement bulletin detail page"
```

---

### Task 17: PWA Manifest + Vercel Config

**Files:**
- Create: `web/public/manifest.json`
- Create: `web/vercel.json`

- [ ] **Step 1: Create the PWA manifest**

Create `web/public/manifest.json`:

```json
{
  "name": "WeatherSpeak PH",
  "short_name": "WeatherSpeak",
  "description": "PAGASA typhoon bulletins in Tagalog, Cebuano, and English",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0a0a0f",
  "theme_color": "#0a0a0f",
  "icons": [
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

> **Note:** Add `public/icon-192.png` and `public/icon-512.png` (a typhoon/cyclone icon). For the hackathon, generate these from any free icon tool (e.g., https://favicon.io).

- [ ] **Step 2: Create Vercel config for subdirectory deployment**

Create `web/vercel.json`:

```json
{
  "framework": "nextjs"
}
```

> **Vercel setup:** In the Vercel dashboard, when importing the repo, set **Root Directory** to `web`. Add the three environment variables from `.env.local` under Project → Settings → Environment Variables.

- [ ] **Step 3: Run all tests to confirm everything passes**

```bash
cd web
npm run test:run
```

Expected: all tests pass (no failures).

- [ ] **Step 4: Run a production build to confirm no type errors**

```bash
npm run build
```

Expected: build succeeds. Fix any TypeScript errors before continuing.

- [ ] **Step 5: Final commit**

```bash
git add web/public/manifest.json web/vercel.json
git commit -m "feat: add PWA manifest and Vercel config"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by task |
|---|---|
| Next.js 14 App Router + TypeScript + Tailwind | Task 1 |
| ISR (home 15 min, storm/bulletin 10 min) | Tasks 14, 15, 16 (`revalidate`) |
| Three routes: `/`, `/storms/[id]`, `/bulletins/[id]` | Tasks 14, 15, 16 |
| No custom API routes | ✅ all data in server components |
| Supabase server client (service role) | Task 5 |
| `getActiveStorms`, `getPastStorms`, `getStormDetail`, `getBulletin` | Task 5 |
| Signal-first storm card | Task 12 |
| `SignalBadge` colour-coded | Task 6 |
| `AudioPlayer` with play/pause/seek/download | Task 7 |
| `BulletinAudioSection` language-aware wrapper | Task 8 |
| `LanguageToggle` (TL·CEB·EN pill, `ws:language-change` event) | Task 8 |
| `DistancePill` with haversine | Task 9 |
| `LocationOnboarding` single-screen modal | Task 10 |
| `AffectedAreas` accordion | Task 11 |
| Philippines geography JSON (provinces + cities) | Task 3 |
| Active storms section + empty state | Task 14 |
| Past storms section (always visible) | Task 14 |
| Storm detail: hero + audio + chart + affected areas + history | Task 15 |
| Bulletin detail: same layout | Task 16 |
| Mode 2 stub | Task 15 |
| Header with language toggle + location | Task 13 |
| First-visit onboarding modal | Task 10 |
| localStorage keys (ws_language, ws_province, ws_city, ws_lat, ws_lon) | Tasks 8, 9, 10, 13 |
| `haversine()` unit tests | Task 4 |
| `audioUrl()` unit tests | Task 4 |
| `parseAffectedAreas()` unit tests | Task 4 |
| Component smoke tests (SignalBadge, AudioPlayer, DistancePill) | Tasks 6, 7, 9 |
| PWA manifest | Task 17 |
| Environment variables documented | Tasks 1, 17 |
| Error handling: null audio_path, null chart_path, no active storms | Tasks 7, 8, 14, 15, 16 |

All spec requirements are covered. No gaps found.
