# Constrained Decoding Analysis — 2026-04-25

## Purpose
Investigate whether Ollama's constrained decoding (via `format` parameter) is effectively enforcing the `PAGASA_JSON_SCHEMA` for structured metadata extraction.

## Findings

### ✅ Schema Structure is Enforced
The constrained decoding **successfully enforces the JSON schema structure**:
- All required fields are present
- Nested objects follow the correct hierarchy
- Array items have required properties
- Enum values are respected (e.g., `bulletin_type`, `storm.category`)

### ❌ Data Quality is NOT Enforced
Constrained decoding does **NOT prevent garbage content**:

**Example from `PAGASA_25-TC02_Bising_TCA#01`:**

**Good OCR input (from markdown):**
```
| 24-Hour Forecast 2:00 PM 05 July 2025 | 20.8 | 117.7 | 430 km West of Ibayat, Batanes (OUTSIDE PAR) | 75 | TS | NS Slowly |
| 36-Hour Forecast 2:00 AM 06 July 2025 | 21.2 | 117.9 | 410 km West of Ibayat, Batanes (OUTSIDE PAR) | 75 | TS | NE Slowly |
```

**Bad structured output (from metadata.json):**
```json
{
  "hour": 24,
  "label": "2:00 PM 05 July 2025",
  "latitude": 117.7,  // WRONG: This is longitude
  "longitude": null,  // Missing
  "reference": "4             KM West of B         en Batanes, Batanes (OUTSIDE PAR)"  // Mangled
},
{
  "hour": 36,
  "label": "2forecasts_positions_36h_data_missing"  // Garbage label
}
```

## Why This Happens

1. **JSON Schema validates TYPE, not CONTENT**
   - `{"type": ["number", "null"]}` accepts ANY number, including wrong ones
   - `{"type": "string"}` accepts ANY string, including garbage

2. **OCR-to-JSON extraction is LLM-generated**
   - Gemma 4 E4B parses tables and converts to JSON
   - Even with good OCR, the model can misalign columns or hallucinate

3. **No semantic validation**
   - Schema doesn't check if `latitude` is in valid range (-90 to 90)
   - Doesn't verify if `reference` text is coherent
   - Doesn't cross-check coordinate swapping

## Impact

**Low risk for production:**
- Most files extract cleanly (e.g., Verbena TCB#24 is perfect)
- OCR quality is generally good (tables are readable)
- Radio scripts in Step 2 regenerate content from markdown, not structured JSON
- TTS in Step 3 uses radio scripts, not metadata

**Metadata is primarily for:**
- Database indexing (storm name, category, position)
- UI display (bulletin type, issuance time)
- Future analytics

## Recommendations

### 1. Add Post-Processing Validation ✅
Add validation in `step1_ocr.py` after `_generate_metadata()`:

```python
def _validate_metadata(metadata: dict) -> dict:
    """Apply semantic validation and cleanup."""
    # Fix: Ensure latitude is -90 to 90
    if metadata.get("current_position", {}).get("latitude"):
        lat = metadata["current_position"]["latitude"]
        if lat < -90 or lat > 90:
            metadata["current_position"]["latitude"] = None
    
    # Fix: Ensure longitude is -180 to 180
    if metadata.get("current_position", {}).get("longitude"):
        lon = metadata["current_position"]["longitude"]
        if lon < -180 or lon > 180:
            metadata["current_position"]["longitude"] = None
    
    # Fix: Clean up forecast positions
    for pos in metadata.get("forecast_positions", []):
        if "latitude" in pos and (pos["latitude"] < -90 or pos["latitude"] > 90):
            pos["latitude"] = None
        if "longitude" in pos and (pos["longitude"] < -180 or pos["longitude"] > 180):
            pos["longitude"] = None
        # Remove garbage labels
        if "label" in pos and ("data_missing" in pos["label"] or len(pos["label"]) < 5):
            pos["label"] = f"{pos['hour']}-hour forecast"
    
    return metadata
```

### 2. Add Confidence Scoring ✅ (Already in Schema)
The schema includes `"confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}`, but it's not being set meaningfully. Consider:
- Parse quality score based on field completeness
- Set to -1 or 0.0 if critical fields are garbage

### 3. Fallback to OCR Markdown 
For radio scripts (Step 2), always use `ocr.md` as the source, not `metadata.json`. This is already the case — confirmed in `step2_scripts.py`.

### 4. Monitor and Alert
Add ETL report warnings when:
- Required fields are null
- Coordinates are out of range
- Reference strings contain control characters or excessive whitespace
- Confidence < 0.5

## Conclusion

**Constrained decoding works as designed** — it enforces JSON structure but not data quality. The solution is **post-processing validation** and **fallback to OCR markdown** for downstream tasks.

The structured metadata is "best effort" indexing, not a replacement for the full bulletin text.
