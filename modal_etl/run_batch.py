"""WeatherSpeak PH — Modal batch ETL entrypoint.

Usage:
    # Initialise volumes (first time only):
    uv run modal run modal_etl/setup_volumes.py::setup_ollama_volume
    uv run modal run modal_etl/setup_volumes.py::setup_tts_volume

    # Run the full batch:
    uv run modal run modal_etl/run_batch.py

    # Process fewer events (override N_EVENTS):
    uv run modal run modal_etl/run_batch.py --n 3

    # Force re-run all steps even if outputs already exist:
    uv run modal run modal_etl/run_batch.py --n 1 --force
"""
import datetime
import sys
import time
from pathlib import Path

from modal_etl.app import app
from modal_etl.bulletin_selector import get_bulletin_by_stem, get_latest_bulletins
from modal_etl.config import N_EVENTS, LANGUAGES
from modal_etl.step1_ocr import Step1OCR
from modal_etl.step2_scripts import step2_scripts
from modal_etl.step3_tts import step3_tts
from modal_etl.step4_upload import step4_upload

# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

_LANG_LABEL = {"ceb": "Cebuano", "tl": "Tagalog", "en": "English"}


def _fmt_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"


def _fmt_dt(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _write_report(
    run_start: datetime.datetime,
    run_end: datetime.datetime,
    n_requested: int,
    force: bool,
    results: list[dict],
) -> Path:
    """Write a Markdown ETL run report and return the file path."""
    total_elapsed = (run_end - run_start).total_seconds()
    timestamp = run_start.strftime("%Y%m%d_%H%M%S")
    reports_dir = Path("data/etl_reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"etl_report_{timestamp}.md"

    ok_count = sum(1 for r in results if r["overall"] == "ok")
    fail_count = len(results) - ok_count

    lines: list[str] = []

    # Header
    lines += [
        "# WeatherSpeak PH — ETL Run Report",
        "",
        f"**Started:**   {_fmt_dt(run_start)}",
        f"**Finished:**  {_fmt_dt(run_end)}",
        f"**Duration:**  {_fmt_elapsed(total_elapsed)}",
        f"**Bulletins:** {len(results)} processed"
        + (f" / {n_requested} requested" if n_requested != len(results) else ""),
        f"**Force:**     {'yes' if force else 'no'}",
        f"**Result:**    {'✅ all ok' if fail_count == 0 else f'⚠️ {ok_count} ok, {fail_count} failed'}",
        "",
        "---",
        "",
    ]

    # Per-bulletin sections
    for r in results:
        stem = r["stem"]
        status_icon = "✅" if r["overall"] == "ok" else "❌"
        lines += [
            f"## {status_icon} {stem}",
            "",
        ]

        steps = r["steps"]

        # Step 1
        s1 = steps.get("step1_ocr", {})
        icon = "✅" if s1.get("status") == "ok" else "❌"
        lines.append(f"### {icon} Step 1 — OCR  `{_fmt_elapsed(s1.get('elapsed_s', 0))}`")
        if s1.get("status") == "ok":
            lines += [
                "| File | Notes |",
                "|------|-------|",
                "| `ocr.md` | Bulletin text extracted by Gemma 4 E4B |",
                "| `chart.png` | Storm track chart |",
                "| `metadata.json` | Structured storm metadata |",
            ]
        else:
            lines.append(f"> ❌ Failed: {s1.get('error', 'unknown error')}")
        lines.append("")

        # Step 2
        s2 = steps.get("step2_scripts", {})
        icon = "✅" if s2.get("status") == "ok" else "❌"
        lines.append(f"### {icon} Step 2 — Scripts  `{_fmt_elapsed(s2.get('elapsed_s', 0))}` (3 languages in parallel)")
        if s2.get("status") == "ok":
            lines += [
                "| File | Description |",
                "|------|-------------|",
            ]
            for lang in LANGUAGES:
                label = _LANG_LABEL[lang]
                lines.append(f"| `radio_{lang}.md` | {label} radio script (~300 words) |")
            for lang in LANGUAGES:
                label = _LANG_LABEL[lang]
                lines.append(f"| `tts_{lang}.txt` | {label} TTS plain text (phonetically spelled) |")
        else:
            lines.append(f"> ❌ Failed: {s2.get('error', 'unknown error')}")
        lines.append("")

        # Step 3
        s3 = steps.get("step3_tts", {})
        icon = "✅" if s3.get("status") == "ok" else "❌"
        lines.append(f"### {icon} Step 3 — TTS Synthesis  `{_fmt_elapsed(s3.get('elapsed_s', 0))}` (3 languages in parallel)")
        if s3.get("status") == "ok":
            lines += [
                "| File | Synthesizer | Est. duration |",
                "|------|-------------|---------------|",
                "| `audio_ceb.mp3` | Facebook MMS VITS | ~2 min |",
                "| `audio_tl.mp3` | Facebook MMS VITS | ~2 min |",
                "| `audio_en.mp3` | Coqui XTTS v2 (Damien Black) | ~2 min |",
            ]
        else:
            lines.append(f"> ❌ Failed: {s3.get('error', 'unknown error')}")
        lines.append("")

        # Step 4
        s4 = steps.get("step4_upload", {})
        icon = "✅" if s4.get("status") == "ok" else "❌"
        lines.append(f"### {icon} Step 4 — Upload to Supabase  `{_fmt_elapsed(s4.get('elapsed_s', 0))}`")
        if s4.get("status") == "ok":
            lines += [
                "| Destination | Contents |",
                "|-------------|----------|",
                f"| Supabase Storage `{stem.replace('#', '_')}/` | chart.png, audio × 3, scripts × 3, tts text × 3 |",
                "| Supabase DB `storms` | Storm row upserted |",
                "| Supabase DB `bulletins` | Bulletin row upserted |",
                "| Supabase DB `bulletin_media` | 3 media rows (CEB / TL / EN) set to `ready` |",
            ]
        else:
            lines.append(f"> ❌ Failed: {s4.get('error', 'unknown error')}")
        lines.append("")

        # Bulletin total
        total_s = sum(
            steps[k].get("elapsed_s", 0)
            for k in ("step1_ocr", "step2_scripts", "step3_tts", "step4_upload")
            if k in steps
        )
        lines += [
            f"**Bulletin total:** {_fmt_elapsed(total_s)}",
            "",
            "---",
            "",
        ]

    # Summary table
    lines += [
        "## Summary",
        "",
        "| Bulletin | Step 1 | Step 2 | Step 3 | Step 4 | Total |",
        "|----------|--------|--------|--------|--------|-------|",
    ]
    for r in results:
        steps = r["steps"]
        def cell(key: str) -> str:
            s = steps.get(key, {})
            icon = "✅" if s.get("status") == "ok" else ("❌" if s else "—")
            t = _fmt_elapsed(s.get("elapsed_s", 0)) if s else "—"
            return f"{icon} {t}"
        total_s = sum(
            steps[k].get("elapsed_s", 0)
            for k in ("step1_ocr", "step2_scripts", "step3_tts", "step4_upload")
            if k in steps
        )
        short_stem = r["stem"].split("_", 2)[-1]  # drop "PAGASA_YY-" prefix
        lines.append(
            f"| `{short_stem}` "
            f"| {cell('step1_ocr')} "
            f"| {cell('step2_scripts')} "
            f"| {cell('step3_tts')} "
            f"| {cell('step4_upload')} "
            f"| {_fmt_elapsed(total_s)} |"
        )

    lines += [
        "",
        f"**Total run time:** {_fmt_elapsed(total_elapsed)}",
        "",
        f"*Generated by WeatherSpeak PH ETL — {_fmt_dt(run_end)}*",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

@app.local_entrypoint()
def main(n: int = N_EVENTS, force: bool = False, stem: str = "", step: int = 0, backend: str = "gemma4") -> None:
    """Process the newest N severe weather events end-to-end.

    For each event:
      Step 1: OCR the latest bulletin PDF → ocr.md, chart.png, metadata.json
      Step 2: Generate radio scripts + TTS text → radio_{lang}.md + tts_{lang}.txt
      Step 3: Synthesize MP3s in parallel (CEB, TL, EN) → audio_{lang}.mp3
      Step 4: Upload artifacts to Supabase Storage + write DB rows

    All intermediate artifacts are stored in the weatherspeak-output Modal Volume.
    Published artifacts land in Supabase Storage (weatherspeak-public bucket).
    A Markdown run report is written locally: etl_report_{timestamp}.md

    Args:
        n:     Number of most-recent bulletins to process (default: N_EVENTS).
        force: Re-run all steps even if outputs already exist.
        stem:  Process a single specific bulletin by stem, e.g.
               "PAGASA_25-TC22_Verbena_TCB#24". Overrides --n.
        step:  Run only a specific step (1-4). Default 0 runs all steps.
    """
    run_start = datetime.datetime.now()

    if stem:
        print(f"Looking up bulletin by stem: {stem}")
        bulletins = [get_bulletin_by_stem(stem)]
    else:
        print(f"Selecting newest {n} severe weather events from bulletin archive...")
        bulletins = get_latest_bulletins(n)

    if not bulletins:
        print("No bulletins found. Check ARCHIVE_API_URL in config.py.")
        sys.exit(1)

    print(f"Processing {len(bulletins)} bulletins{' (force=True)' if force else ''}:")
    for b in bulletins:
        print(f"  {b.stem}")

    ocr = Step1OCR()

    results: list[dict] = []

    for bulletin in bulletins:
        stem = bulletin.stem
        print(f"\n--- {stem} ---")
        bulletin_result: dict = {"stem": stem, "overall": "ok", "steps": {}}

        # Step 1
        if step in (0, 1):
            print("  Step 1: OCR + chart + metadata...")
            t0 = time.time()
            try:
                stem = ocr.run.remote(bulletin.pdf_url, force=force, backend=backend)
                bulletin_result["steps"]["step1_ocr"] = {
                    "status": "ok",
                    "elapsed_s": round(time.time() - t0, 1),
                }
            except Exception as exc:
                bulletin_result["steps"]["step1_ocr"] = {
                    "status": "failed",
                    "elapsed_s": round(time.time() - t0, 1),
                    "error": str(exc),
                }
                bulletin_result["overall"] = "failed"
                print(f"  ❌ Step 1 failed: {exc}")
                results.append(bulletin_result)
                continue

        # Step 2
        if step in (0, 2):
            print("  Step 2: Radio scripts + TTS text (3 languages in parallel)...")
            t0 = time.time()
            try:
                list(step2_scripts.starmap([(stem, lang, force) for lang in LANGUAGES]))
                bulletin_result["steps"]["step2_scripts"] = {
                    "status": "ok",
                    "elapsed_s": round(time.time() - t0, 1),
                }
            except Exception as exc:
                bulletin_result["steps"]["step2_scripts"] = {
                    "status": "failed",
                    "elapsed_s": round(time.time() - t0, 1),
                    "error": str(exc),
                }
                bulletin_result["overall"] = "failed"
                print(f"  ❌ Step 2 failed: {exc}")
                results.append(bulletin_result)
                continue

        # Step 3
        if step in (0, 3):
            print("  Step 3: TTS synthesis (3 languages in parallel)...")
            t0 = time.time()
            try:
                list(step3_tts.starmap([(stem, lang, force) for lang in LANGUAGES]))
                bulletin_result["steps"]["step3_tts"] = {
                    "status": "ok",
                    "elapsed_s": round(time.time() - t0, 1),
                }
            except Exception as exc:
                bulletin_result["steps"]["step3_tts"] = {
                    "status": "failed",
                    "elapsed_s": round(time.time() - t0, 1),
                    "error": str(exc),
                }
                bulletin_result["overall"] = "failed"
                print(f"  ❌ Step 3 failed: {exc}")
                results.append(bulletin_result)
                continue

        # Step 4
        if step in (0, 4):
            print("  Step 4: Upload to Supabase Storage + DB...")
            t0 = time.time()
            try:
                stem = step4_upload.remote(stem, force=force)
                bulletin_result["steps"]["step4_upload"] = {
                    "status": "ok",
                    "elapsed_s": round(time.time() - t0, 1),
                }
            except Exception as exc:
                bulletin_result["steps"]["step4_upload"] = {
                    "status": "failed",
                    "elapsed_s": round(time.time() - t0, 1),
                    "error": str(exc),
                }
                bulletin_result["overall"] = "failed"
                print(f"  ❌ Step 4 failed: {exc}")

        results.append(bulletin_result)
        print(f"  Done: {stem}")

    run_end = datetime.datetime.now()

    # Write report
    report_path = _write_report(run_start, run_end, len(bulletins), force, results)
    print(f"\nBatch complete. Artifacts published to Supabase.")
    print(f"Report: {report_path.absolute()}")
