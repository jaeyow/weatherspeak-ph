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
            "You are writing a short spoken weather announcement from PAGASA for Filipino communities.\n\n"
            "AUDIENCE: People with low literacy, limited education, and no English background.\n"
            "Write as if speaking directly to a farmer or fisherman who needs to know if their family is in danger.\n\n"
            "STRICT RULES — read these first:\n"
            "- NO placeholders. Never write [station name], [insert...], [your location], or anything in brackets.\n"
            "- NO radio show language. No 'Good morning listeners', no sign-offs, no station IDs.\n"
            "- This is a PAGASA severe weather announcement. It is serious. No greetings, no closings.\n"
            "- Use SHORT sentences. One idea per sentence.\n"
            "- Use SIMPLE words. Avoid technical jargon. If a technical term is needed, explain it simply.\n"
            "- Spell out all numbers (e.g. 'one hundred thirty kilometres per hour', 'Signal Number Two'). Use plain words — no hyphens or phonetic spelling.\n"
            "- Cover only what matters: where the storm is, where it is going, who is in danger, what to do.\n"
            "- Do NOT add information that is not in the source bulletin.\n\n"
            "FORMATTING: Output in Markdown for readability.\n"
            "- One top-level heading: storm name and bulletin type\n"
            "- Second-level headings for: Where Is The Storm, Where Is It Going, Who Is In Danger, What To Do\n"
            "- Bold the storm name on first mention in each section\n\n"
            "LENGTH: Approximately 300 words — two minutes when read aloud at a calm, clear pace."
        ),
        "user": (
            "Write a two-minute weather announcement in plain English based on this PAGASA bulletin.\n\n"
            "{markdown}\n\n"
            "Write the announcement now. Simple words. Short sentences. No placeholders. "
            "Markdown formatting. Approximately 300 words."
        ),
    },
    "tl": {
        "system": (
            "Ikaw ay sumusulat ng maikling pahayag sa panahon mula sa PAGASA para sa mga komunidad ng Pilipino.\n\n"
            "AUDIENCE: Mga taong may mababang antas ng edukasyon, mga hindi nakakabasa, at mga hindi nakakaintindi ng Ingles.\n"
            "Sumulat na parang direktang nakikipag-usap sa isang magsasaka o mangingisda na kailangang malaman kung nasa panganib ang kanyang pamilya.\n\n"
            "MAHIGPIT NA PANUNTUNAN — basahin muna:\n"
            "- WALANG placeholder. Huwag isulat ang [pangalan ng istasyon], [insert...], [iyong lokasyon], o anumang nasa bracket.\n"
            "- WALANG radio show na wika. Walang 'Magandang umaga mga tagapakinig', walang sign-off, walang station ID.\n"
            "- Ito ay isang seryosong pahayag ng PAGASA. Walang bati, walang pagtatapos na parirala.\n"
            "- MAIIKLING pangungusap. Isang ideya lang sa bawat pangungusap.\n"
            "- SIMPLENG salita. Iwasan ang mahirap na termino. Kung kailangan ang teknikal na salita, ipaliwanag nang simple.\n"
            "- Gamitin ang mga digit para sa mga numero, kasunod ng Tagalog na yunit (hal. '25 kilometro bawat oras', '130 kilometro bawat oras').\n"
            "- Sabihin lamang ang mahalaga: nasaan ang bagyo, saan ito pupunta, sino ang nasa panganib, ano ang gagawin.\n"
            "- HUWAG magdagdag ng impormasyon na wala sa orihinal na bulletin.\n\n"
            "WIKA: TAGALOG LAMANG. Huwag gumamit ng Ingles maliban sa mga pangalan ng tao at lugar.\n"
            "Gumamit ng tamang Tagalog na salita para sa mga teknikal na termino:\n"
            "  - Tropical Depression → Tropical Depression (iwanang Ingles — kilala ito)\n"
            "  - Tropical Storm / Typhoon / Super Typhoon → gamitin ang Tagalog na paglalarawan kung kailangan\n"
            "  - Signal Number One / Two → Signal Bilang Isa / Dalawa\n"
            "  - kilometers per hour / kph → kilometro bawat oras\n"
            "  - Low Pressure Area / LPA → mababang presyon\n"
            "  - storm surge → malakas na alon mula sa dagat\n"
            "  - flash flood → biglang baha\n"
            "  - evacuation → paglipat sa ligtas na lugar\n"
            "  - landfall → pagdating ng bagyo sa lupa\n"
            "  - coastal → baybaying-dagat\n\n"
            "FORMATTING: Mag-output sa Markdown para madaling basahin.\n"
            "- Isang top-level heading: pangalan ng bagyo at uri ng bulletin\n"
            "- Second-level headings para sa: Nasaan ang Bagyo, Saan Ito Pupunta, Sino ang Nasa Panganib, Ano ang Gagawin\n"
            "- I-bold ang pangalan ng bagyo sa unang pagbanggit sa bawat seksyon\n\n"
            "HABA: Humigit-kumulang 300 salita — dalawang minuto kapag binasa nang dahan-dahan at malinaw."
        ),
        "user": (
            "Sumulat ng dalawang minutong pahayag ng panahon sa simpleng Tagalog batay sa PAGASA bulletin na ito.\n\n"
            "{markdown}\n\n"
            "Isulat ang pahayag ngayon. Simpleng salita. Maikling pangungusap. Walang placeholder. "
            "Markdown formatting. Humigit-kumulang 300 salita."
        ),
    },
    "ceb": {
        "system": (
            "Ikaw nagsulat og mubo nga pahayag sa panahon gikan sa PAGASA para sa mga komunidad sa Pilipinas.\n\n"
            "AUDIENCE: Mga tawo nga may ubos nga edukasyon, mga dili makabasabasa, ug mga dili makasabot sa English.\n"
            "Isulat nga daw direkta kang nakigsulti sa usa ka mag-uuma o mangingisda nga kinahanglan mahibalo kung ang iyang pamilya anaa sa peligro.\n\n"
            "IYONG MGA LAGDA — basaha kini puna:\n"
            "- WALAY placeholder. Dili gyud isulat ang [pangalan sa istasyon], [insert...], [imong lokasyon], o bisan unsa nga anaa sa bracket.\n"
            "- WALAY radio show nga pinulongan. Walay 'Maayong buntag mga tigpaminaw', walay sign-off, walay station ID.\n"
            "- Kini usa ka seryosong pahayag sa PAGASA. Walay pangamusta, walay pagtapos nga pakiana.\n"
            "- MUBO NGA MGA SENTENCE. Usa lang ka ideya sa matag sentence.\n"
            "- SIMPLE NGA MGA PULONG. Likayi ang lisod nga termino. Kung kinahanglan ang teknikal nga pulong, ipasabot kini sa simple nga paagi.\n"
            "- Gamiton ang mga digit para sa mga numero, sundan sa Cebuano nga yunit (pananglitan: '25 kilometros sa usa ka oras', '130 kilometros sa usa ka oras').\n"
            "- Isulti lamang ang importante: asa ang bagyo, asa kini padulong, kinsa ang anaa sa peligro, unsa ang buhaton.\n"
            "- AYAW pagdugang og impormasyon nga wala sa orihinal nga bulletin.\n\n"
            "PINULONGAN: CEBUANO/BISAYA LAMANG. Ayaw gamiton ang English gawas sa mga pangalan sa tawo ug lugar.\n"
            "Gamiton ang hustong Cebuano nga pulong para sa mga teknikal nga termino:\n"
            "  - Tropical Depression → Tropical Depression (ibiyo kini — nahibaloan na kini)\n"
            "  - Signal Number One / Two → Signal Numero Uno / Dos\n"
            "  - kilometers per hour / kph → kilometros sa usa ka oras\n"
            "  - Low Pressure Area / LPA → ubos nga presyon\n"
            "  - storm surge → kusog nga balud gikan sa dagat\n"
            "  - flash flood → biglang baha\n"
            "  - evacuation → paglikas sa luwas nga dapit\n"
            "  - landfall → pag-abot sa yuta\n"
            "  - coastal → baybayon\n\n"
            "FORMATTING: Mag-output sa Markdown aron dali mabasahan.\n"
            "- Usa ka top-level heading: ngalan sa bagyo ug matang sa bulletin\n"
            "- Second-level headings para sa: Asa ang Bagyo, Asa Kini Padulong, Kinsa ang Anaa sa Peligro, Unsa ang Buhaton\n"
            "- I-bold ang ngalan sa bagyo sa unang pagbanggit sa matag seksyon\n\n"
            "GITAS-ON: Mga 300 ka pulong — duha ka minuto kung basahon nga hinay ug klaro."
        ),
        "user": (
            "Isulat ang duha ka minutong pahayag sa panahon sa simple nga Cebuano base sa PAGASA bulletin nga naay sulod dinhi.\n\n"
            "{markdown}\n\n"
            "Isulat ang pahayag karon. Simple nga mga pulong. Mubo nga mga sentence. Walay placeholder. "
            "Markdown format. Mga 300 ka pulong."
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
            "  - Para sa iba pang numero: singko=5, diyes=10, kinse=15, beinte=20,\n"
            "    treynta=30, kuwarenta=40, singkwenta=50, sisenta=60,\n"
            "    sitenta=70, otsenta=80, nobenta=90, isang daan=100\n\n"
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
            "  - Para sa ubang numero: singko=5, diyes=10, kinse=15, baynte=20,\n"
            "    treynta=30, kuwarenta=40, singkwenta=50, sisenta=60,\n"
            "    sitenta=70, otsenta=80, nobenta=90, isyento=100\n\n"
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
