"""WeatherSpeak PH — Modal batch ETL entrypoint.

Usage:
    # Initialise volumes (first time only):
    uv run modal run modal_etl/setup_volumes.py::setup_ollama_volume
    uv run modal run modal_etl/setup_volumes.py::setup_tts_volume

    # Run the full batch:
    uv run modal run modal_etl/run_batch.py

    # Process fewer events (override N_EVENTS):
    uv run modal run modal_etl/run_batch.py --n 3
"""
import sys

import modal

from modal_etl.app import app
from modal_etl.bulletin_selector import get_latest_bulletins
from modal_etl.config import N_EVENTS, LANGUAGES
from modal_etl.step1_ocr import Step1OCR
from modal_etl.step2_scripts import Step2Scripts
from modal_etl.step3_tts import step3_tts


@app.local_entrypoint()
def main(n: int = N_EVENTS, force: bool = False) -> None:
    """Process the newest N severe weather events end-to-end.

    For each event:
      1. OCR the latest bulletin PDF → ocr.md, chart.png, metadata.json
      2. Generate radio scripts + TTS text → radio_{lang}.md + tts_{lang}.txt
      3. Synthesize MP3s in parallel (CEB, TL, EN) → audio_{lang}.mp3

    All artifacts are stored in the weatherspeak-output Modal Volume.

    Args:
        n:     Number of most-recent bulletins to process (default: N_EVENTS).
        force: Re-run all steps even if outputs already exist in the volume.
    """
    print(f"Selecting newest {n} severe weather events from bulletin archive...")
    bulletins = get_latest_bulletins(n)

    if not bulletins:
        print("No bulletins found. Check ARCHIVE_API_URL in config.py.")
        sys.exit(1)

    print(f"Processing {len(bulletins)} bulletins{' (force=True)' if force else ''}:")
    for b in bulletins:
        print(f"  {b.stem}")

    ocr = Step1OCR()
    scripts = Step2Scripts()

    for bulletin in bulletins:
        print(f"\n--- {bulletin.stem} ---")

        print("  Step 1: OCR + chart + metadata...")
        stem = ocr.run.remote(bulletin.pdf_url, force=force)

        print("  Step 2: Radio scripts + TTS text...")
        stem = scripts.run.remote(stem, force=force)

        print("  Step 3: TTS synthesis (3 languages in parallel)...")
        list(step3_tts.starmap([(stem, lang, force) for lang in LANGUAGES]))

        print(f"  Done: {stem}")

    print("\nBatch complete. All artifacts in weatherspeak-output volume.")
