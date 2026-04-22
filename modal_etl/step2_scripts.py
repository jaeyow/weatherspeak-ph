import subprocess
import time
from pathlib import Path

import requests

from modal_etl.app import app, ollama_image, OLLAMA_MOUNTS, output_volume
from modal_etl.config import OLLAMA_MODELS_PATH, OUTPUT_PATH, GEMMA_MODEL, LANGUAGES
from modal_etl.phonetics import apply_phonetics

OLLAMA_URL = "http://localhost:11434"
OLLAMA_TIMEOUT = 300  # seconds per language prompt

# ---------------------------------------------------------------------------
# Radio script prompts (system + user template per language)
# ---------------------------------------------------------------------------

_RADIO_PROMPTS = {
    "en": {
        "system": (
            "You are converting a PAGASA typhoon bulletin into a short weather announcement in English "
            "that will be displayed on a website and read aloud as audio.\n\n"
            "PURPOSE: This will be read by Filipinos who may not understand technical English — "
            "farmers, fisherfolk, and rural communities who need to know if they are in danger and what to do. "
            "Every word must earn its place. There is no room for anything that does not help them act.\n\n"
            "PRIORITY ORDER — pack these in, in this order, within 200 words:\n"
            "  1. Storm name and current category (what is it)\n"
            "  2. Where it is now and where it is headed (location + track)\n"
            "  3. Which areas are affected and at what Signal level (who is in danger)\n"
            "  4. What people must do — evacuate, stay indoors, avoid the coast (action)\n"
            "  5. When the next update is (so they know to listen again)\n\n"
            "STYLE:\n"
            "- Write as if explaining to a neighbour — conversational, simple, direct\n"
            "- No broadcaster language, no formal sign-offs, no station IDs\n"
            "- Short sentences. Common words. Cut anything that does not add critical information.\n"
            "- Use digits for numbers (e.g. '25 kilometres per hour', 'Signal 2')\n"
            "- Write place names naturally as they are spelled (e.g. Catanduanes, Visayas, Mindanao)\n"
            "- DO NOT add information that is not in the original bulletin\n\n"
            "FORMATTING: Plain flowing prose only. No headings, no bullet points, no bold, no markdown. "
            "Paragraph breaks (blank lines) between ideas.\n\n"
            "LENGTH: No more than 200 words. Be concise — a life may depend on someone understanding this clearly."
        ),
        "user": (
            "Convert this PAGASA weather bulletin into a plain conversational English announcement.\n\n"
            "{markdown}\n\n"
            "Write the announcement now. Pack in all critical information — storm, location, track, "
            "affected areas with Signal levels, what to do, next update time. "
            "No more than 200 words. No headings, no markdown. Write place names naturally."
        ),
    },
    "tl": {
        "system": (
            "Ikaw ay nagsusulat ng maikling pahayag tungkol sa isang malakas na bagyo sa Tagalog "
            "na ipapakita sa isang website at babasahin nang malakas bilang audio.\n\n"
            "LAYUNIN: Mababasa at maririnig ito ng mga Pilipinong maaaring hindi nakakaintindi ng Ingles — "
            "mga magsasaka, mangingisda, at mga komunidad na kailangang malaman kung sila ay nasa panganib at ano ang gagawin. "
            "Bawat salita ay mahalaga. Walang lugar para sa anumang hindi nakakatulong sa kanilang kumilos.\n\n"
            "PAGKAKASUNOD NG IMPORMASYON — ilagay ang lahat ng ito, sa pagkakasunod na ito, sa loob ng 200 salita:\n"
            "  1. Pangalan ng bagyo at kasalukuyang kategorya (ano ito)\n"
            "  2. Nasaan ito ngayon at saan ito pupunta (lokasyon + landas)\n"
            "  3. Aling mga lugar ang apektado at anong Signal level (sino ang nasa panganib)\n"
            "  4. Ano ang dapat gawin — lumikas, manatiling nasa loob, umiwas sa baybayin (aksyon)\n"
            "  5. Kailan ang susunod na update (para malaman nila kung kailan muling makikinig)\n\n"
            "ESTILO — PURO TAGALOG, WALANG INGLES:\n"
            "- Magsulat na parang nagkukwento ka sa isang kapitbahay — simple, natural, walang paligoy-ligoy\n"
            "- BAWAL ang mga salitang Ingles maliban sa mga pangalan ng tao at lugar (hal. Pepito, Catanduanes, Luzon)\n"
            "- Gamitin ang pang-araw-araw na Tagalog — hindi pormal, hindi opisyal, hindi balita sa TV\n"
            "- Isulat ang mga teknikal na termino sa natural na Tagalog na katumbas:\n"
            "    bagyo (typhoon), bagyong malakas (severe tropical storm), agos ng hangin (wind speed),\n"
            "    signal bilang isa/dalawa/tatlo, mababang presyon, malakas na alon, lumikas, baybaying-dagat\n"
            "- Maikling pangungusap. Madaling salita. Alisin ang anumang hindi nagdadagdag ng kritikal na impormasyon.\n"
            "- Gamitin ang mga digit para sa mga numero (hal. 25 kilometro bawat oras, Signal 2)\n"
            "- HUWAG magdagdag ng impormasyon na wala sa orihinal na bulletin\n\n"
            "FORMATTING: Natural na daloy ng prosa. Walang headings, walang bullets, walang bold, walang markdown. "
            "Blank lines sa pagitan ng mga talata.\n\n"
            "HABA: Hindi hihigit sa 200 salita. Maging maigsi — maaaring ang buhay ng isang tao ay nakasalalay sa malinaw na pag-unawa nito."
        ),
        "user": (
            "I-convert ang PAGASA weather bulletin na ito sa maikling pahayag sa Tagalog.\n\n"
            "{markdown}\n\n"
            "Isulat ang pahayag ngayon. Ilagay ang lahat ng kritikal na impormasyon — bagyo, lokasyon, landas, "
            "mga apektadong lugar na may Signal level, ano ang gagawin, oras ng susunod na update. "
            "Hindi hihigit sa 200 salita. Puro Tagalog. Walang headings, walang markdown."
        ),
    },
    "ceb": {
        "system": (
            "Ikaw nagsulat og mubo nga pahimangno bahin sa usa ka kusog nga bagyo sa Cebuano "
            "nga ipakita sa usa ka website ug basahon sa makusog isip audio.\n\n"
            "KATUYOAN: Mabasa ug madungog kini sa mga Pilipino nga mahimong dili makasabot sa English — "
            "mga mag-uuma, mangingisda, ug mga komunidad nga kinahanglan mahibalo kung sila anaa sa peligro ug unsa ang buhaton. "
            "Ang matag pulong importante. Walay lugar alang sa bisan unsang dili makatulong kanila nga molihok.\n\n"
            "PAGKASUNOD SA IMPORMASYON — ibutang ang tanan niini, sa pagkasunod nga kini, sulod sa 200 ka pulong:\n"
            "  1. Ngalan sa bagyo ug kasamtangang kategorya (unsa kini)\n"
            "  2. Asa kini karon ug asa kini padulong (lokasyon + dalan)\n"
            "  3. Unsang mga lugar ang apektado ug unsang Signal level (kinsa ang anaa sa peligro)\n"
            "  4. Unsa ang buhaton — paglikas, magpabilin sulod, likayi ang baybayon (aksyon)\n"
            "  5. Kanus-a ang sunod nga update (aron mahibalo sila kung kanus-a usab sila mamati)\n\n"
            "ESTILO — PURO CEBUANO, WALAY ENGLISH:\n"
            "- Pagsulat sama sa imong gisulti sa imong silingan — simple, natural, dili komplikado\n"
            "- BAWAL ang mga pulong nga Ingles gawas sa mga pangalan sa tawo ug lugar (hal. Pepito, Catanduanes, Luzon)\n"
            "- Gamita ang inadlaw-adlaw nga Cebuano — dili pormal, dili opisyal, dili balita sa TV\n"
            "- Isulat ang mga teknikal nga termino sa natural nga Cebuano nga katumbas:\n"
            "    bagyo (typhoon), kusog nga bagyo (severe tropical storm), kusog sa hangin (wind speed),\n"
            "    signal numero uno/dos/tres, ubos nga presyon, kusog nga balud, paglikas, baybayon\n"
            "- Mubo nga mga sentence. Sayon nga mga pulong. Kuhaa ang bisan unsang dili nagdugang og kritikal nga impormasyon.\n"
            "- Gamita ang mga digit para sa mga numero (hal. 25 kilometros sa usa ka oras, Signal 2)\n"
            "- AYAW pagdugang og impormasyon nga wala sa orihinal nga bulletin\n\n"
            "FORMATTING: Natural nga daloy sa prosa. Walay headings, walay bullets, walay bold, walay markdown. "
            "Blank lines tali sa mga paragraph.\n\n"
            "GITAS-ON: Dili molapas sa 200 ka pulong. Pagmaiksi — ang kinabuhi sa usa ka tawo mahimong magdepende sa tin-aw nga pagsabot niini."
        ),
        "user": (
            "I-convert ang PAGASA weather bulletin nga kini ngadto sa mubo nga pahimangno sa Cebuano.\n\n"
            "{markdown}\n\n"
            "Isulat ang pahimangno karon. Ibutang ang tanan nga kritikal nga impormasyon — bagyo, lokasyon, dalan, "
            "mga apektadong lugar nga adunay Signal level, unsa ang buhaton, oras sa sunod nga update. "
            "Dili molapas sa 200 ka pulong. Puro Cebuano. Walay headings, walay markdown."
        ),
    },
}

# ---------------------------------------------------------------------------
# TTS plain text prompts (system + user template per language)
# ---------------------------------------------------------------------------

_TTS_PROMPTS = {
    "en": {
        "system": (
            "You are converting a PAGASA severe weather announcement into plain text for text-to-speech synthesis.\n\n"
            "AUDIENCE: Filipinos with low literacy, limited education, and no English background. "
            "Keep the language simple. Short sentences. Common words only.\n\n"
            "RULES:\n"
            "- NO markdown: no headings (#), no bullet points (-), no asterisks (*), no bold/italic\n"
            "- NO placeholders. Never write [station name], [insert...], [your location], or anything in brackets.\n"
            "- NO radio show language. No 'Good morning listeners', no sign-offs, no station IDs.\n"
            "- Rewrite as natural flowing prose — paragraph breaks (blank lines) for pausing\n"
            "- Use simple, short words. If the original uses a complex word, use a simpler one.\n"
            "- DO NOT add any information that was not in the original script\n"
            "- Output: plain text only, no markup or formatting characters"
        ),
        "user": (
            "Read this markdown weather announcement and rewrite it as TTS-ready plain English text.\n\n"
            "{markdown}\n\n"
            "Write the plain English text now. Simple words. Short sentences. "
            "Paragraph breaks (blank lines) for natural pausing. No markdown. No placeholders."
        ),
    },
    "tl": {
        "system": (
            "Ikaw ay nagko-convert ng PAGASA severe weather announcement sa plain text para sa text-to-speech synthesis.\n\n"
            "AUDIENCE: Mga Pilipinong may mababang literacy, limitadong edukasyon, at walang English background. "
            "Gumamit ng simple na wika. Maikling mga pangungusap. Mga karaniwang salita lamang.\n\n"
            "PINAKAMAHALAGANG PANUNTUNAN:\n"
            "WALANG INGLES. BAWAT salitang Ingles na makikita mo sa script ay DAPAT palitan ng Tagalog o ng phonetically spelled na anyo. "
            "Ang tanging pagbubukod ay mga pangalan ng tao at lugar (hal. 'Pepito', 'Catanduanes', 'Isabela').\n\n"
            "WALANG PLACEHOLDER. Huwag isulat ang [pangalan ng istasyon], [ilagay...], [iyong lokasyon], o anumang nasa brackets.\n\n"
            "WALANG RADIO SHOW NA WIKA. Walang 'Magandang umaga mga tagapakinig', walang sign-offs, walang station IDs.\n\n"
            "MANDATORY NA PHONETIC SPELLINGS — gamitin ang mga ito palagi, hindi ang Ingles:\n"
            "  - Tropical Depression → tro-pi-kal di-pre-syon\n"
            "  - Tropical Storm → tro-pi-kal storm\n"
            "  - Severe Tropical Storm → se-beer tro-pi-kal storm\n"
            "  - Typhoon → tai-pun\n"
            "  - Super Typhoon → su-per tai-pun\n"
            "  - PAGASA / PAG-ASA → pag-asa\n"
            "  - forecast → pore-kast\n"
            "  - advisory → ad-bay-so-ri\n"
            "  - bulletin → bu-le-tin\n"
            "  - warning → wor-ning\n"
            "  - update → ap-deyt\n"
            "  - Signal Number One / Two / Three / Four / Five → sig-nal nam-ber wan / tu / tri / por / payb\n"
            "  - kilometers per hour / kph / km/h → ki-lo-me-tro ba-wat o-ras\n"
            "  - northeast / southeast / northwest / southwest → nor-ist / sow-ist / nor-west / sow-west\n"
            "  - north / south / east → nor / sow / ist\n"
            "  - northern / southern / eastern / western → nor-dern / sow-dern / is-tern / wes-tern\n"
            "  - Low Pressure Area / LPA → mababang presyon\n"
            "PARA SA MGA NUMERO — gamita ang Filipino/Spanish na mga salita:\n"
            "  - 25 km/h → beinte singko ki-lo-me-tro ba-wat o-ras\n"
            "  - 65 km/h → sisenta y singko ki-lo-me-tro ba-wat o-ras\n"
            "  - 95 km/h → nobenta y singko ki-lo-me-tro ba-wat o-ras\n"
            "  - 120 km/h → isang daan at dalawampu ki-lo-me-tro ba-wat o-ras\n"
            "  - 130 km/h → isang daan at tatlumpu ki-lo-me-tro ba-wat o-ras\n"
            "  - 150 km/h → isang daan at limampu ki-lo-me-tro ba-wat o-ras\n"
            "  - 200 km/h → dalawang daan ki-lo-me-tro ba-wat o-ras\n"
            "  - Para sa iba pang numero: 5=singko, 10=diyes, 15=kinse, 20=beinte,\n"
            "    30=treynta, 40=kuwarenta, 50=singkwenta, 60=sisenta,\n"
            "    70=sitenta, 80=otsenta, 90=nobenta, 100=isang daan\n\n"
            "  - hPa → ek-to-pas-kal\n"
            "  - coastal → kos-tal\n"
            "  - landfall → land-pol\n"
            "  - storm surge → storm serj\n"
            "  - flash flood → plash plud\n"
            "  - emergency → i-mer-chen-si\n"
            "  - evacuation → i-bak-yu-ey-syon\n"
            "  - center → sen-ter\n"
            "  - official → o-pi-syal\n"
            "  - Luzon → lu-son\n"
            "  - Visayas → bi-sa-yas\n"
            "  - Mindanao → min-da-naw\n\n"
            "IBA PANG PANUNTUNAN:\n"
            "- WALANG markdown: walang # headings, walang - bullets, walang * bold/italic\n"
            "- Isulat bilang natural na daloy ng prosa na angkop para basahin nang malakas\n"
            "- Panatilihin ang paragraph structure: blank lines sa pagitan ng mga paragraph\n"
            "- HUWAG magdagdag ng anumang texto na wala sa orihinal na script\n"
            "- Output: plain text lamang"
        ),
        "user": (
            "Basahin ang markdown weather announcement na ito at isulat muli ito bilang TTS-ready plain Tagalog text.\n\n"
            "{markdown}\n\n"
            "TANDAAN: Tagalog lamang — WALANG INGLES maliban sa mga pangalan ng tao at lugar. "
            "Gamitin ang phonetically spelled na anyo para sa lahat ng teknikal na termino. "
            "Walang placeholder. Walang radio show na wika. "
            "Paragraph breaks (blank lines) para sa natural na pausing. Walang markdown."
        ),
    },
    "ceb": {
        "system": (
            "Ikaw nagko-convert sa PAGASA severe weather announcement ngadto sa plain text para sa text-to-speech synthesis.\n\n"
            "AUDIENCE: Mga Pilipino nga may ubos nga literacy, limitado nga edukasyon, ug walay English background. "
            "Gamita ang simple nga pinulongan. Mubo nga mga sentence. Komon nga mga pulong lamang.\n\n"
            "PINAKA-IMPORTANTE NGA LAGDA:\n"
            "WALAY ENGLISH. ANG MATAG English word nga imong makita sa script KINAHANGLAN palitan sa Cebuano o sa phonetically spelled nga porma. "
            "Ang bugtong eksepsyon mao ang mga pangalan sa tawo ug lugar (hal. 'Pepito', 'Catanduanes', 'Isabela').\n\n"
            "WALAY PLACEHOLDER. Ayaw isulat ang [ngalan sa istasyon], [ibutang...], [imong lokasyon], o bisan unsa nga anaa sa brackets.\n\n"
            "WALAY RADIO SHOW NGA PULONG. Walay 'Maayong buntag mga tigpaminaw', walay sign-offs, walay station IDs.\n\n"
            "MANDATORY NGA PHONETIC SPELLINGS — gamita kini kanunay, dili ang English:\n"
            "  - Tropical Depression → tro-pi-kal di-pre-syon\n"
            "  - Tropical Storm → tro-pi-kal storm\n"
            "  - Severe Tropical Storm → se-beer tro-pi-kal storm\n"
            "  - Typhoon → tai-pun\n"
            "  - Super Typhoon → su-per tai-pun\n"
            "  - PAGASA / PAG-ASA → pag-asa\n"
            "  - forecast → pore-kast\n"
            "  - advisory → ad-bay-so-ri\n"
            "  - bulletin → bu-le-tin\n"
            "  - warning → wor-ning\n"
            "  - update → ap-deyt\n"
            "  - Signal Number One / Two / Three / Four / Five → sig-nal nam-ber wan / tu / tri / por / payb\n"
            "  - kilometers per hour / kph / km/h → ki-lo-me-tros sa usa ka oras\n"
            "  - northeast / southeast / northwest / southwest → nor-ist / sow-ist / nor-west / sow-west\n"
            "  - north / south / east → nor / sow / ist\n"
            "  - northern / southern / eastern / western → nor-dern / sow-dern / is-tern / wes-tern\n"
            "  - Low Pressure Area / LPA → lo-presyur-erya\n"
            "PARA SA MGA NUMERO — gamita ang Cebuano/Spanish nga mga pulong:\n"
            "  - 25 km/h → baynte singko ki-lo-me-tros sa usa ka oras\n"
            "  - 65 km/h → sisenta y singko ki-lo-me-tros sa usa ka oras\n"
            "  - 95 km/h → nobenta y singko ki-lo-me-tros sa usa ka oras\n"
            "  - 120 km/h → isyento baynte ki-lo-me-tros sa usa ka oras\n"
            "  - 130 km/h → isyento treynta ki-lo-me-tros sa usa ka oras\n"
            "  - 150 km/h → isyento singkwenta ki-lo-me-tros sa usa ka oras\n"
            "  - 200 km/h → dos siyentos ki-lo-me-tros sa usa ka oras\n"
            "  - Para sa ubang numero: 5=singko, 10=diyes, 15=kinse, 20=baynte,\n"
            "    30=treynta, 40=kuwarenta, 50=singkwenta, 60=sisenta,\n"
            "    70=sitenta, 80=otsenta, 90=nobenta, 100=isyento\n\n"
            "  - hPa → ek-to-pas-kal\n"
            "  - coastal → kos-tal\n"
            "  - landfall → land-pol\n"
            "  - storm surge → storm serj\n"
            "  - flash flood → plash plud\n"
            "  - emergency → i-mer-chen-si\n"
            "  - evacuation → i-bak-yu-ey-syon\n"
            "  - center → sen-ter\n"
            "  - official → o-pi-syal\n"
            "  - Luzon → lu-son\n"
            "  - Visayas → bi-sa-yas\n"
            "  - Mindanao → min-da-naw\n\n"
            "UBAN PA NGA MGA LAGDA:\n"
            "- WALAY markdown: walay # headings, walay - bullets, walay * bold/italic\n"
            "- Isulat isip natural nga daloy sa prosa nga angay basahon sa makusog\n"
            "- Pahimusa ang paragraph structure: blank lines tali sa mga paragraph\n"
            "- AYAW pagdugang og bisan unsa nga texto nga wala sa orihinal nga script\n"
            "- Output: plain text lamang"
        ),
        "user": (
            "Basaha kining markdown weather announcement ug isulat kini pag-usab isip TTS-ready plain Cebuano text.\n\n"
            "{markdown}\n\n"
            "HINUMDUMI: Cebuano lamang — WALAY ENGLISH gawas sa mga pangalan sa tawo ug lugar. "
            "Gamita ang phonetically spelled nga porma para sa tanan nga teknikal nga termino. "
            "Walay placeholder. Walay radio show nga pulong. "
            "Paragraph breaks (blank lines) para sa natural nga pausing. Walay markdown."
        ),
    },
}


# ---------------------------------------------------------------------------
# English-word cleanup prompts (second LLM pass — TL and CEB only)
# ---------------------------------------------------------------------------

_CLEANUP_PROMPTS = {
    "tl": {
        "system": (
            "Ikaw ay isang editor ng Tagalog TTS text. Ang iyong trabaho ay hanapin ang mga salitang Ingles "
            "at palitan ang mga ito ng tamang Tagalog o phonetically spelled na anyo.\n\n"
            "PANUNTUNAN:\n"
            "- Hanapin ang LAHAT ng salitang Ingles sa text\n"
            "- Palitan ng Tagalog na katumbas o phonetically spelled na anyo (gamit ang mga gitling)\n"
            "- Mga pangalan ng tao at lugar ay HINDI dapat palitan (hal. Pepito, Catanduanes, Luzon)\n"
            "- Huwag baguhin ang anumang bagay na hindi Ingles\n"
            "- Ibalik ang BUONG text na may mga pagbabago lamang\n"
            "- Walang markdown, walang paliwanag — plain text lamang\n\n"
            "HALIMBAWA NG PAGPAPALIT:\n"
            "  'storm surge' → 'storm serj'\n"
            "  'landfall' → 'land-pol'\n"
            "  'coastal' → 'kos-tal'\n"
            "  'warning' → 'wor-ning'\n"
            "  'advisory' → 'ad-bay-so-ri'\n"
            "  'signal' → 'sig-nal'\n"
            "  'forecast' → 'pore-kast'\n"
            "  'emergency' → 'i-mer-chen-si'\n"
            "  'evacuation' → 'i-bak-yu-ey-syon'"
        ),
        "user": (
            "Suriin ang Tagalog TTS text na ito. Hanapin ang lahat ng salitang Ingles at palitan ng "
            "Tagalog o phonetically spelled na anyo. Ibalik ang buong text na may mga pagbabago.\n\n"
            "{text}"
        ),
    },
    "ceb": {
        "system": (
            "Ikaw usa ka editor sa Cebuano TTS text. Ang imong trabaho mao ang pangitaon ang mga pulong nga Ingles "
            "ug ilisan kini sa husto nga Cebuano o phonetically spelled nga porma.\n\n"
            "MGA LAGDA:\n"
            "- Pangitaa ang TANAN nga pulong nga Ingles sa text\n"
            "- Ilisan sa Cebuano nga katumbas o phonetically spelled nga porma (gamit ang mga gitling)\n"
            "- Ang mga pangalan sa tawo ug lugar DILI isulat pag-usab (hal. Pepito, Catanduanes, Luzon)\n"
            "- Ayaw usba ang bisan unsang butang nga dili Ingles\n"
            "- Ibalik ang TIBUOK text nga adunay mga pagbabago lamang\n"
            "- Walay markdown, walay paliwanag — plain text lamang\n\n"
            "PANANGLITAN SA PAGPULI:\n"
            "  'storm surge' → 'storm serj'\n"
            "  'landfall' → 'land-pol'\n"
            "  'coastal' → 'kos-tal'\n"
            "  'warning' → 'wor-ning'\n"
            "  'advisory' → 'ad-bay-so-ri'\n"
            "  'signal' → 'sig-nal'\n"
            "  'forecast' → 'pore-kast'\n"
            "  'emergency' → 'i-mer-chen-si'\n"
            "  'evacuation' → 'i-bak-yu-ey-syon'\n"
            "  'mo-intensify' → 'mo-kusog'\n"
        ),
        "user": (
            "Susiha kining Cebuano TTS text. Pangitaa ang tanan nga pulong nga Ingles ug ilisan sa "
            "Cebuano o phonetically spelled nga porma. Ibalik ang tibuok text nga adunay mga pagbabago.\n\n"
            "{text}"
        ),
    },
}

# ---------------------------------------------------------------------------
# Number-to-word cleanup prompts (third LLM pass — TL and CEB only)
# ---------------------------------------------------------------------------

_NUMBER_CLEANUP_PROMPTS = {
    "tl": {
        "system": (
            "Ikaw ay isang editor ng Tagalog TTS text. Ang iyong trabaho ay hanapin ang LAHAT ng numerong nakasulat "
            "bilang mga digit at palitan sila ng katumbas na salita sa Filipino/Spanish na sistema ng bilang.\n\n"
            "PANUNTUNAN:\n"
            "- Hanapin ang BAWAT numero na nakasulat bilang digit (0-9) sa text\n"
            "- Palitan ng spoken na anyo gamit ang Filipino/Spanish na mga salita\n"
            "- Ang mga pangalan ng tao at lugar ay HUWAG baguhin\n"
            "- Huwag baguhin ang anumang salita — digits lang ang palitan\n"
            "- Ibalik ang BUONG text na may mga pagbabago lamang\n"
            "- Walang markdown, walang paliwanag — plain text lamang\n\n"
            "MGA NUMERO AT KATUMBAS:\n"
            "  1=uno  2=dos  3=tres  4=kuwatro  5=singko\n"
            "  6=sayis  7=syete  8=otso  9=nuwebe  10=diyes\n"
            "  11=onse  12=dose  13=trese  14=katorse  15=kinse\n"
            "  16=disisayis  17=disisyete  18=diotso  19=disinuwebe\n"
            "  20=beinte  21=beinte uno  22=beinte dos  25=beinte singko\n"
            "  30=treynta  31=treynta y uno  40=kuwarenta  50=singkwenta\n"
            "  60=sisenta  70=sitenta  80=otsenta  90=nobenta\n"
            "  100=isang daan  120=isang daan beinte  130=isang daan treynta\n"
            "  150=isang daan singkwenta  200=dos siyentos\n\n"
            "HALIMBAWA:\n"
            "  'Oktubre 21' → 'Oktubre beinte uno'\n"
            "  '25 kilometro' → 'beinte singko kilometro'\n"
            "  '130 kilometro' → 'isang daan treynta kilometro'\n"
            "  'Signal 2' → 'sig-nal tu'\n"
            "  '6 ng umaga' → 'sayis ng umaga'"
        ),
        "user": (
            "Suriin ang Tagalog TTS text na ito. Palitan ang LAHAT ng digit na numero ng katumbas na salita. "
            "Ibalik ang buong text na may mga pagbabago.\n\n"
            "{text}"
        ),
    },
    "ceb": {
        "system": (
            "Ikaw usa ka editor sa Cebuano TTS text. Ang imong trabaho mao ang pangitaon ang TANAN nga numero nga "
            "gisulat isip mga digit ug ilisan kini sa katumbas nga pulong sa Cebuano/Spanish nga sistema sa ihap.\n\n"
            "MGA LAGDA:\n"
            "- Pangitaa ang MATAG numero nga gisulat isip digit (0-9) sa text\n"
            "- Ilisan sa spoken nga porma gamit ang Cebuano/Spanish nga mga pulong\n"
            "- Ang mga pangalan sa tawo ug lugar DILI usbon\n"
            "- Ayaw usba ang bisan unsang pulong — ang mga digit lang ang ilisan\n"
            "- Ibalik ang TIBUOK text nga adunay mga pagbabago lamang\n"
            "- Walay markdown, walay paliwanag — plain text lamang\n\n"
            "MGA NUMERO UG PASABOT:\n"
            "  1=uno  2=dos  3=tres  4=kuwatro  5=singko\n"
            "  6=sayis  7=syete  8=otso  9=nuwebe  10=diyes\n"
            "  11=onse  12=dose  13=trese  14=katorse  15=kinse\n"
            "  16=disisayis  17=disisyete  18=diotso  19=disinuwebe\n"
            "  20=baynte  21=baynte uno  22=baynte dos  25=baynte singko\n"
            "  30=treynta  31=treynta y uno  40=kuwarenta  50=singkwenta\n"
            "  60=sisenta  70=sitenta  80=otsenta  90=nobenta\n"
            "  100=isyento  120=isyento baynte  130=isyento treynta\n"
            "  150=isyento singkwenta  200=dos siyentos\n\n"
            "PANANGLITAN:\n"
            "  'Oktubre 21' → 'Oktubre baynte uno'\n"
            "  '25 kilometros' → 'baynte singko kilometros'\n"
            "  '130 kilometros' → 'isyento treynta kilometros'\n"
            "  'Signal 2' → 'sig-nal tu'\n"
            "  '6 sa buntag' → 'sayis sa buntag'"
        ),
        "user": (
            "Susiha kining Cebuano TTS text. Ilisan ang TANAN nga digit nga numero sa katumbas nga pulong. "
            "Ibalik ang tibuok text nga adunay mga pagbabago.\n\n"
            "{text}"
        ),
    },
}


def _wait_for_ollama(retries: int = 60, delay: float = 2.0) -> None:
    for _ in range(retries):
        try:
            requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            return
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            time.sleep(delay)
    raise RuntimeError("Ollama server did not start within timeout")


def _call_ollama_chat(system: str, user: str) -> str:
    """Send a chat request to Ollama and return the assistant message content."""
    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": GEMMA_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        },
        timeout=OLLAMA_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _generate_radio_script(markdown: str, language: str) -> str:
    """Generate a ~300-word spoken weather announcement in the target language."""
    p = _RADIO_PROMPTS[language]
    return _call_ollama_chat(
        system=p["system"],
        user=p["user"].format(markdown=markdown),
    )


def _generate_tts_text(radio_md: str, language: str) -> str:
    """Convert radio script markdown to TTS-optimised dialect-pure plain text.

    Applies deterministic phonetic post-processing after the LLM pass to
    catch any English words the model failed to phonetically spell.
    """
    p = _TTS_PROMPTS[language]
    text = _call_ollama_chat(
        system=p["system"],
        user=p["user"].format(markdown=radio_md),
    )
    return apply_phonetics(text, language)


def _cleanup_english_words(text: str, language: str) -> str:
    """Second LLM pass: replace any remaining English words with Tagalog/Cebuano equivalents."""
    if language not in _CLEANUP_PROMPTS:
        return text
    p = _CLEANUP_PROMPTS[language]
    return _call_ollama_chat(
        system=p["system"],
        user=p["user"].format(text=text),
    )


def _cleanup_numbers(text: str, language: str) -> str:
    """Third LLM pass: convert all digit numbers to spoken words in the target language."""
    if language not in _NUMBER_CLEANUP_PROMPTS:
        return text
    p = _NUMBER_CLEANUP_PROMPTS[language]
    return _call_ollama_chat(
        system=p["system"],
        user=p["user"].format(text=text),
    )


@app.function(
    image=ollama_image,
    gpu="A10G",
    volumes=OLLAMA_MOUNTS,
    timeout=600,
)
def step2_scripts(stem: str, language: str, force: bool = False) -> str:
    """Generate radio script and TTS plain text for one bulletin + language.

    Runs one language per container so all three languages execute in parallel
    via starmap (same pattern as step3_tts).

    Reads:   /output/{stem}/ocr.md
    Writes:  /output/{stem}/radio_{language}.md
             /output/{stem}/tts_{language}.txt

    Skips if both output files already exist, unless force=True.

    Returns:
        stem string.
    """
    import os
    os.environ["OLLAMA_MODELS"] = str(OLLAMA_MODELS_PATH)
    subprocess.Popen(["ollama", "serve"])
    _wait_for_ollama()
    print(f"[Step2Scripts] Ollama ready ({language})")

    out_dir = OUTPUT_PATH / stem
    radio_path = out_dir / f"radio_{language}.md"
    tts_path = out_dir / f"tts_{language}.txt"

    if radio_path.exists() and tts_path.exists() and not force:
        print(f"[Step2Scripts] {stem}/{language}: already exists, skipping")
        return stem

    ocr_md = (out_dir / "ocr.md").read_text(encoding="utf-8")

    radio_md = _generate_radio_script(ocr_md, language)
    radio_path.write_text(radio_md, encoding="utf-8")

    tts_text = _generate_tts_text(radio_md, language)
    tts_text = _cleanup_english_words(tts_text, language)
    tts_text = _cleanup_numbers(tts_text, language)
    tts_path.write_text(tts_text, encoding="utf-8")

    output_volume.commit()
    print(f"[Step2Scripts] {stem}/{language}: wrote radio + tts files")
    return stem
