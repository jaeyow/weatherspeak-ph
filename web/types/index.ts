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
