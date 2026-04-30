import type { Language } from '@/types';

export type TranslationKey =
  | 'active_typhoons'
  | 'past_storms'
  | 'no_active_typhoons'
  | 'stay_prepared'
  | 'affected_areas'
  | 'storm_track'
  | 'past_bulletins'
  | 'storm_summary_audio'
  | 'coming_soon'
  | 'audio_not_available'
  | 'download'
  | 'all_storms'
  | 'back_to_storm'
  | 'area'
  | 'areas'
  | 'setup_subtitle'
  | 'your_location'
  | 'get_started'
  | 'read_bulletin'
  | 'tap_to_hear';

export const translations: Record<Language, Record<TranslationKey, string>> = {
  en: {
    active_typhoons:     'Active Typhoons',
    past_storms:         'Past Storms',
    no_active_typhoons:  'No active typhoons right now.',
    stay_prepared:       'Stay prepared. Check back during typhoon season.',
    affected_areas:      'Affected Areas',
    storm_track:         'Storm Track',
    past_bulletins:      'Past Bulletins',
    storm_summary_audio: 'Storm Summary Audio',
    coming_soon:         'Coming soon — full storm narrative in your language.',
    audio_not_available: 'Audio not yet available for this language.',
    download:            'Download',
    all_storms:          '← All Storms',
    back_to_storm:       '← Back to Storm',
    area:                'area',
    areas:               'areas',
    setup_subtitle:      'Setup — takes 10 seconds',
    your_location:       'Your location',
    get_started:         'Get Started',
    read_bulletin:       'Read bulletin',
    tap_to_hear:         'Tap ▶ to hear this bulletin in',
  },
  tl: {
    active_typhoons:     'Mga Aktibong Bagyo',
    past_storms:         'Mga Nakaraang Bagyo',
    no_active_typhoons:  'Walang aktibong bagyo ngayon.',
    stay_prepared:       'Manatiling handa. Bumalik tuwing panahon ng bagyo.',
    affected_areas:      'Mga Apektadong Lugar',
    storm_track:         'Landas ng Bagyo',
    past_bulletins:      'Mga Nakaraang Bullettin',
    storm_summary_audio: 'Audio ng Buod ng Bagyo',
    coming_soon:         'Malapit na — buong kwento ng bagyo sa inyong wika.',
    audio_not_available: 'Hindi pa available ang audio para sa wikang ito.',
    download:            'I-download',
    all_storms:          '← Lahat ng Bagyo',
    back_to_storm:       '← Bumalik sa Bagyo',
    area:                'lugar',
    areas:               'mga lugar',
    setup_subtitle:      'Setup — 10 segundo lang',
    your_location:       'Inyong lokasyon',
    get_started:         'Magsimula',
    read_bulletin:       'Basahin ang bullettin',
    tap_to_hear:         'I-tap ang ▶ para marinig ang bulletin sa',
  },
  ceb: {
    active_typhoons:     'Mga Aktibong Bagyo',
    past_storms:         'Mga Miaging Bagyo',
    no_active_typhoons:  'Walay aktibong bagyo karon.',
    stay_prepared:       'Pabilin nga andam. Balik sa panahon sa bagyo.',
    affected_areas:      'Mga Apektadong Dapit',
    storm_track:         'Dalan sa Bagyo',
    past_bulletins:      'Mga Miaging Bullettin',
    storm_summary_audio: 'Audio sa Resumo sa Bagyo',
    coming_soon:         'Moabot na — tibuok sugilanon sa bagyo sa imong pinulongan.',
    audio_not_available: 'Dili pa available ang audio alang niining pinulongan.',
    download:            'I-download',
    all_storms:          '← Tanan nga Bagyo',
    back_to_storm:       '← Balik sa Bagyo',
    area:                'dapit',
    areas:               'mga dapit',
    setup_subtitle:      'Setup — 10 segundo ra',
    your_location:       'Imong lokasyon',
    get_started:         'Sugdan',
    read_bulletin:       'Basaha ang bullettin',
    tap_to_hear:         'I-tap ang ▶ aron madungog ang bulletin sa',
  },
};

export function t(lang: Language, key: TranslationKey): string {
  return translations[lang]?.[key] ?? translations.en[key];
}
