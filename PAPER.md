# Image Cultural Accuracy Benchmark

## AI Image Models Hallucinate History — and We Can Fix It

### The Problem

Ask an AI image model to "draw a Roman senator giving a speech" and you'll get the Colosseum — a venue for gladiatorial combat, not political debate. Senators spoke in the Curia Julia or from the Rostra in the Forum Romanum. Ask for "a young Roman woman with flowers in her hair" and you'll get a Renaissance portrait, not a Trajanic-era coiffure with *acus crinales* hairpins.

AI image models hallucinate history the same way language models hallucinate facts. The images look plausible but are filled with anachronisms — wrong buildings, wrong clothing, wrong objects, wrong social dynamics. For applications in education, entertainment, and cultural preservation, this matters.

We built a benchmark to measure this problem and a system to fix it.

---

### The Benchmark: Rome 110 CE

**3 characters** from a historical fiction setting in Trajan's Rome:

| Character | Role | Key Visual Markers |
|-----------|------|--------------------|
| **Senator Marcus Tullius** | Age 58, senior senator, Stoic | Toga praetexta (purple border), Esquiline Hill villa |
| **Gaius the Merchant** | Age 35, freedman trader | Tunica and pallium (NOT toga), bronze merchant disc |
| **Julia Aurelia** | Age 22, patrician daughter | Stola and palla, Trajanic-era pinned coiffure |

**8 shot types** per character = **24 image pairs** total:

| Shot Type | What It Tests |
|-----------|---------------|
| Portrait | Face, clothing, class markers |
| Scene | Character in a specific location |
| Action | Period-accurate activities and objects |
| Marketing Hero | Cinematic composition with historical grounding |
| Dialogue | Two characters interacting — social dynamics and class distinction |
| Public Gathering | Civic/religious events with period-accurate crowds |
| Domestic | Private home/workplace with household details |
| Transit | Moving through Rome — streets, harbors, transport |

Each prompt has a **deliberately naive "raw" version** (what a typical user would type) and **known anachronisms** that the raw prompt will produce:

> **Raw prompt:** "Marcus, a Roman senator, writing with a pen and paper at his desk"
>
> **Known anachronisms:** Paper and modern pen don't exist in 110 CE. Should be wax tablet or papyrus scroll with a stylus.

---

### The Method: Triad Engine Cultural Grounding

The Triad Engine is a multi-layer system for grounding AI outputs in domain-specific knowledge:

- **μ-layer (cultural guide):** A structured knowledge base of historically accurate details — clothing by social class, architecture by era, objects by period, social customs by context
- **Enhancer:** Takes the naive user prompt + cultural guide and produces a historically grounded prompt with period-accurate details

The same character avatar image is passed to both the raw and enhanced pipelines, isolating **prompt quality** as the only variable.

**Pipeline:**
```
RAW path:   avatar + naive prompt → image model → save
TRIAD path: naive prompt → enhancer (grounded in μ-layer) → enhanced prompt
            → avatar + enhanced prompt → image model → save
```

Both paths use the same image generation model with the same character reference image. The comparison purely isolates whether cultural grounding in the prompt improves historical accuracy.

---

### The Results (Blinded Evaluation)

All 24 image pairs were evaluated using a **blinded A/B methodology** — the judge did not know which image was RAW and which was TRIAD-enhanced. Images were randomly ordered and evaluated against the same historical accuracy rubric.

| Metric | RAW (naive prompt) | TRIAD (enhanced prompt) |
|--------|-------------------|------------------------|
| **PASS** (historically accurate) | 3/24 (12.5%) | **20/24 (83.3%)** |
| **PARTIAL** (mostly accurate, 1-2 minor issues) | 18/24 (75%) | 4/24 (16.7%) |
| **FAIL** (significant anachronisms) | 3/24 (12.5%) | 0/24 (0%) |

| Metric | Score |
|--------|-------|
| **Triad judged more accurate** | **23/24 (95.8%)** |
| **Equal accuracy** | 1/24 (4.2%) |
| **RAW judged more accurate** | 0/24 (0%) |
| **Clear improvement (YES)** | 23/24 (95.8%) |
| **Full prompt adherence** | 20/24 (83.3%) |

Raw prompts are not catastrophically wrong — they produce images that are *mostly* period-appropriate (75% PARTIAL). But the Triad Engine dramatically shifts the accuracy distribution: **6.7x more PASS results** (20 vs 3), **zero FAIL results** (vs 3), and the judge identified TRIAD as more accurate in **23 out of 24 pairs**. In no case was RAW judged more accurate than TRIAD.

**By character:**

| Character | RAW PASS/PARTIAL/FAIL | TRIAD PASS/PARTIAL/FAIL | Triad More Accurate |
|-----------|----------------------|------------------------|-------------------|
| Marcus | 2/5/1 | 7/1/0 | 7/8 (87.5%) |
| Gaius | 0/7/1 | 6/2/0 | 8/8 (100%) |
| Julia | 1/6/1 | 7/1/0 | 8/8 (100%) |

**Notable findings:**
- Gaius and Julia achieved 100% — TRIAD was judged more accurate in all 8 pairs for both characters
- Marcus had the one EQUAL case (marcus_portrait) where both RAW and TRIAD produced accurate senator portraits
- The 4 remaining TRIAD PARTIAL results involved subtle details like wrist-clasp vs handshake (gaius_action) and pen-on-paper persisting despite explicit negation (marcus_action) — edge cases where the image model resists prompt instructions
- Gaius never scored a RAW PASS — freedman-specific details (tunica vs toga, merchant disc, trade goods) are consistently missed by naive prompts

---

### What the Raw Prompts Get Wrong

Raw prompts produce images that look plausible but contain subtle anachronisms. In our blinded evaluation, 87.5% of raw images were rated PARTIAL or FAIL — the images get the *general feel* right but miss period-specific details:

| Prompt | Anachronism | Why It's Wrong |
|--------|-------------|----------------|
| "Senator giving a speech in the Colosseum" | Wrong venue | Senators spoke in the Curia Julia, not the Colosseum |
| "Writing with a pen and paper" | Wrong materials | Romans used wax tablets with stylus, or papyrus with reed pen |
| "Young Roman woman with flowers in her hair" | Wrong era | Renaissance aesthetic, not Roman — should be pinned Trajanic coiffure |
| "Merchant wearing Roman clothes" | Wrong class markers | Freedmen wore tunica/pallium, NOT the toga (reserved for citizens) |
| "Making a business deal" (handshake) | Wrong gesture | Modern handshake rendered instead of Roman *dextrarum iunctio* (wrist-to-wrist clasp) |
| "Watching a religious ceremony" | Wrong religion | Christian-style reverence rendered instead of Roman state religion |
| "Getting ready with her maids" | Wrong objects | Wall mirrors (Romans used small polished bronze hand mirrors) |
| "Being carried through the streets in a chair" | Wrong vehicle | Generic palanquin instead of Roman *lectica* with period-correct bearers |

---

### Prompt Engineering Insights

Not all enhancement strategies work equally well. We identified specific failure modes and developed solutions:

#### 1. Visual Translation Over Terminology

Historical terms that image models don't know get silently dropped. The fix is describing what to **draw**, not what to **call** it.

| Fails | Works |
|-------|-------|
| "dextrarum iunctio handshake" | "two men clasping right hands wrist-to-wrist, elbows raised" |
| "acus crinales hairpins" | "elaborate pinned upswept hairstyle with metal hairpins" |
| "Mercury amulet" | "small bronze disc engraved with a winged staff on a leather cord" |
| "collegium banner" | "painted wooden guild sign with a winged staff symbol" |

#### 2. MUST / SHOULD / BACKGROUND Priority System

Image models drop details when overloaded with concurrent specifics. Leading with 2-3 critical elements improves adherence:

```
MUST: Julia Aurelia in a deep saffron-yellow stola — vivid golden-yellow
color, this is critical — with a white wool outer drape.
MUST: standing OUTDOORS on stone steps of a Roman villa at dusk.
BACKGROUND: Roman domus stone facade behind her, warm golden evening light.
```

#### 3. Explicit OUTDOOR / INDOOR Flagging

Without explicit instruction, models default to interior rendering for most prompts. Adding "OUTDOORS" with a sky description forces correct rendering:

```
MUST: Marcus Tullius standing OUTDOORS in the Forum Romanum — open sky,
ancient Roman stone plaza.
```

#### 4. Color Emphasis Through Repetition

Critical colors buried mid-sentence get lost. Stating the color early AND repeating it improves adherence:

```
"deep saffron-yellow stola — vivid golden-yellow color, this is critical"
```

#### 5. Ceremonial Scenes: Describe What the Viewer Sees

Named ceremonies are unknown to image models. Describe the visual scene instead:

| Fails | Works |
|-------|-------|
| "Vestal Virgins performing sacred rites" | "women in ankle-length white robes with white woolen bands woven through their upswept hair, tending a small fire burning on a circular stone altar" |

---

### Evaluation Methodology

All 24 image pairs were evaluated using a **blinded A/B protocol** to eliminate confirmation bias:

1. **Randomized order:** For each pair, images were randomly assigned as "Image A" and "Image B" — the judge did not know which was RAW and which was TRIAD
2. **Same rubric for both:** Both images were evaluated against the same historical accuracy criteria, without being told which anachronisms to expect
3. **De-blinding after scoring:** A/B verdicts were mapped back to RAW/TRIAD only after all scores were assigned

The judge (Gemini Vision, gemini-2.0-flash) evaluates each image on:
- **Historical accuracy verdict:** PASS (period-accurate), PARTIAL (mostly accurate, 1-2 minor issues), or FAIL (significant anachronisms)
- **Specific details noted:** What historical elements are correct or incorrect
- **Which image is more accurate:** Direct A/B comparison without knowing which is enhanced
- **Overall improvement:** Whether one image is clearly better (YES/MARGINAL/NO)

This blinded approach prevents the judge from rating RAW images as FAIL simply because it *knows* they should contain anachronisms, and prevents it from rating TRIAD images as PASS simply because it *knows* they were enhanced. The result is a more honest assessment of both approaches.

---

### Reproducing the Benchmark

The benchmark is fully reproducible. All prompts, known anachronisms, and enhancement goals are defined in `image_prompts.json`. The evaluation rubric is embedded in the judge prompt.

**Files:**
- `data/image_prompts.json` — 24 prompts with raw text, known anachronisms, and enhancement goals
- `runners/run_image_benchmark.py` — Generates RAW and TRIAD images with avatar reference
- `runners/evaluate_images.py` — Runs Gemini Vision judge on all 24 pairs
- `runners/generate_pdf_report.py` — Full 24-page PDF report with all pairs
- `runners/generate_compact_pdf.py` — Compact PDF with best examples for sharing
- `results/images/` — All 48 generated images (24 raw + 24 triad)
- `results/image_evaluation_*.json` — Machine-readable evaluation results

**Requirements:**
- Google AI API key (Gemini 2.0 Flash for enhancement + evaluation)
- Image generation model access (gemini-3-pro-image-preview or equivalent)
- Python 3.10+ with `httpx`, `google-genai`, `Pillow`, `reportlab`

**Run:**
```bash
# Generate all images (both raw and triad-enhanced)
python runners/run_image_benchmark.py

# Evaluate all pairs with Gemini Vision judge
python runners/evaluate_images.py

# Generate PDF reports
python runners/generate_pdf_report.py
python runners/generate_compact_pdf.py
```

---

### Key Takeaway

AI image models don't catastrophically fail on historical scenes — naive prompts produce *mostly* plausible results (75% PARTIAL). But "mostly plausible" isn't good enough for education, entertainment, or cultural preservation. The difference between a generic toga and a *toga praetexta*, between the Colosseum and the Curia Julia, between a modern handshake and a Roman *dextrarum iunctio* — these details matter.

Cultural grounding through the Triad Engine shifts the accuracy distribution dramatically: **6.7x more PASS results** (20 vs 3), **zero FAIL results** (vs 3), and **95.8% of pairs judged more accurate** in a blinded evaluation. In no case was a raw image judged more accurate than its Triad-enhanced counterpart. The fix is not better models — it's better prompts, informed by domain expertise and structured as visual descriptions rather than historical terminology.

The same μ-layer architecture that achieved 100% accuracy on a Polish cultural text benchmark (RAW 91.1% → TRIAD 100.0% on 56 factual questions) transfers to image generation with comparable results (RAW 12.5% PASS → TRIAD 83.3% PASS).

---

*Benchmark conducted March 2026. Image generation: gemini-3-pro-image-preview. Enhancement: gemini-2.0-flash. Evaluation: gemini-2.0-flash (blinded A/B Gemini Vision judge). All images generated with character avatar reference for identity consistency.*
