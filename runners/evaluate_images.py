#!/usr/bin/env python3
"""
Image Visual Evaluation — Blinded Gemini Vision Judge
=====================================================
For each raw/triad image pair:
  1. Randomizes image order (A/B) so judge doesn't know which is RAW vs TRIAD
  2. Sends both images to Gemini Vision with identical evaluation rubric
  3. Judge scores each image independently on historical accuracy (PASS/PARTIAL/FAIL)
  4. Results are de-blinded back to raw/triad after scoring
  5. Saves full evaluation JSON with blind order recorded

This eliminates confirmation bias — the judge can't favor TRIAD images
because it doesn't know which is which.

Usage:
    python evaluate_images.py
    python evaluate_images.py --prompt-id marcus_portrait
    python evaluate_images.py --character julia
"""

import json
import time
import os
import sys
import base64
import argparse
from datetime import datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)

try:
    from PIL import Image
    import io as _io
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
RESULTS_DIR = SCRIPT_DIR.parent / "results"
IMAGES_DIR = RESULTS_DIR / "images"

IMAGE_PROMPTS_FILE = DATA_DIR / "image_prompts.json"

# ── Load .env ──────────────────────────────────────────────────────────────────
def _load_dotenv():
    """Load .env file from repo root if present."""
    env_file = SCRIPT_DIR.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v

_load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
JUDGE_MODEL = "gemini-2.0-flash"


# ── Load image as compressed JPEG base64 ──────────────────────────────────────
def load_image_b64(path: Path, max_side: int = 768, quality: int = 80) -> tuple[str | None, str]:
    """Return (base64_string, mime_type). Compresses to JPEG to avoid API timeouts."""
    if not path.exists():
        return None, "image/jpeg"
    if _PIL_AVAILABLE:
        try:
            img = Image.open(path).convert("RGB")
            if max(img.size) > max_side:
                ratio = max_side / max(img.size)
                img = img.resize(
                    (int(img.width * ratio), int(img.height * ratio)),
                    Image.Resampling.LANCZOS
                )
            buf = _io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            return base64.b64encode(buf.getvalue()).decode("utf-8"), "image/jpeg"
        except Exception:
            pass
    # Fallback: send raw bytes
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8"), "image/png"


# ── Gemini vision judge call ───────────────────────────────────────────────────
def judge_image_pair(
    raw_b64: str | None,
    triad_b64: str | None,
    prompt_entry: dict,
    retries: int = 4,
    raw_mime: str = "image/jpeg",
    triad_mime: str = "image/jpeg",
) -> dict:
    """
    Send raw + triad images to Gemini Vision.
    Returns structured evaluation dict.
    """
    anachronisms = prompt_entry.get("anachronisms_in_raw", [])
    enhancement_goal = prompt_entry.get("enhancement_goal", "")
    raw_prompt = prompt_entry["raw_prompt"]
    pid = prompt_entry["id"]

    anachronism_list = "\n".join(f"  - {a}" for a in anachronisms)

    # ── BLINDED EVALUATION ──────────────────────────────────────────────
    # The judge does NOT know which image is RAW vs TRIAD.
    # Images are labeled A and B in randomized order.
    # Both are evaluated against the SAME historical accuracy rubric.
    # This eliminates confirmation bias toward the enhanced image.

    import random
    order = random.choice(["raw_first", "triad_first"])
    if order == "raw_first":
        first_label, second_label = "A", "B"
        first_b64, first_mime = raw_b64, raw_mime
        second_b64, second_mime = triad_b64, triad_mime
    else:
        first_label, second_label = "A", "B"
        first_b64, first_mime = triad_b64, triad_mime
        second_b64, second_mime = raw_b64, raw_mime

    # Store mapping for later de-blinding
    prompt_entry["_blind_order"] = order

    judge_prompt = f"""You are a Roman history expert evaluating AI-generated images of Ancient Rome, 110 CE, for historical accuracy.

SCENE DESCRIPTION:
A user asked for: "{raw_prompt}"

You are shown two images (Image A and Image B) generated from different prompts for the same scene. You do NOT know which used a basic prompt and which used an enhanced prompt. Evaluate each on its own merits.

HISTORICAL ACCURACY CHECKLIST FOR THIS SCENE:
{anachronism_list}

Additional period details to check:
{enhancement_goal}

YOUR TASK — evaluate EACH image independently for historical accuracy:

For EACH image, assess:
- Is the clothing period-accurate for 110 CE Rome and the character's social class?
- Are objects and materials period-accurate (writing instruments, furniture, containers)?
- Is the architecture and setting historically plausible for 110 CE?
- Are social customs and gestures depicted accurately?
- Are there any anachronisms (objects, styles, or elements from the wrong era)?

Rate each image:
- PASS: Historically accurate for Rome 110 CE with no significant anachronisms
- PARTIAL: Mostly accurate but with 1-2 minor historical issues
- FAIL: Contains clear anachronisms or historically inaccurate elements

Respond in this exact JSON format:
{{
  "image_a_verdict": "PASS" or "PARTIAL" or "FAIL",
  "image_a_anachronisms": ["list any anachronisms or historical inaccuracies visible"],
  "image_a_accurate_details": ["list historically accurate details visible"],
  "image_a_notes": "brief description of what Image A shows and its historical accuracy",
  "image_b_verdict": "PASS" or "PARTIAL" or "FAIL",
  "image_b_anachronisms": ["list any anachronisms or historical inaccuracies visible"],
  "image_b_accurate_details": ["list historically accurate details visible"],
  "image_b_notes": "brief description of what Image B shows and its historical accuracy",
  "which_is_more_accurate": "A" or "B" or "EQUAL",
  "comparison_notes": "one sentence comparing the two images on historical accuracy"
}}

Respond with ONLY the JSON object, no preamble."""

    # Build parts list — images in blinded order
    parts = []

    if first_b64:
        parts.append({"inline_data": {"mime_type": first_mime, "data": first_b64}})
        parts.append({"text": "This is Image A."})
    else:
        parts.append({"text": "Image A: Not available."})

    if second_b64:
        parts.append({"inline_data": {"mime_type": second_mime, "data": second_b64}})
        parts.append({"text": "This is Image B."})
    else:
        parts.append({"text": "Image B: Not available."})

    parts.append({"text": judge_prompt})

    url = f"{GEMINI_BASE_URL}/models/{JUDGE_MODEL}:generateContent?key={GOOGLE_API_KEY}"

    for attempt in range(retries):
        try:
            resp = httpx.post(
                url,
                json={
                    "contents": [{"role": "user", "parts": parts}],
                    "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.0},
                },
                timeout=60,
            )
            if resp.status_code == 429:
                wait = 2 ** attempt * 5
                print(f"    Judge rate-limited, waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            candidates = resp.json().get("candidates", [])
            if not candidates:
                return {"error": "no candidates returned"}
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            blinded = json.loads(text)

            # ── De-blind: map A/B back to raw/triad ──────────────────
            if order == "raw_first":
                raw_key, triad_key = "image_a", "image_b"
            else:
                raw_key, triad_key = "image_b", "image_a"

            # Determine which was more accurate in de-blinded terms
            more_accurate = blinded.get("which_is_more_accurate", "EQUAL")
            if more_accurate == "A":
                more_accurate_deblind = "RAW" if order == "raw_first" else "TRIAD"
            elif more_accurate == "B":
                more_accurate_deblind = "TRIAD" if order == "raw_first" else "RAW"
            else:
                more_accurate_deblind = "EQUAL"

            # Map raw verdict: PASS stays PASS, PARTIAL/FAIL stay as-is
            raw_v = blinded.get(f"{raw_key}_verdict", "?")
            triad_v = blinded.get(f"{triad_key}_verdict", "?")

            # Determine overall improvement from blinded comparison
            if more_accurate_deblind == "TRIAD":
                overall = "YES"
            elif more_accurate_deblind == "EQUAL":
                overall = "MARGINAL"
            else:
                overall = "NO"

            # Determine prompt adherence from triad accuracy
            if triad_v == "PASS":
                adherence = "FULL"
            elif triad_v == "PARTIAL":
                adherence = "PARTIAL"
            else:
                adherence = "POOR"

            return {
                "blind_order": order,
                "raw_verdict": raw_v,
                "raw_anachronisms_found": blinded.get(f"{raw_key}_anachronisms", []),
                "raw_anachronisms_missed": [],
                "raw_notes": blinded.get(f"{raw_key}_notes", ""),
                "raw_accurate_details": blinded.get(f"{raw_key}_accurate_details", []),
                "triad_verdict": triad_v,
                "triad_corrections": blinded.get(f"{triad_key}_accurate_details", []),
                "triad_remaining_issues": blinded.get(f"{triad_key}_anachronisms", []),
                "triad_notes": blinded.get(f"{triad_key}_notes", ""),
                "prompt_adherence": adherence,
                "prompt_adherence_notes": "",
                "overall_improvement": overall,
                "overall_notes": blinded.get("comparison_notes", ""),
                "which_more_accurate_blind": more_accurate,
                "which_more_accurate": more_accurate_deblind,
            }
        except json.JSONDecodeError as e:
            print(f"    JSON parse error: {e}", flush=True)
            if attempt == retries - 1:
                return {"error": f"JSON parse failed: {e}", "raw_response": text if 'text' in dir() else ""}
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == retries - 1:
                return {"error": str(e)}
            time.sleep(2 ** attempt)

    return {"error": "all retries failed"}


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Evaluate image pairs with Gemini Vision judge")
    parser.add_argument("--prompt-id", help="Evaluate single prompt by ID (e.g. marcus_portrait)")
    parser.add_argument("--character", choices=["marcus", "gaius", "julia"],
                        help="Evaluate only one character")
    args = parser.parse_args()

    if not GOOGLE_API_KEY:
        print("ERROR: GOOGLE_API_KEY or GEMINI_API_KEY not set")
        sys.exit(1)

    with open(IMAGE_PROMPTS_FILE) as f:
        prompt_data = json.load(f)

    prompts = prompt_data["prompts"]

    if args.character:
        prompts = [p for p in prompts if p["character"] == args.character]
    if args.prompt_id:
        prompts = [p for p in prompts if p["id"] == args.prompt_id]

    print("=" * 70)
    print("Image Visual Evaluation — Gemini Vision Judge")
    print(f"  Judge:   {JUDGE_MODEL}")
    print(f"  Prompts: {len(prompts)}")
    print(f"  Images:  {IMAGES_DIR}")
    print("=" * 70)

    results = []
    passed_raw = 0      # raw correctly shows anachronism (expected FAIL)
    passed_triad = 0    # triad correctly fixed it (expected PASS)
    full_adherence = 0

    for entry in prompts:
        pid = entry["id"]
        print(f"\n{'─' * 60}")
        print(f"  {pid}")
        print(f"  Raw prompt: {entry['raw_prompt'][:70]}")
        print(f"{'─' * 60}")

        raw_path = IMAGES_DIR / f"{pid}_raw.png"
        triad_path = IMAGES_DIR / f"{pid}_triad.png"

        raw_b64, raw_mime = load_image_b64(raw_path)
        triad_b64, triad_mime = load_image_b64(triad_path)

        if not raw_b64:
            print(f"  WARNING: raw image not found at {raw_path}")
        if not triad_b64:
            print(f"  WARNING: triad image not found at {triad_path}")

        print("  Sending to Gemini Vision judge...", flush=True)
        evaluation = judge_image_pair(raw_b64, triad_b64, entry, raw_mime=raw_mime, triad_mime=triad_mime)

        if "error" in evaluation:
            print(f"  ERROR: {evaluation['error']}")
        else:
            rv = evaluation.get("raw_verdict", "?")
            tv = evaluation.get("triad_verdict", "?")
            pa = evaluation.get("prompt_adherence", "?")
            oi = evaluation.get("overall_improvement", "?")

            print(f"  Raw:        {rv} — {evaluation.get('raw_notes', '')[:80]}")
            print(f"  Triad:      {tv} — {evaluation.get('triad_notes', '')[:80]}")
            print(f"  Adherence:  {pa}")
            print(f"  Improved:   {oi}")

            if rv == "FAIL":  # raw shows anachronisms
                passed_raw += 1
            if tv == "PASS":  # triad historically accurate
                passed_triad += 1
            elif tv == "PARTIAL":
                passed_triad += 0.5
            if pa == "FULL":
                full_adherence += 1

        result = {
            "id": pid,
            "character": entry["character"],
            "shot_type": entry["shot_type"],
            "raw_prompt": entry["raw_prompt"],
            "known_anachronisms": entry.get("anachronisms_in_raw", []),
            "enhancement_goal": entry.get("enhancement_goal", ""),
            "raw_image_exists": raw_b64 is not None,
            "triad_image_exists": triad_b64 is not None,
            "evaluation": evaluation,
        }
        results.append(result)
        time.sleep(4)  # stay under rate limits

    # ── Save results ───────────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = RESULTS_DIR / f"image_evaluation_{timestamp}.json"

    n = len(results)
    evaluated = sum(1 for r in results if "error" not in r.get("evaluation", {"error": True}))

    summary = {
        "benchmark": "Image Visual Evaluation — Rome 110 CE",
        "judge": JUDGE_MODEL,
        "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_pairs": n,
        "evaluated": evaluated,
        "summary": {
            "raw_shows_anachronism": f"{passed_raw}/{evaluated}",
            "triad_fixes_anachronism": f"{passed_triad}/{evaluated}",
            "triad_accuracy_pct": round(passed_triad / evaluated * 100, 1) if evaluated else 0,
            "full_prompt_adherence": f"{full_adherence}/{evaluated}",
        },
        "interpretation": {
            "raw_verdict": "FAIL means the image correctly showed the known anachronism (expected)",
            "triad_verdict": "PASS means the Triad Engine successfully produced a historically accurate image",
            "prompt_adherence": "Whether Imagen followed the enhanced prompt details (not Triad's fault if POOR)",
        },
        "results": results,
    }

    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)

    # ── Print final summary ────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)
    print(f"  Pairs evaluated:           {evaluated}/{n}")
    print(f"  Raw shows anachronism:     {passed_raw}/{evaluated}  (expected: all)")
    print(f"  Triad fixes anachronism:   {passed_triad}/{evaluated}  ({round(passed_triad/evaluated*100,1) if evaluated else 0}%)")
    print(f"  Full prompt adherence:     {full_adherence}/{evaluated}")
    print(f"  Results: {output_file}")
    print()

    print("Per-image summary:")
    for r in results:
        ev = r.get("evaluation", {})
        if "error" in ev:
            print(f"  {r['id']:25} ERROR")
        else:
            rv = ev.get("raw_verdict", "?")
            tv = ev.get("triad_verdict", "?")
            pa = ev.get("prompt_adherence", "?")[0]
            oi = "✓" if ev.get("overall_improvement") == "YES" else "~" if ev.get("overall_improvement") == "MARGINAL" else "✗"
            print(f"  {r['id']:25} raw={rv:4}  triad={tv:4}  adherence={pa}  improved={oi}")


if __name__ == "__main__":
    main()
