# Multi-Bulletin History Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show all historical bulletins for a storm in the web UI, with only the latest bulletin receiving full WeatherSpeak treatment (audio + translations). Historical bulletins are registered as lightweight DB rows and link directly to the original PAGASA PDF.

**Architecture:** ETL discovery pass runs after Step 4, upserts all historical bulletins as minimal `bulletins` rows with inferred dates. Web UI bulletin history list links to PAGASA PDFs for those rows. No schema changes required.

**Tech Stack:** Python (Modal ETL), TypeScript/Next.js (web), Supabase (PostgreSQL)

---

## Background

PAGASA issues a new bulletin every 6 hours during active storms. A single storm like Typhoon Basyang can have 23 bulletins over its lifetime. Currently, the ETL processes only the latest bulletin per storm — the other 22 are invisible to users.

The storm page already has a "Bulletin History" section but it renders empty because no historical rows exist in the DB.

---

## Phase I — What This Spec Covers

Show all bulletins in the history list. Only the latest gets audio and translations. Historical bulletins link to the PAGASA PDF.

## Phase II — Documented for Later

Full backfill OCR + storm summary audio. See implementation notes at the bottom of this spec and the memory file `project_phase2_storm_summary.md`.

---

## Data Model

No schema changes. The `bulletins` table already has all needed columns:

| Column | Latest bulletin | Historical (lightweight) |
|--------|----------------|--------------------------|
| `storm_id` | ✅ set | ✅ set |
| `stem` | ✅ set | ✅ set |
| `bulletin_number` | ✅ set | ✅ set |
| `bulletin_type` | ✅ set | ✅ set (from filename) |
| `pdf_url` | ✅ set | ✅ set |
| `issued_at` | ✅ accurate (from OCR) | ✅ inferred (±6h) |
| `category`, `wind_signal`, position, etc. | ✅ set | NULL |
| `bulletin_media` rows | ✅ 3 rows (EN/TL/CEB) | none |

**Distinguishing latest from historical:** A bulletin has full treatment if and only if `bulletin_media` rows exist for it. The web layer uses this to decide whether to link to `/bulletins/[id]` or directly to `pdf_url`.

---

## ETL Changes

### `modal_etl/bulletin_selector.py`

Add a new function alongside `get_latest_bulletins`:

```python
def get_all_bulletins_for_storm(storm_id: str, event_name: str) -> list[BulletinInfo]:
    """Return ALL bulletins for a specific storm event, sorted by sequence ascending."""
```

- Queries the same GitHub archive API
- Filters to bulletins matching `storm_id` and `event_name`
- Returns all of them, sorted by `bulletin_seq` ascending (oldest first)
- Fills `pdf_url` for each entry

### `modal_etl/run_batch.py`

After Step 4 completes successfully for a bulletin, run a discovery pass:

```python
# After step4_upload succeeds:
_discover_historical_bulletins(stem, parsed_latest, latest_issued_at, client)
```

The discovery helper:
1. Calls `get_all_bulletins_for_storm(storm_id, event_name)` 
2. Filters out the latest bulletin (already processed)
3. Infers `issued_at` for each: `latest_issued_at - (latest_num - hist_num) * 6 hours`
4. Upserts each as a lightweight `bulletins` row (no `bulletin_media`)

The discovery pass is best-effort — failure does not abort or fail the main bulletin result.

### `modal_etl/step4_upload.py`

Add a `step4_discover_bulletins` Modal function (or inline helper) that performs lightweight bulletin upserts:

```python
def _upsert_lightweight_bulletin(client, storm_id, info: BulletinInfo, issued_at: datetime) -> None:
    """Upsert a historical bulletin with minimal metadata. No bulletin_media rows."""
    bulletin_row = {
        "storm_id": storm_id,
        "stem": info.stem,
        "bulletin_type": ...,  # parsed from stem
        "bulletin_number": info.bulletin_seq,
        "issued_at": issued_at.isoformat(),
        "pdf_url": info.pdf_url,
    }
    client.table("bulletins").upsert(bulletin_row, on_conflict="stem").execute()
```

---

## Web Changes

### `web/lib/supabase/queries.ts`

`getStormDetail` — add `pdf_url` to the `bulletinHistory` shape:

```typescript
bulletinHistory: rest.map(b => ({
  id: b.id,
  bulletin_number: b.bulletin_number,
  issued_at: b.issued_at,
  pdf_url: b.pdf_url,          // ← add this
})),
```

Update the `StormDetail` interface accordingly.

### `web/app/storms/[stormId]/page.tsx`

History list: use `<a href={b.pdf_url} target="_blank">` instead of `<Link href={/bulletins/${b.id}}>` for historical bulletins.

Each row shows:
- Bulletin number (e.g. "Bulletin #5")
- Inferred date (e.g. "Apr 10, 2026 · 5:00 PM")
- "PDF ↗" indicator (small, muted)

The latest bulletin is unaffected — still shown as the hero with full audio.

---

## What Stays the Same

- `bulletin_selector.get_latest_bulletins(n)` — unchanged, still drives the main batch loop
- Steps 1–4 pipeline — unchanged
- `/bulletins/[bulletinId]` page — unchanged (only reachable via latest bulletin)
- `BulletinAudioSection`, `AudioPlayer` — unchanged

---

## Phase II Notes — Storm Summary Audio

When ready to implement Phase II:

**Find bulletins needing backfill:**
```sql
SELECT b.*
FROM bulletins b
WHERE b.storm_id = '<target_storm_id>'
  AND b.id NOT IN (SELECT bulletin_id FROM bulletin_media)
ORDER BY b.bulletin_number ASC;
```

**Steps:**
1. Run `Step1OCR` on each lightweight bulletin row (using `pdf_url`) to get real `issued_at` + `ocr.md`
2. Feed all `ocr.md` files (sorted by bulletin_number) into a new Gemma 4 prompt for storm lifecycle narrative
3. Convert narrative to TL/CEB audio via Step 3 pipeline
4. Upload and link to the storm row

**CLI flag to add to `run_batch.py`:**
```bash
uv run modal run modal_etl/run_batch.py --backfill-ocr --storm <storm_code>
```

The "🎙 Storm Summary Audio" stub in `web/app/storms/[stormId]/page.tsx` is already in place — Phase II just populates it.

---

## Files Touched

| File | Change |
|------|--------|
| `modal_etl/bulletin_selector.py` | Add `get_all_bulletins_for_storm()` |
| `modal_etl/run_batch.py` | Add discovery pass after Step 4 |
| `modal_etl/step4_upload.py` | Add `_upsert_lightweight_bulletin()` helper |
| `web/lib/supabase/queries.ts` | Add `pdf_url` to `bulletinHistory` shape |
| `web/app/storms/[stormId]/page.tsx` | History list links to `pdf_url` with PDF indicator |
