# Image Cultural Accuracy Benchmark

**AI image models hallucinate history. We built a benchmark to measure it and a system to fix it.**

| Metric | RAW (naive prompt) | TRIAD (enhanced prompt) |
|--------|-------------------|------------------------|
| PASS (historically accurate) | 3/24 (12.5%) | **20/24 (83.3%)** |
| PARTIAL (minor issues) | 18/24 (75%) | 4/24 (16.7%) |
| FAIL (significant anachronisms) | 3/24 (12.5%) | 0/24 (0%) |
| **Judged more accurate** | 0/24 (0%) | **23/24 (95.8%)** |

Read the full paper: **[PAPER.md](PAPER.md)** | [PDF version](results/image_cultural_accuracy_article.pdf)

---

## What This Is

A reproducible benchmark testing whether **cultural grounding** improves historical accuracy of AI-generated images. 24 image pairs across 3 characters set in Rome 110 CE, evaluated with a blinded A/B methodology.

**The finding:** Naive prompts produce images that *look* Roman but contain subtle anachronisms (wrong buildings, wrong clothing, wrong objects). Structured knowledge injection through the Triad Engine shifts accuracy from 12.5% to 83.3% PASS rate.

## Characters

| Character | Role | Key Visual Markers |
|-----------|------|-------------------|
| Senator Marcus Tullius | Age 58, senior senator | Toga praetexta (purple border), Esquiline Hill villa |
| Gaius the Merchant | Age 35, freedman trader | Tunica and pallium (NOT toga), bronze merchant disc |
| Julia Aurelia | Age 22, patrician daughter | Stola and palla, Trajanic-era pinned coiffure |

## Example: What Raw Prompts Get Wrong

| Prompt | Anachronism | Correct |
|--------|-------------|---------|
| "Senator giving a speech in the Colosseum" | Wrong venue | Senators spoke in the Curia Julia |
| "Writing with a pen and paper" | Wrong materials | Wax tablet with stylus, or papyrus with reed pen |
| "Young Roman woman with flowers in her hair" | Wrong era | Pinned Trajanic coiffure with metal hairpins |
| "Merchant wearing Roman clothes" | Wrong class | Freedmen wore tunica/pallium, NOT the toga |

## Quick Start

```bash
# Clone
git clone https://github.com/Mysticbirdie/image-cultural-accuracy-benchmark.git
cd image-cultural-accuracy-benchmark

# Install dependencies
pip install httpx Pillow google-genai

# Set your API key
export GOOGLE_API_KEY="your-key-here"

# Generate all images (both raw and triad-enhanced)
python runners/run_image_benchmark.py

# Evaluate all pairs with Gemini Vision judge
python runners/evaluate_images.py
```

## Repo Structure

```
data/
  image_prompts.json      # 24 prompts with raw text, known anachronisms, enhancement goals
  cultural_guide.json     # Structured knowledge base for Rome 110 CE
  characters.json         # Character definitions
  avatars/                # Character reference images (3 avatars)

runners/
  run_image_benchmark.py  # Generate RAW and TRIAD images
  evaluate_images.py      # Run blinded Gemini Vision evaluation
  generate_article_pdf.py # Generate PDF of the paper
  generate_pdf_report.py  # Full 24-page report with all pairs

results/
  images/                 # All 48 generated images (24 raw + 24 triad)
  image_evaluation_*.json # Machine-readable evaluation results

PAPER.md                  # Full research paper
```

## Requirements

- Python 3.10+
- Google AI API key (for Gemini 2.0 Flash enhancement + evaluation, and image generation)
- `httpx`, `Pillow`, `google-genai`

## Methodology

All 24 image pairs evaluated using a **blinded A/B protocol**:
1. Images randomly assigned as "Image A" / "Image B" -- judge doesn't know which is RAW vs TRIAD
2. Both evaluated against the same historical accuracy rubric
3. Verdicts mapped back to RAW/TRIAD only after scoring

See [PAPER.md](PAPER.md) for full methodology and prompt engineering insights.

---

*Benchmark conducted March 2026. Image generation: Gemini. Enhancement + Evaluation: Gemini 2.0 Flash.*
