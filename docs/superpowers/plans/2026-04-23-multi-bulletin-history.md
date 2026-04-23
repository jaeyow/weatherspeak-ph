# Multi-Bulletin History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show all historical bulletins for a storm in the web UI, with only the latest bulletin receiving full WeatherSpeak treatment; historical bulletins are registered as lightweight DB rows linking to the original PAGASA PDF.

**Architecture:** After Step 4 completes in the ETL, a discovery pass fetches all bulletin filenames for the storm from the GitHub archive, infers their issued_at timestamps (6 hours apart), and upserts minimal rows into the `bulletins` table. The storm page history list links those rows directly to their PAGASA PDF. No schema changes required — `pdf_url` already exists on the `bulletins` table.

**Tech Stack:** Python/Modal (ETL), TypeScript/Next.js (web), Supabase PostgreSQL (DB), GitHub archive API (bulletin discovery), `uv run pytest` (test runner)

---

## File Map

| File | Change |
|------|--------|
| `modal_etl/bulletin_selector.py` | Add `get_all_bulletins_for_storm()` |
| `modal_etl/step4_upload.py` | Add `_infer_issued_at()` + `_discover_historical_bulletins()`, call discovery at end of `step4_upload()` |
| `tests/test_step4_upload.py` | New — tests for `_infer_issued_at()` |
| `tests/test_bulletin_selector.py` | Add tests for `get_all_bulletins_for_storm()` |
| `web/lib/supabase/queries.ts` | Add `pdf_url` to `bulletinHistory` shape in `getStormDetail` |
| `web/app/storms/[stormId]/page.tsx` | History list items link to `pdf_url` |

---

## Task 1: `_infer_issued_at()` helper + tests

**Files:**
- Create: `tests/test_step4_upload.py`
- Modify: `modal_etl/step4_upload.py` (add function before `_upload_file`)

Context: PAGASA issues bulletins every 6 hours. Given the latest bulletin's timestamp and numbers, we can estimate any historical bulletin's timestamp. This is a pure function — easy to TDD without mocking.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_step4_upload.py`:

```python
# tests/test_step4_upload.py
import datetime
import pytest
from modal_etl.step4_upload import _infer_issued_at


def _utc(year, month, day, hour=0) -> datetime.datetime:
    return datetime.datetime(year, month, day, hour, 0, 0,
                             tzinfo=datetime.timezone.utc)


def test_infer_issued_at_same_bulletin_number():
    """When hist_num == latest_num, result equals latest."""
    latest = _utc(2026, 4, 22, 23)
    result = _infer_issued_at(latest, latest_num=5, hist_num=5)
    assert result == latest


def test_infer_issued_at_one_bulletin_back():
    """One bulletin back = 6 hours earlier."""
    latest = _utc(2026, 4, 22, 23)
    result = _infer_issued_at(latest, latest_num=23, hist_num=22)
    assert result == _utc(2026, 4, 22, 17)


def test_infer_issued_at_many_bulletins_back():
    """Bulletin #1 of 23 = 22 steps × 6 h = 132 h earlier."""
    latest = _utc(2026, 4, 22, 23)
    result = _infer_issued_at(latest, latest_num=23, hist_num=1)
    expected = latest - datetime.timedelta(hours=132)
    assert result == expected


def test_infer_issued_at_preserves_timezone():
    """Result keeps the timezone of latest_issued_at."""
    tz = datetime.timezone(datetime.timedelta(hours=8))
    latest = datetime.datetime(2026, 4, 22, 23, 0, 0, tzinfo=tz)
    result = _infer_issued_at(latest, latest_num=3, hist_num=1)
    assert result.tzinfo == tz
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_step4_upload.py -v
```

Expected: `ImportError` or `AttributeError` — `_infer_issued_at` does not exist yet.

- [ ] **Step 3: Add `_infer_issued_at()` to `modal_etl/step4_upload.py`**

Add this function directly before the `_upload_file` function (around line 81):

```python
def _infer_issued_at(
    latest_issued_at: "datetime.datetime",
    latest_num: int,
    hist_num: int,
) -> "datetime.datetime":
    """Estimate issued_at for a historical bulletin at 6-hour intervals."""
    import datetime as _dt
    return latest_issued_at - _dt.timedelta(hours=6 * (latest_num - hist_num))
```

Also add `import datetime` at the top of the file if not already present (it is not — add it after the existing imports).

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_step4_upload.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add modal_etl/step4_upload.py tests/test_step4_upload.py
git commit -m "feat: add _infer_issued_at helper for historical bulletin timestamps"
```

---

## Task 2: `get_all_bulletins_for_storm()` in bulletin_selector.py + tests

**Files:**
- Modify: `modal_etl/bulletin_selector.py`
- Modify: `tests/test_bulletin_selector.py`

Context: The existing `get_latest_bulletins(n)` fetches all bulletins and picks the highest-sequence one per storm. The new function filters by storm and returns all bulletins sorted ascending. It shares the same GitHub API call pattern.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_bulletin_selector.py`:

```python
from modal_etl.bulletin_selector import get_all_bulletins_for_storm

# Use the same FAKE_TREE already defined in this file (Pepito has #01 and #02,
# Basyang has only #01).

def test_get_all_bulletins_for_storm_returns_all_for_event():
    """Returns all bulletins for the requested storm, not just the latest."""
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_all_bulletins_for_storm("20-19W", "Pepito")
    assert len(results) == 2


def test_get_all_bulletins_for_storm_sorted_ascending():
    """Results are sorted by bulletin_seq ascending (oldest first)."""
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_all_bulletins_for_storm("20-19W", "Pepito")
    seqs = [r.bulletin_seq for r in results]
    assert seqs == sorted(seqs)


def test_get_all_bulletins_for_storm_excludes_other_storms():
    """Does not include bulletins for a different storm."""
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_all_bulletins_for_storm("20-19W", "Pepito")
    stems = [r.stem for r in results]
    assert not any("Basyang" in s for s in stems)


def test_get_all_bulletins_for_storm_pdf_urls_encoded():
    """PDF URLs must not contain bare # characters."""
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_all_bulletins_for_storm("20-19W", "Pepito")
    for r in results:
        assert "#" not in r.pdf_url
        assert r.pdf_url.startswith("https://raw.githubusercontent.com")


def test_get_all_bulletins_for_storm_returns_empty_for_unknown():
    """Returns empty list when no bulletins match the requested storm."""
    with patch("modal_etl.bulletin_selector.requests.get") as mock_get:
        mock_get.return_value.json.return_value = FAKE_TREE
        mock_get.return_value.raise_for_status = lambda: None
        results = get_all_bulletins_for_storm("99-ZZ", "Unknown")
    assert results == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_bulletin_selector.py::test_get_all_bulletins_for_storm_returns_all_for_event -v
```

Expected: `ImportError` — `get_all_bulletins_for_storm` does not exist yet.

- [ ] **Step 3: Add `get_all_bulletins_for_storm()` to `modal_etl/bulletin_selector.py`**

Add this function after `get_latest_bulletins` (around line 79):

```python
def get_all_bulletins_for_storm(storm_id: str, event_name: str) -> list[BulletinInfo]:
    """Return ALL bulletins for a specific storm event, sorted by bulletin_seq ascending.

    Args:
        storm_id:   Archive storm identifier, e.g. "20-19W" or "22-TC02".
                    This is the second underscore-segment of the filename,
                    e.g. from "PAGASA_20-19W_Pepito_SWB#01.pdf".
        event_name: Storm name, e.g. "Pepito" or "Basyang".
    """
    resp = requests.get(ARCHIVE_API_URL)
    resp.raise_for_status()
    tree = resp.json().get("tree", [])

    bulletins = []
    for node in tree:
        if node.get("type") != "blob":
            continue
        path = node["path"]
        info = parse_bulletin_filename(path)
        if info is None:
            continue
        if info.storm_id != storm_id or info.event_name != event_name:
            continue
        info.pdf_url = f"{ARCHIVE_RAW_BASE}/{quote(path, safe='/')}"
        bulletins.append(info)

    bulletins.sort(key=lambda b: b.bulletin_seq)
    return bulletins
```

- [ ] **Step 4: Run all bulletin_selector tests**

```bash
uv run pytest tests/test_bulletin_selector.py -v
```

Expected: all tests PASS (9 existing + 5 new = 14 total).

- [ ] **Step 5: Commit**

```bash
git add modal_etl/bulletin_selector.py tests/test_bulletin_selector.py
git commit -m "feat: add get_all_bulletins_for_storm to bulletin_selector"
```

---

## Task 3: Discovery pass in `step4_upload.py`

**Files:**
- Modify: `modal_etl/step4_upload.py`

Context: After the main `step4_upload()` function finishes (storms + bulletins + media upserted), it calls `_discover_historical_bulletins()`. This helper fetches all bulletin filenames for the storm from the GitHub archive, filters out the one just processed, infers their timestamps, and upserts lightweight rows. Failure is non-fatal — it prints a warning and continues.

The archive storm_id (e.g. "20-19W") is extracted from the stem: `decoded_stem.split("_")[1]`.
The storm name (e.g. "Pepito") is `parsed["storm_name"]`.
The latest `issued_at` ISO string comes from `bulletin_row["issued_at"]` (set earlier in the function).

- [ ] **Step 1: Add `_discover_historical_bulletins()` to `modal_etl/step4_upload.py`**

Add this function after `_infer_issued_at` and before `_upload_file`:

```python
def _discover_historical_bulletins(
    client,
    db_storm_id: str,
    archive_storm_id: str,
    event_name: str,
    latest_issued_at_iso: str | None,
    latest_num: int,
) -> None:
    """Upsert lightweight bulletin rows for all historical bulletins of a storm.

    Args:
        client:               Supabase client (already authenticated).
        db_storm_id:          UUID of the storm row in Supabase.
        archive_storm_id:     Archive ID like "20-19W" or "22-TC02".
        event_name:           Storm name like "Pepito" or "Basyang".
        latest_issued_at_iso: ISO 8601 string for the latest bulletin's issued_at.
        latest_num:           Bulletin sequence number of the already-processed bulletin.
    """
    import datetime as _dt
    from modal_etl.bulletin_selector import get_all_bulletins_for_storm

    all_bulletins = get_all_bulletins_for_storm(archive_storm_id, event_name)
    historical = [b for b in all_bulletins if b.bulletin_seq < latest_num]

    if not historical:
        print(f"[Discovery] no historical bulletins found for {event_name}")
        return

    latest_dt: _dt.datetime | None = None
    if latest_issued_at_iso:
        try:
            from dateutil import parser as dtparser
            latest_dt = dtparser.parse(latest_issued_at_iso)
        except Exception:
            pass

    for info in historical:
        issued_at_iso: str | None = None
        if latest_dt is not None:
            inferred = _infer_issued_at(latest_dt, latest_num, info.bulletin_seq)
            issued_at_iso = inferred.isoformat()

        raw_type = info.stem.rsplit("_", 1)[-1].split("#")[0]  # "SWB", "TCA", etc.
        btype = raw_type if raw_type in ("SWB", "TCA", "TCB") else "other"

        bulletin_row = {
            "storm_id":        db_storm_id,
            "stem":            info.stem,
            "bulletin_type":   btype,
            "bulletin_number": info.bulletin_seq,
            "issued_at":       issued_at_iso,
            "pdf_url":         info.pdf_url,
        }
        client.table("bulletins").upsert(
            bulletin_row, on_conflict="stem"
        ).execute()
        print(f"[Discovery] registered {info.stem} (issued_at≈{issued_at_iso})")
```

- [ ] **Step 2: Call `_discover_historical_bulletins()` at the end of `step4_upload()`**

In `step4_upload.py`, find the final `print(f"[Step4Upload] {decoded_stem}: done")` line (currently the last line of the function, around line 276). Add the discovery call immediately before it:

```python
    # ------------------------------------------------------------------
    # Discovery pass: register all historical bulletins as lightweight rows
    # ------------------------------------------------------------------
    archive_storm_id = decoded_stem.split("_")[1]   # e.g. "20-19W"
    try:
        _discover_historical_bulletins(
            client=client,
            db_storm_id=storm_id,
            archive_storm_id=archive_storm_id,
            event_name=parsed["storm_name"],
            latest_issued_at_iso=bulletin_row["issued_at"],
            latest_num=parsed["bulletin_number"],
        )
    except Exception as exc:
        print(f"[Discovery] non-fatal error: {exc}")

    print(f"[Step4Upload] {decoded_stem}: done")
    return stem
```

- [ ] **Step 3: Run the full test suite to make sure nothing is broken**

```bash
uv run pytest tests/ -v
```

Expected: all previously passing tests still PASS. No new tests for this task — `_discover_historical_bulletins` orchestrates DB calls that require a real Supabase client, which is tested by running the ETL end-to-end.

- [ ] **Step 4: Commit**

```bash
git add modal_etl/step4_upload.py
git commit -m "feat: add historical bulletin discovery pass to step4_upload"
```

---

## Task 4: Add `pdf_url` to `bulletinHistory` in `queries.ts`

**Files:**
- Modify: `web/lib/supabase/queries.ts`

Context: `getStormDetail` currently returns `bulletinHistory` with `{ id, bulletin_number, issued_at }`. The storm page needs `pdf_url` to link each historical bulletin to its PAGASA PDF. The `pdf_url` column already exists on the `bulletins` table.

- [ ] **Step 1: Update the `StormDetail` interface in `queries.ts`**

Find the `StormDetail` interface (lines 43–48). Change `bulletinHistory`:

```typescript
export interface StormDetail {
  storm: StormWithStatus;
  latestBulletin: Bulletin;
  latestMedia: MediaByLang;
  bulletinHistory: Array<{
    id: string;
    bulletin_number: number | null;
    issued_at: string | null;
    pdf_url: string | null;        // ← add this
  }>;
}
```

- [ ] **Step 2: Add `pdf_url` to the `bulletinHistory` map in `getStormDetail`**

Find the return statement in `getStormDetail` (around line 71). Change `bulletinHistory`:

```typescript
  return {
    storm: storm as StormWithStatus,
    latestBulletin: latest,
    latestMedia: toMediaByLang(latest.bulletin_media ?? []),
    bulletinHistory: rest.map(b => ({
      id: b.id,
      bulletin_number: b.bulletin_number,
      issued_at: b.issued_at,
      pdf_url: b.pdf_url ?? null,    // ← add this
    })),
  };
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add web/lib/supabase/queries.ts
git commit -m "feat: expose pdf_url in bulletinHistory from getStormDetail"
```

---

## Task 5: Storm page history list links to PAGASA PDF

**Files:**
- Modify: `web/app/storms/[stormId]/page.tsx`

Context: The bulletin history section (lines 82–100) currently wraps each item in a `<Link href={/bulletins/${b.id}}>`. Historical bulletins now have `pdf_url` set, so they should open the original PAGASA PDF in a new tab instead. The latest bulletin is not in the history list — it's shown as the hero — so all history items can safely link to `pdf_url`.

- [ ] **Step 1: Replace the history list with PDF links**

Find the bulletin history section in `web/app/storms/[stormId]/page.tsx` (lines 82–100):

```tsx
      {/* Bulletin history */}
      {bulletinHistory.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
            <PageLabel k="past_bulletins" />
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
```

Replace it with:

```tsx
      {/* Bulletin history */}
      {bulletinHistory.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
            <PageLabel k="past_bulletins" />
          </h2>
          <div className="space-y-1">
            {bulletinHistory.map(b => (
              b.pdf_url ? (
                <a
                  key={b.id}
                  href={b.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex justify-between items-center px-4 py-2.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                >
                  <span className="text-sm text-white">Bulletin #{b.bulletin_number}</span>
                  <span className="text-xs text-gray-400">
                    {formatDate(b.issued_at)}
                    <span className="ml-2 text-gray-500">PDF ↗</span>
                  </span>
                </a>
              ) : (
                <Link
                  key={b.id}
                  href={`/bulletins/${b.id}`}
                  className="flex justify-between items-center px-4 py-2.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                >
                  <span className="text-sm text-white">Bulletin #{b.bulletin_number}</span>
                  <span className="text-xs text-gray-400">{formatDate(b.issued_at)}</span>
                </Link>
              )
            ))}
          </div>
        </section>
      )}
```

The `pdf_url ? <a> : <Link>` branch keeps Phase II compatibility — when a historical bulletin is later fully processed, it still has `pdf_url` but could also be navigated via `/bulletins/[id]`. For now all history rows have `pdf_url`, so the `<a>` branch always fires.

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Start the dev server and verify the history list renders**

```bash
cd web && npm run dev
```

Open `http://localhost:3000` in a browser, navigate to a storm with processed bulletins (e.g. Basyang), and verify:
- The "Past Bulletins" section shows all historical rows
- Each row displays bulletin number + date + "PDF ↗"
- Clicking a row opens the PAGASA PDF in a new tab

- [ ] **Step 4: Commit**

```bash
git add web/app/storms/[stormId]/page.tsx
git commit -m "feat: link historical bulletin rows to PAGASA PDF in storm history list"
```

---

## Self-Review

**Spec coverage:**
- ✅ ETL discovery pass registers all historical bulletins after Step 4
- ✅ Inferred issued_at (6-hour intervals)
- ✅ `pdf_url` stored for each historical row
- ✅ No schema changes
- ✅ Phase II hook documented (query `bulletins` rows with no `bulletin_media`)
- ✅ Web history list shows bulletin number + date + PDF link
- ✅ Latest bulletin unaffected (still full hero treatment)

**Placeholder scan:** None found.

**Type consistency:**
- `_infer_issued_at(latest_issued_at, latest_num, hist_num)` — used consistently in Task 1 (test) and Task 3 (call site)
- `get_all_bulletins_for_storm(storm_id, event_name)` — used consistently in Task 2 (definition) and Task 3 (import + call)
- `bulletinHistory[n].pdf_url` — added in Task 4, consumed in Task 5
