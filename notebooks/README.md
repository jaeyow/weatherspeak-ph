# OCR Experiments — WeatherSpeak PH

This directory contains Jupyter notebooks for comparing different OCR approaches on PAGASA typhoon bulletins.

## ✅ Decision: Scenario A — Vision-First Pipeline

**Gemma 4 E4B Vision has been selected as the production approach.**

Gemma 4 Vision passed the comparison with good enough accuracy on PAGASA bulletins. The vision-first pipeline means a single model handles both OCR and translation — simpler architecture, semantic understanding of storm track maps, and full alignment with the hackathon theme.

---

## 📚 Notebooks

### 01. [OCR Setup and Data Collection](01-ocr-setup-and-data.ipynb)
- Clone PAGASA bulletin archive
- Select 10 diverse sample bulletins
- Convert PDFs to images (200 DPI)
- Prepare evaluation framework

### 02. [Surya OCR Testing](02-surya-ocr.ipynb)
- Test Surya OCR (best AI-native OCR, 19.6k stars)
- Benchmark processing speed
- Extract text and measure completion
- Built for document understanding

### 03. [Marker Document Parser Testing](03-marker.ipynb)
- Replaces PaddleOCR (persistent macOS dependency/kernel crash issues)
- Handles **mixed content** — text, tables, and storm track charts
- Outputs clean Markdown with reading order preserved
- Extracts charts/figures as separate images (unlike pure-text OCR tools)

### 04. [Gemma 4 Vision Testing](04-gemma4.ipynb)
- **Winner**: Vision-language model replaces specialized OCR
- Model: `gemma4:e4b` via Ollama — good accuracy, fast local inference
- Two-step pipeline: image → markdown (Step 1), markdown → structured JSON (Step 2)
- Constrained decoding via JSON Schema guarantees valid structured output

### 05. [Comparison Analysis](05-comparison.ipynb) ✅
- Side-by-side comparison of all three approaches
- Performance metrics (speed, accuracy, structure)
- Decision matrix with weighted scores
- **Outcome: Gemma 4 Vision selected (Scenario A)**

## 🎯 Research Question

**Can Gemma 4 Vision extract text accurately enough from structured government documents (PAGASA bulletins) to replace specialized OCR engines?**

**Answer: Yes.** Gemma 4 E4B provides good enough accuracy with the benefit of semantic chart understanding — something no traditional OCR tool can match.

## 📊 Decision Framework — Resolved

### ✅ Scenario A: Vision-First Pipeline — CHOSEN
- **Result**: Gemma 4 Vision accuracy is good enough for PAGASA bulletins
- **Pipeline**: Gemma 4 E4B for OCR extraction → Gemma 4 E4B for translation
- **Key advantage**: Only Gemma 4 can semantically interpret the storm track map

### Scenario B: Hybrid Pipeline
- **IF**: Gemma 4 Vision accuracy 70-90%
- **THEN**: Use Surya/Marker for OCR → Gemma 4 for translation
- *Not needed — Scenario A passed*

### Scenario C: Pure OCR Pipeline
- **IF**: Gemma 4 Vision accuracy < 70%
- **THEN**: Use Surya/Marker for OCR → Gemma 4 for translation only
- *Not needed — Scenario A passed*

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install pdf2image pillow requests GitPython

# 2. Run notebooks in order
jupyter notebook 01-ocr-setup-and-data.ipynb

# 3. For Gemma 4 Vision (notebook 04):
brew install ollama  # macOS
ollama pull gemma4:e4b  # E4B: good accuracy, fast local inference
ollama serve

# 4. View comparison results
jupyter notebook 05-comparison.ipynb
```

## 📁 Output Structure

```
data/
├── bulletin-archive/           # Cloned PAGASA PDFs
├── sample_images/              # Converted to images (200 DPI)
├── sample_metadata.json        # Test sample catalog
├── surya_results/              # Surya OCR outputs
├── marker_results/             # Marker outputs (markdown + extracted figures)
│   └── figures/                # Storm track charts extracted from bulletins
├── gemma4_results/             # Gemma 4 Vision outputs (PRODUCTION CHOICE)
│   ├── *_markdown.md           # Raw extracted markdown per bulletin
│   ├── structured/             # Structured JSON per bulletin
│   └── gemma4_vision_results.json  # Summary metadata
└── ocr_comparison_report.json  # Final comparison report
```

## 🔗 Related Files

- [HACKATHON_PLAN.md](../HACKATHON_PLAN.md) - Overall project plan
- [devlog.md](../devlog.md) - Development progress log
- [README.md](../README.md) - Project overview
