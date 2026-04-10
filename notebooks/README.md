# OCR Experiments — WeatherSpeak PH

This directory contains Jupyter notebooks for comparing different OCR approaches on PAGASA typhoon bulletins.

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

### 03. [PaddleOCR Testing](03-paddleocr.ipynb)
- Test PaddleOCR (best traditional OCR, 75k+ stars)
- Production-grade reliability
- Confidence scores for quality assessment
- Industry-proven baseline

### 04. [Gemma 4 Vision Testing](04-gemma4-vision.ipynb)
- **Critical experiment**: Can vision-language models replace specialized OCR?
- Test Gemma 4 26B via Ollama
- Zero-shot document extraction
- Structured field extraction via prompts

### 05. [Comparison Analysis](05-comparison.ipynb)
- Side-by-side comparison of all three approaches
- Performance metrics (speed, accuracy, structure)
- Decision matrix with weighted scores
- Production architecture recommendation

## 🎯 Research Question

**Can Gemma 4 Vision extract text accurately enough from structured government documents (PAGASA bulletins) to replace specialized OCR engines?**

## 📊 Decision Framework

### Scenario A: Vision-First Pipeline
- **IF**: Gemma 4 Vision accuracy ≥ 90%
- **THEN**: Use Gemma 4 for both OCR and translation
- **PROS**: Simpler pipeline, semantic understanding, hackathon alignment

### Scenario B: Hybrid Pipeline
- **IF**: Gemma 4 Vision accuracy 70-90%
- **THEN**: Use Surya/Paddle for OCR → Gemma 4 for translation
- **PROS**: Balance accuracy and intelligence

### Scenario C: Pure OCR Pipeline
- **IF**: Gemma 4 Vision accuracy < 70%
- **THEN**: Use Surya/Paddle for OCR → Gemma 4 for translation only
- **PROS**: Proven reliability, faster processing

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install pdf2image pillow requests GitPython

# 2. Run notebooks in order
jupyter notebook 01-ocr-setup-and-data.ipynb

# 3. For Gemma 4 Vision (notebook 04):
brew install ollama  # macOS
ollama pull gemma2:27b-vision
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
├── paddleocr_results/          # PaddleOCR outputs
├── gemma4_results/             # Gemma 4 Vision outputs
└── ocr_comparison_report.json  # Final comparison
```

## ⚠️ Critical Path

The OCR decision **blocks all downstream work** for WeatherSpeak PH:
- Translation pipeline design
- TTS integration strategy
- Geographic context features
- Database schema

**Complete manual assessment in notebook 05 ASAP to unblock Week 2 implementation.**

## 📝 Manual Assessment Checklist

After running all notebooks, review:
- [ ] Text extraction accuracy (character-level)
- [ ] Storm name, category extraction
- [ ] Coordinate table handling
- [ ] Warnings and advisories completeness
- [ ] Structure preservation (headers, body, tables)
- [ ] Processing speed acceptability
- [ ] Update decision matrix scores in notebook 05
- [ ] Re-run weighted calculation
- [ ] Choose production scenario (A, B, or C)
- [ ] Update `../HACKATHON_PLAN.md` with chosen approach

## 🔗 Related Files

- [HACKATHON_PLAN.md](../HACKATHON_PLAN.md) - Overall project plan
- [devlog.md](../devlog.md) - Development progress log
- [README.md](../README.md) - Project overview
