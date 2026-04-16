import subprocess
import time
from pathlib import Path

import modal
import requests

from modal_etl.app import app, ollama_image, OLLAMA_MOUNTS, output_volume
from modal_etl.config import OLLAMA_MODELS_PATH, OUTPUT_PATH, GEMMA_MODEL, LANGUAGES

OLLAMA_URL = "http://localhost:11434"
OLLAMA_TIMEOUT = 300  # seconds per language prompt

# ---------------------------------------------------------------------------
# Radio script prompts (system + user template per language)
# ---------------------------------------------------------------------------

_RADIO_PROMPTS = {
    "en": {
        "system": (
            "You are a Philippine radio weather broadcaster writing a spoken bulletin script for on-air reading in English.\n\n"
            "STYLE RULES:\n"
            "- Write in flowing, natural prose suitable for reading aloud.\n"
            "- Use a calm, authoritative tone appropriate for public emergency broadcasts.\n"
            "- Spell out numbers when they will be read aloud (e.g. \"one hundred thirty kilometres per hour\", \"Signal Number Two\").\n"
            "- Repeat the storm name and the most critical warning signal at least twice — radio listeners may tune in partway through.\n"
            "- Use natural spoken transitions: \"At this time...\", \"Moving on to the forecast...\", \"Residents are urged to...\"\n"
            "- Reference the Philippine Atmospheric, Geophysical and Astronomical Services Administration, or PAGASA, by name at the start.\n"
            "- Close with the time of the next scheduled bulletin update.\n\n"
            "FORMATTING: Output in Markdown so the script is easy to read and review.\n"
            "- Use a top-level heading for the bulletin title (storm name + bulletin type)\n"
            "- Use second-level headings for each section: Current Situation, Forecast Track, Affected Areas, Public Safety Advisory, Closing\n"
            "- Bold the storm name and signal numbers on first mention in each section\n"
            "- Keep the prose itself natural and speakable — the markdown is for readability only\n\n"
            "LENGTH: Target approximately 750 words — this should read aloud in about five minutes at a steady broadcast pace."
        ),
        "user": (
            "Write a five-minute radio broadcast bulletin script in English based on the following PAGASA weather bulletin text.\n\n"
            "{markdown}\n\n"
            "Write the radio script now. Use Markdown formatting, approximately 750 words."
        ),
    },
    "tl": {
        "system": (
            "Ikaw ay isang Filipino radio weather broadcaster na sumusulat ng spoken bulletin script para basahin sa ere sa Tagalog.\n\n"
            "MGA PATAKARAN SA ESTILO:\n"
            "- Sumulat sa natural na daloy ng prosa na angkop para basahin nang malakas.\n"
            "- Gumamit ng kalmado at may awtoridad na tono na angkop para sa public emergency broadcasts.\n"
            "- I-spell out ang mga numero kapag babasahin (halimbawa: \"isandaan at tatlumpung kilometro bawat oras\", \"Signal Number Two\").\n"
            "- Ulitin ang pangalan ng bagyo at ang pinaka-kritikal na babala nang kahit dalawang beses.\n"
            "- Gumamit ng natural na transisyon: \"Sa ngayon...\", \"Patungo sa forecast...\", \"Hinihikayat ang mga residente na...\"\n"
            "- Banggitin ang PAGASA sa simula ng bulletin.\n"
            "- Magtapos sa oras ng susunod na scheduled bulletin update.\n\n"
            "FORMATTING: Mag-output sa Markdown para madaling basahin at suriin.\n"
            "- Gumamit ng top-level heading para sa pamagat ng bulletin (pangalan ng bagyo + uri ng bulletin)\n"
            "- Gumamit ng second-level headings para sa bawat seksyon: Kasalukuyang Sitwasyon, Forecast Track, Mga Apektadong Lugar, Payo sa Kaligtasan, Pangwakas\n"
            "- I-bold ang pangalan ng bagyo at signal numbers sa unang pagbanggit sa bawat seksyon\n"
            "- Panatilihing natural ang prosa para mabasa nang maayos\n\n"
            "HABA: Target na humigit-kumulang 750 salita — dapat itong mabasa sa loob ng limang minuto."
        ),
        "user": (
            "Sumulat ng limang minutong radio broadcast bulletin script sa Tagalog batay sa sumusunod na PAGASA weather bulletin text.\n\n"
            "{markdown}\n\n"
            "Sumulat ng radio script ngayon. Gumamit ng Markdown formatting, humigit-kumulang 750 salita."
        ),
    },
    "ceb": {
        "system": (
            "Ikaw usa ka Filipino radio weather broadcaster nga direkta nakigsulti sa mga mamumuno sa Cebuano. "
            "Isulat ang bulletin sama sa imong gisulti sa radyo — natural, conversational, ug dali masabtan.\n\n"
            "MGA LAGDA SA ESTILO (CONVERSATIONAL RADIO CEBUANO):\n"
            "- Pagsulat sama sa regular nga radyo broadcaster nga nakigsulti sa mga tagapaminaw — dili formal, natural lang nga Bisaya.\n"
            "- Gamita ang mga common nga radio phrases: \"Ato pang hisgutan...\", \"Karon, mga higala...\", \"Unya ha...\", \"Importante nga...\"\n"
            "- I-spell out ang mga numero sama sa pagsulti (pananglitan: \"usa ka gatos ug katluan ka kilometro matag oras\", \"Signal Number Two\").\n"
            "- Sublia ang ngalan sa bagyo ug signal areas og duha o tulo ka beses — basin lang dili makahibalo ang uban.\n"
            "- Gamita ang conversational nga transitions: \"Karon ha...\", \"Unya kini...\", \"Importante kaayo nga...\", \"Mga kauban...\"\n"
            "- Mention PAGASA sa sinugdan pero dili kaayo formal — natural lang.\n"
            "- Taposan sama sa regular nga radyo: \"Tan-awa nato pag-usab sa...\" o \"Magkita tag usab sa...\"\n\n"
            "FORMATTING: Mag-output sa Markdown aron dali mabasahan.\n"
            "- Paggamit og top-level heading alang sa titulo sa bulletin (ngalan sa bagyo + matang sa bulletin)\n"
            "- Paggamit og second-level headings alang sa matag seksyon pero simple lang: Unsay Nahitabo Karon, Asa Padulong ang Bagyo, Kinsa ang Apektado, Unsa ang Kinahanglan Buhaton, Pangwakas\n"
            "- I-bold ang ngalan sa bagyo ug signal numbers\n"
            "- Pero ang script mismo kinahanglan conversational — parang nag-istambay lang mo sa radyo\n\n"
            "GITAS-ON: Mga 750 ka pulong — lima ka minuto nga radyo talk, dili basahon nga formal."
        ),
        "user": (
            "Isulat ang lima ka minutong conversational radio bulletin sa Cebuano base sa PAGASA weather bulletin text nga naay sulod dinhi.\n\n"
            "{markdown}\n\n"
            "Pagsulat karon — conversational Bisaya, parang nag-istorya lang sa radyo. Markdown format, mga 750 ka pulong."
        ),
    },
}

# ---------------------------------------------------------------------------
# TTS plain text prompts (system + user template per language)
# ---------------------------------------------------------------------------

_TTS_PROMPTS = {
    "en": {
        "system": (
            "You are a specialist in writing plain text suitable for text-to-speech synthesis.\n\n"
            "Your task:\n"
            "- Read the provided markdown radio script\n"
            "- Rewrite it as natural flowing prose IN ENGLISH ONLY — no markdown\n"
            "- NO markdown: no headings (#), no bullet points (-), no asterisks (*), no bold/italic\n"
            "- Keep technical terms clear and pronounceable\n"
            "- Maintain paragraph structure: blank lines between paragraphs\n"
            "- DO NOT add any text that wasn't in the original script\n"
            "- Output: plain text only, no markup or formatting characters"
        ),
        "user": (
            "Read this markdown radio script and rewrite it as TTS-ready plain English text.\n\n"
            "{markdown}\n\n"
            "Write the plain English text now. Clear pronunciation-friendly English, "
            "paragraph breaks (blank lines) for natural pausing. No markdown."
        ),
    },
    "tl": {
        "system": (
            "Ikaw ay isang espesyalista sa Tagalog na sumusulat ng plain text na angkop para sa text-to-speech synthesis.\n\n"
            "Ang iyong trabaho:\n"
            "- Basahin ang markdown radio script na ibinigay\n"
            "- Isulat muli ito bilang natural na flowing prose SA TAGALOG LAMANG — walang markdown\n"
            "- WALANG markdown: walang headings (#), walang bullet points (-), walang asterisks (*), walang bold/italic\n"
            "- Para sa mga English proper nouns o teknikal na termino, i-spell ang mga ito nang phonetically sa Tagalog:\n"
            "  - PAGASA → pa-ga-sa\n"
            "  - Northern Luzon → nor-dern lu-son\n"
            "  - Signal Number One / Two / Three → sig-nal nam-ber wan / tu / tri\n"
            "  - tropical depression → tro-pi-kal di-pre-syon\n"
            "  - tropical storm → tro-pi-kal storm\n"
            "  - kilometers per hour → ki-lo-me-tro ba-wat o-ras\n"
            "  - northeast / southeast / northwest / southwest → nor-ist / sow-ist / nor-west / sow-west\n"
            "- Panatilihin ang paragraph structure: blank lines sa pagitan ng mga paragraph\n"
            "- HUWAG magdagdag ng anumang texto na wala sa orihinal na script\n"
            "- Output: plain text lamang, walang anumang markup o formatting characters"
        ),
        "user": (
            "Basahin ang markdown radio script na ito at isulat muli ito bilang TTS-ready plain Tagalog text.\n\n"
            "{markdown}\n\n"
            "Isulat ang plain Tagalog text ngayon. Tagalog na salita lamang, phonetically spelled kung "
            "kinakailangan, paragraph breaks (blank lines) para sa natural na pausing. Walang markdown."
        ),
    },
    "ceb": {
        "system": (
            "Ikaw usa ka espesyalista sa Cebuano nga nagsulat og plain text nga angay para sa text-to-speech synthesis.\n\n"
            "Ang imong trabaho:\n"
            "- Basaha ang markdown radio script nga gihatag\n"
            "- Isulat kini pag-usab isip natural nga flowing prose SA CEBUANO LAMANG — walay markdown\n"
            "- WALA markdown: wala headings (#), wala bullet points (-), wala asterisks (*), wala bold/italic\n"
            "- Para sa mga English proper nouns o teknikal nga termino, i-spell sila phonetically sa Cebuano:\n"
            "  - PAGASA → pa-ga-sa\n"
            "  - Northern Luzon → nor-dern lu-son\n"
            "  - Signal Number One / Two / Three → sig-nal nam-ber wan / tu / tri\n"
            "  - tropical depression → tro-pi-kal di-pre-syon\n"
            "  - tropical storm → tro-pi-kal storm\n"
            "  - kilometers per hour → ki-lo-me-tros sa usa ka oras\n"
            "  - northeast / southeast / northwest / southwest → nor-ist / sow-ist / nor-west / sow-west\n"
            "- Pahimusa ang paragraph structure: blank lines tali sa mga paragraph\n"
            "- AYAW pagdugang og bisan unsa nga texto nga wala sa orihinal nga script\n"
            "- Output: plain text lamang, walay bisan unsang markup o formatting characters"
        ),
        "user": (
            "Basaha kining markdown radio script ug isulat kini pag-usab isip TTS-ready plain Cebuano text.\n\n"
            "{markdown}\n\n"
            "Isulat ang plain Cebuano text karon. Cebuano nga pulong lamang, phonetically spelled kung "
            "kinahanglan, paragraph breaks (blank lines) para sa natural nga pausing. Walay markdown."
        ),
    },
}


def _wait_for_ollama(retries: int = 60, delay: float = 1.0) -> None:
    for _ in range(retries):
        try:
            requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
            return
        except requests.exceptions.ConnectionError:
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
    """Generate a ~750-word radio broadcast script in the target language."""
    p = _RADIO_PROMPTS[language]
    return _call_ollama_chat(
        system=p["system"],
        user=p["user"].format(markdown=markdown),
    )


def _generate_tts_text(radio_md: str, language: str) -> str:
    """Convert radio script markdown to TTS-optimised dialect-pure plain text."""
    p = _TTS_PROMPTS[language]
    return _call_ollama_chat(
        system=p["system"],
        user=p["user"].format(markdown=radio_md),
    )


@app.cls(
    image=ollama_image,
    gpu="A10G",
    volumes=OLLAMA_MOUNTS,
    timeout=3600,
)
class Step2Scripts:
    @modal.enter()
    def start_ollama(self) -> None:
        import os
        os.environ["OLLAMA_MODELS"] = str(OLLAMA_MODELS_PATH)
        subprocess.Popen(["ollama", "serve"])
        _wait_for_ollama()
        print("[Step2Scripts] Ollama ready")

    @modal.method()
    def run(self, stem: str) -> str:
        """Generate radio scripts and TTS plain text for all 3 languages.

        Reads:   /output/{stem}/ocr.md
        Writes:  /output/{stem}/radio_{lang}.md   (× 3)
                 /output/{stem}/tts_{lang}.txt     (× 3)

        Skips a language if both output files already exist.

        Returns:
            stem string.
        """
        out_dir = OUTPUT_PATH / stem
        ocr_md = (out_dir / "ocr.md").read_text(encoding="utf-8")

        for lang in LANGUAGES:
            radio_path = out_dir / f"radio_{lang}.md"
            tts_path = out_dir / f"tts_{lang}.txt"

            if radio_path.exists() and tts_path.exists():
                print(f"[Step2Scripts] {stem}/{lang}: already exists, skipping")
                continue

            radio_md = _generate_radio_script(ocr_md, lang)
            radio_path.write_text(radio_md, encoding="utf-8")

            tts_text = _generate_tts_text(radio_md, lang)
            tts_path.write_text(tts_text, encoding="utf-8")

            print(f"[Step2Scripts] {stem}/{lang}: wrote radio + tts files")

        output_volume.commit()
        return stem
