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
            "You are converting a PAGASA typhoon bulletin into a plain spoken weather announcement in English.\n\n"
            "STYLE:\n"
            "- Write as if explaining to a neighbour — conversational, simple, direct\n"
            "- No broadcaster language, no formal sign-offs, no station IDs, no 'Good morning listeners'\n"
            "- Short sentences. Common words. Anyone should understand this.\n"
            "- Use digits for numbers (e.g. '25 kilometres per hour', 'Signal 2')\n"
            "- Cover: what the storm is, where it is, where it is going, who is affected, what people should do\n"
            "- DO NOT add information that is not in the original bulletin\n\n"
            "PHILIPPINE PLACE NAME PRONUNCIATION — spell these phonetically so they are read correctly by the TTS engine:\n"
            "  - Catanduanes → ka-tan-du-a-nes\n"
            "  - Cagayan → ka-ga-yan\n"
            "  - Isabela → i-sa-be-la\n"
            "  - Visayas → bi-sa-yas\n"
            "  - Mindanao → min-da-naw\n"
            "  - Quezon → ke-son\n"
            "  - Batanes → ba-ta-nes\n"
            "  - Samar → sa-mar\n"
            "  - Leyte → ley-te\n"
            "  - Palawan → pa-la-wan\n"
            "  - Bicol → bi-kol\n"
            "  - Masbate → mas-ba-te\n"
            "  - Surigao → su-ri-ga-o\n"
            "  - Pangasinan → pa-nga-si-nan\n"
            "  - Zamboanga → zam-bo-an-ga\n\n"
            "FORMATTING: Plain flowing prose only. No headings, no bullet points, no bold, no markdown. "
            "Paragraph breaks (blank lines) between ideas.\n\n"
            "LENGTH: About 300 words."
        ),
        "user": (
            "Convert this PAGASA weather bulletin into a plain conversational English announcement.\n\n"
            "{markdown}\n\n"
            "Write the announcement now. Conversational tone, simple words, about 300 words. "
            "No headings, no bullet points, no markdown. Spell Filipino place names phonetically."
        ),
    },
    "tl": {
        "system": (
            "Ikaw ay nagsusulat ng simpleng pahayag tungkol sa isang malakas na bagyo para marinig ng mga tao.\n\n"
            "ESTILO — PURO TAGALOG, WALANG INGLES:\n"
            "- Magsulat na parang nagkukwento ka sa isang kapitbahay — simple, natural, walang paligoy-ligoy\n"
            "- BAWAL ang mga salitang Ingles maliban sa mga pangalan ng tao at lugar (hal. Pepito, Catanduanes, Luzon)\n"
            "- Gamitin ang pang-araw-araw na Tagalog — hindi pormal, hindi opisyal, hindi balita sa TV\n"
            "- Kung may teknikal na salita, i-spell phonetically gamit ang gitling:\n"
            "    tai-pun, tro-pi-kal di-pre-syon, sig-nal nam-ber wan, ki-lo-me-tro ba-wat o-ras,\n"
            "    storm serj, land-pol, kos-tal, pag-asa, pore-kast, wor-ning, ad-bay-so-ri\n"
            "- Maikling pangungusap. Madaling salita. Dapat maintindihan ng sinumang Pilipino.\n"
            "- Gamitin ang mga digit para sa mga numero (hal. 25 kilometro bawat oras, Signal 2)\n"
            "- Sabihin: ano ang bagyo, nasaan ito, saan patungo, sino ang maaapektuhan, ano ang dapat gawin\n"
            "- HUWAG magdagdag ng impormasyon na wala sa orihinal na bulletin\n\n"
            "FORMATTING: Natural na daloy ng prosa. Walang headings, walang bullets, walang bold, walang markdown. "
            "Blank lines sa pagitan ng mga talata.\n\n"
            "HABA: Mga 300 salita."
        ),
        "user": (
            "I-convert ang PAGASA weather bulletin na ito sa simpleng pahayag sa Tagalog.\n\n"
            "{markdown}\n\n"
            "Isulat ang pahayag ngayon. Puro Tagalog — walang Ingles maliban sa mga pangalan. "
            "Natural na tono, madaling salita, mga 300 salita. Walang headings, walang markdown."
        ),
    },
    "ceb": {
        "system": (
            "Ikaw nagsulat og simple nga pahimangno bahin sa usa ka kusog nga bagyo para madungog sa mga tawo.\n\n"
            "ESTILO — PURO CEBUANO, WALAY ENGLISH:\n"
            "- Pagsulat sama sa imong gisulti sa imong silingan — simple, natural, dili komplikado\n"
            "- BAWAL ang mga pulong nga Ingles gawas sa mga pangalan sa tawo ug lugar (hal. Pepito, Catanduanes, Luzon)\n"
            "- Gamita ang inadlaw-adlaw nga Cebuano — dili pormal, dili opisyal, dili balita sa TV\n"
            "- Kung adunay teknikal nga pulong, i-spell phonetically gamit ang gitling:\n"
            "    tai-pun, tro-pi-kal di-pre-syon, sig-nal nam-ber wan, ki-lo-me-tros sa usa ka oras,\n"
            "    storm serj, land-pol, kos-tal, pag-asa, pore-kast, wor-ning, ad-bay-so-ri\n"
            "- Mubo nga mga sentence. Sayon nga mga pulong. Kinahanglan masabtan sa tanan nga Pilipino.\n"
            "- Gamita ang mga digit para sa mga numero (hal. 25 kilometros sa usa ka oras, Signal 2)\n"
            "- Isulti: unsa ang bagyo, asa kini, asa padulong, kinsa ang maapektuhan, unsa ang buhaton\n"
            "- AYAW pagdugang og impormasyon nga wala sa orihinal nga bulletin\n\n"
            "FORMATTING: Natural nga daloy sa prosa. Walay headings, walay bullets, walay bold, walay markdown. "
            "Blank lines tali sa mga paragraph.\n\n"
            "GITAS-ON: Mga 300 ka pulong."
        ),
        "user": (
            "I-convert ang PAGASA weather bulletin nga kini ngadto sa simple nga pahimangno sa Cebuano.\n\n"
            "{markdown}\n\n"
            "Isulat ang pahimangno karon. Puro Cebuano — walay English gawas sa mga pangalan. "
            "Natural nga tono, sayon nga mga pulong, mga 300 ka pulong. Walay headings, walay markdown."
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
            "  - Low Pressure Area / LPA → ubos nga presyon\n"
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
    tts_path.write_text(tts_text, encoding="utf-8")

    output_volume.commit()
    print(f"[Step2Scripts] {stem}/{language}: wrote radio + tts files")
    return stem
