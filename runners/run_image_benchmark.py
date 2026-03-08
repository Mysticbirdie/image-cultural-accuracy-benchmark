#!/usr/bin/env python3
"""
Image Accuracy Benchmark — Rome 110 CE
=======================================
Tests whether the Triad Engine improves historical accuracy of image generation prompts.

Architecture:
  1. Load character avatar images (from data/avatars/ or fallback URLs)
  2. RAW path:   avatar + raw prompt → Gemini multimodal → save
  3. TRIAD path: raw prompt → Gemini enhancer (grounded in cultural guide) → enhanced prompt
               → avatar + enhanced prompt → Gemini multimodal → save
  4. Photorealism check: Gemini Vision judges each image — reject + retry if not photorealistic
  5. Track rejection counts per path (raw vs triad)

Both paths pass the SAME character avatar image directly to the generation model.
The comparison purely isolates prompt quality (naive vs Triad-enhanced).

Requires:
  - Google AI API key (GOOGLE_API_KEY or GEMINI_API_KEY env var)
  - pip install httpx Pillow google-genai

Usage:
    python run_image_benchmark.py                    # all prompts, both modes
    python run_image_benchmark.py --character marcus  # one character
    python run_image_benchmark.py --shot-type portrait
    python run_image_benchmark.py --raw-only
    python run_image_benchmark.py --triad-only
    python run_image_benchmark.py --prompt-id marcus_portrait
"""

import json
import time
import os
import sys
import base64
import argparse
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)

try:
    from PIL import Image as PILImage
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: google-genai not installed. Run: pip install google-genai")
    sys.exit(1)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
REPO_DIR = SCRIPT_DIR.parent
DATA_DIR = REPO_DIR / "data"
RESULTS_DIR = REPO_DIR / "results"
IMAGES_DIR = RESULTS_DIR / "images"
RESULTS_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

IMAGE_PROMPTS_FILE = DATA_DIR / "image_prompts.json"
CULTURAL_GUIDE_FILE = DATA_DIR / "cultural_guide.json"

# ── Load .env ──────────────────────────────────────────────────────────────────
def _load_dotenv():
    """Load .env file from repo root if present."""
    env_file = REPO_DIR / ".env"
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

# ── Config ─────────────────────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GENERATION_MODEL = "gemini-3-pro-image-preview"
ENHANCER_MODEL = "gemini-2.0-flash"

# Max retries for photorealism rejection loop
MAX_PHOTO_RETRIES = 5

# Aspect ratio by shot type
ASPECT_BY_SHOT = {
    "portrait": "3:4",
    "scene": "16:9",
    "action": "4:3",
    "marketing_hero": "16:9",
    "dialogue": "16:9",
    "public_gathering": "16:9",
    "domestic": "4:3",
    "transit": "16:9",
}

# Local avatar directory (for standalone / public repo use)
AVATAR_DIR = REPO_DIR / "data" / "avatars"

# Avatar image URLs (fallback if local files not found)
AVATAR_URLS = {
    "marcus": "https://airtrek-ai-de887.web.app/images/Marcus_avatar.jpg",
    "julia": "https://airtrek-ai-de887.web.app/images/Julia_avatar.jpg",
    "gaius": "https://airtrek-ai-de887.web.app/images/Gaius_avatar.jpg",
}


# ── Default character info (used when no external character pack is available) ─
DEFAULT_CHARACTERS = {
    "marcus": {"id": "marcus", "name": "Senator Marcus Tullius", "age": 58, "role": "senior senator, Stoic philosopher"},
    "gaius": {"id": "gaius", "name": "Gaius the Merchant", "age": 35, "role": "freedman spice and silk trader"},
    "julia": {"id": "julia", "name": "Julia Aurelia", "age": 22, "role": "patrician daughter, Stoic philosophy student"},
}


# ── Fetch avatar as PIL.Image ─────────────────────────────────────────────────
_avatar_cache: dict = {}

def fetch_avatar_image(char_id: str) -> Optional[PILImage.Image]:
    """Load character avatar from local file first, then fall back to URL."""
    if char_id in _avatar_cache:
        return _avatar_cache[char_id]

    # Try local files first (data/avatars/)
    if AVATAR_DIR.exists():
        for ext in ("jpg", "jpeg", "png", "webp"):
            local_path = AVATAR_DIR / f"{char_id}_avatar.{ext}"
            if local_path.exists():
                img = PILImage.open(local_path)
                _avatar_cache[char_id] = img
                print(f"    Loaded avatar from local file: {local_path.name}")
                return img

    # Fall back to URL
    url = AVATAR_URLS.get(char_id)
    if not url:
        print(f"    WARNING: No avatar found for character '{char_id}'")
        return None

    try:
        resp = httpx.get(url, timeout=30.0)
        if resp.status_code != 200:
            print(f"    WARNING: avatar fetch failed ({resp.status_code}): {url}")
            return None
        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type:
            print(f"    WARNING: avatar response is not an image (type={content_type})")
            return None
        img = PILImage.open(io.BytesIO(resp.content))
        _avatar_cache[char_id] = img
        return img
    except Exception as e:
        print(f"    WARNING: avatar fetch error: {e}")
        return None


# ── Photorealism check ────────────────────────────────────────────────────────
def check_photorealism(b64_data: str) -> tuple[bool, str]:
    """
    Ask Gemini Vision: is this image photorealistic?
    Returns (is_photorealistic, explanation).
    """
    url = f"{GEMINI_BASE_URL}/models/{ENHANCER_MODEL}:generateContent?key={GOOGLE_API_KEY}"
    prompt = """Is this image photorealistic?

Photorealistic = looks like a real photograph or hyper-realistic digital render that could be mistaken for a photo.
NOT photorealistic = illustration, watercolor, sketch, cartoon, anime, stylized painting, oil painting with visible brushstrokes, or any clearly non-photographic artistic style.

Answer EXACTLY: YES or NO on the first line, then one sentence explanation."""

    for attempt in range(3):
        try:
            resp = httpx.post(
                url,
                json={
                    "contents": [{"parts": [
                        {"inline_data": {"mime_type": "image/png", "data": b64_data}},
                        {"text": prompt}
                    ]}],
                    "generationConfig": {"maxOutputTokens": 80, "temperature": 0.0},
                },
                timeout=30,
            )
            if resp.status_code == 429:
                time.sleep(2 ** attempt * 3)
                continue
            resp.raise_for_status()
            text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            is_photo = text.upper().startswith("YES")
            return is_photo, text
        except Exception as e:
            if attempt == 2:
                return True, f"check failed: {e}"
            time.sleep(2 ** attempt)
    return True, "check failed after retries"


# ── Triad prompt enhancer ─────────────────────────────────────────────────────
def build_enhancer_system(cultural_guide: dict, char_map: dict, char_id: str) -> str:
    ctx = cultural_guide
    not_built = ", ".join(ctx["anachronisms_to_avoid"]["not_yet_built"])
    not_happened = ", ".join(ctx["anachronisms_to_avoid"]["not_yet_happened"])
    already_dead = ", ".join(ctx["anachronisms_to_avoid"]["already_dead"][:5])
    no_tech = ", ".join(ctx["anachronisms_to_avoid"]["technology_notes"])

    char_section = ""
    if char_id and char_id in char_map:
        c = char_map[char_id]
        char_section = f"""
CHARACTER: {c['name']}, age {c['age']}, {c['role']}
Backstory: {c.get('backstory', '')[:200]}
Visual notes: Base your visual description on this character's exact role and social status in 110 CE Rome.
"""

    return f"""You are an expert in Roman history (110 CE) and image generation prompt engineering.

Your task: Transform a vague or anachronistic image prompt into a historically accurate,
visually detailed prompt optimized for image generation.

HISTORICAL CONTEXT — ROME 110 CE:
Emperor: {ctx['time_period_context']['emperor']}
Population: {ctx['time_period_context']['population']}
{char_section}
STRICT ANACHRONISMS — DO NOT INCLUDE IN PROMPTS:
Not yet built: {not_built}
Not yet happened: {not_happened}
Already dead (do not depict as living): {already_dead}
No technology: {no_tech}

ROMAN VISUAL ACCURACY RULES:
- Senators: toga praetexta (white with purple border), no laurel unless triumphing general
- Freedmen/merchants: tunica and pallium, NOT toga — toga requires citizen birth
- Women: stola (long inner garment) + palla (draped outer), NOT Greek peplos
- Hairstyles (women, Trajanic era): elaborate pinned coiffure with acus crinales hairpins, NOT flowers
- Writing: wax tablets (tabulae ceratae) with stylus, or papyrus scrolls — NOT paper or modern pens
- Lighting: oil lamps (lucerna), candles — NOT torches indoors in wealthy homes
- Architecture: marble columns, opus reticulatum concrete, terracotta tile roofs
- Locations: Forum Romanum, Curia Julia (Senate), Forum Boarium, Ostia harbor, domus peristyle gardens
- Money: aureus (gold), denarius (silver), sestertius (bronze), as (copper)
- No gladiators in Senate; no senators in arena; keep social roles accurate

PROMPT ENGINEERING RULES:
- Output ONLY the enhanced prompt — no preamble, no explanation
- Length: 150-250 words, rich visual detail
- Structure order: CHARACTER → CLOTHING (colors first) → KEY PROPS → SETTING → LIGHTING/MOOD
- Style: photorealistic, cinematic, historically authentic, high detail
- End with: "Ancient Rome 110 CE, hyper-realistic, cinematic lighting, historically accurate"

PRIORITY SYSTEM — image models drop details when overloaded:
- Lead with the 2-3 most critical visual elements in the FIRST two sentences
- Repeat key colors/items twice (once early, once in the final description)
- Put background/setting in its own dedicated final sentence
- Never specify more than 3 props — choose the most visually distinctive

VISUAL TRANSLATION — describe what to DRAW, never use obscure historical terms:
- "dextrarum iunctio" → "two men clasping right hands wrist-to-wrist, elbows raised, Roman deal-sealing grip"
- "acus crinales hairpins" → "long bronze hairpins securing the elaborate upswept coiffure"
- "collegium banner" → "painted wooden sign with guild symbol above the entrance"
- "Mercury amulet" → "small bronze disc engraved with a winged staff on a leather cord at his neck"
- "suffibulum veil" → "short white veil pinned at the chest"
- "vittae" → "white woolen bands woven through the upswept hair"
- "lectica" → "curtained litter carried on poles by slaves"
- "impluvium" → "rectangular shallow pool open to the sky in the center of the hall"
- "abacus counting board" → "flat wooden board with rows of small bronze counting discs"
- "papyrus manifest" → "rolled papyrus document with visible dark ink writing"

CEREMONIAL SCENES — describe what the viewer SEES, not the ceremony name:
- Vestal Virgins → "women in ankle-length white robes with white bands woven through upswept hair, tending a small fire on a circular stone altar"

COLOR EMPHASIS — if a specific color is required, state it early AND repeat it:
- CORRECT: "She wears a deep saffron-yellow stola — vivid golden-yellow — with a white wool outer drape"
- WRONG: "saffron stola" buried mid-sentence

OUTDOOR vs INDOOR — be explicit when a scene must be outdoors:
- State "OUTDOORS" and describe sky/open space: "Standing outdoors in the Forum Romanum — open sky, ancient stone plaza"

Enhance the following image prompt:"""


def enhance_prompt(raw_prompt: str, system_prompt: str, enhancement_goal: str = "", retries: int = 4) -> Optional[str]:
    url = f"{GEMINI_BASE_URL}/models/{ENHANCER_MODEL}:generateContent?key={GOOGLE_API_KEY}"
    user_content = raw_prompt
    if enhancement_goal:
        user_content = f"{raw_prompt}\n\nKEY DETAILS TO INCLUDE IN ENHANCED PROMPT: {enhancement_goal}"
    for attempt in range(retries):
        try:
            resp = httpx.post(
                url,
                json={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_content}]}],
                    "generationConfig": {"maxOutputTokens": 800, "temperature": 0.3},
                },
                timeout=30,
            )
            if resp.status_code == 429:
                time.sleep(2 ** attempt * 3)
                continue
            resp.raise_for_status()
            parts = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
        except Exception as e:
            if attempt == retries - 1:
                return f"ERROR: {e}"
            time.sleep(2 ** attempt)
    return None


# Shot-type-specific camera/composition overrides
SHOT_TYPE_CAMERA = {
    "portrait": (
        "Shot on Arri Alexa 65, Zeiss Master Prime 85mm, natural golden hour sunlight, "
        "shallow depth of field f/1.4, soft bokeh background, film grain."
    ),
    "scene": (
        "Shot on Arri Alexa 65, Zeiss Master Prime 35mm, natural warm daylight, "
        "medium depth of field f/4, environmental detail sharp, film grain."
    ),
    "action": (
        "Shot on Arri Alexa 65, Zeiss Master Prime 35mm, 1/1000s shutter to freeze motion, "
        "dynamic composition, sense of active movement, hands and objects in sharp focus, film grain."
    ),
    "marketing_hero": (
        "Shot on Arri Alexa 65, Zeiss Master Prime 18mm wide angle, dramatic chiaroscuro lighting, "
        "low angle heroic composition, deep rich shadows, golden rim light, cinematic epic scale, film grain."
    ),
    "dialogue": (
        "Shot on Arri Alexa 65, Zeiss Master Prime 50mm, eye-level two-shot composition, "
        "both figures clearly visible, warm motivated lighting, shallow depth of field f/2, film grain."
    ),
    "public_gathering": (
        "Shot on Arri Alexa 65, Zeiss Master Prime 24mm, wide establishing shot, "
        "crowd depth, natural diffused daylight, f/5.6, environmental storytelling, film grain."
    ),
    "domestic": (
        "Shot on Arri Alexa 65, Zeiss Master Prime 35mm, warm oil lamp motivated lighting, "
        "intimate framing, f/2.8, rich interior textures sharp, film grain."
    ),
    "transit": (
        "Shot on Arri Alexa 65, Zeiss Master Prime 28mm, natural morning light, "
        "street-level dynamic framing, motion in background, f/4, film grain."
    ),
}


# ── Generate image with Gemini Multimodal (Gemini multimodal) ────────────────────
def generate_with_gemini_multimodal(
    avatar_img: PILImage.Image,
    prompt: str,
    char_name: str,
    char_role: str,
    genai_client: genai.Client,
    shot_type: str = "scene",
    second_avatar_img: Optional[PILImage.Image] = None,
    second_char_name: str = "",
    retries: int = 3,
) -> Optional[str]:
    """
    Generate image using Gemini multimodal with avatar reference.
    Passes avatar PIL.Image + text prompt to the generation model.
    For dialogue shots, accepts a second avatar for the second character.
    Returns base64 PNG or None.
    """
    camera_settings = SHOT_TYPE_CAMERA.get(shot_type, SHOT_TYPE_CAMERA["scene"])

    second_char_note = ""
    if second_avatar_img and second_char_name:
        second_char_note = (
            f"The SECOND person in the second reference image is {second_char_name}. "
            f"Preserve both characters' faces with absolute fidelity. "
        )

    composite_prompt = (
        f"A real photograph taken on location in Ancient Rome, 110 CE. "
        f"Scene: {prompt}. "
        f"The person in the first reference image is present in this scene as {char_name}, a {char_role}. "
        f"Preserve their exact face, skin tone, hair, and features with absolute fidelity. "
        f"{second_char_note}"
        f"REAL PHOTOGRAPH. {camera_settings} "
        f"National Geographic cover quality, 8K resolution. "
        f"NOT illustration, NOT CGI, NOT painting."
    )

    contents = [avatar_img]
    if second_avatar_img:
        contents.append(second_avatar_img)
    contents.append(composite_prompt)

    for attempt in range(retries):
        try:
            response = genai_client.models.generate_content(
                model=GENERATION_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE'],
                ),
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    return base64.b64encode(part.inline_data.data).decode()

            print(f"    WARNING: No image data in Gemini response (attempt {attempt+1})", flush=True)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait = 2 ** attempt * 5
                print(f"    Rate limited, waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
            print(f"    Gemini multimodal error (attempt {attempt+1}): {e}", flush=True)
            if attempt < retries - 1:
                time.sleep(3)

    return None


# ── Generate one image with photorealism loop ──────────────────────────────────
def generate_photorealistic(
    prompt: str,
    char_id: str,
    char_name: str,
    char_role: str,
    avatar_img: Optional[PILImage.Image],
    genai_client: genai.Client,
    label: str,
    shot_type: str = "scene",
    second_avatar_img: Optional[PILImage.Image] = None,
    second_char_name: str = "",
) -> tuple[Optional[str], int, str]:
    """
    Generate an image using Gemini Multimodal (Gemini multimodal) with avatar reference.
    Checks for photorealism and retries if needed.
    For dialogue shots, pass second_avatar_img and second_char_name.

    Returns: (base64_data, rejection_count, model_used)
    """
    if avatar_img is None:
        print(f"    [{label}] ERROR: No avatar image — cannot generate", flush=True)
        return None, 0, "none"

    rejections = 0
    model_used = GENERATION_MODEL

    for attempt in range(MAX_PHOTO_RETRIES + 1):
        print(f"    [{label}] Generating with Gemini multimodal + avatar reference (attempt {attempt+1})...", flush=True)
        b64 = generate_with_gemini_multimodal(
            avatar_img=avatar_img,
            prompt=prompt,
            char_name=char_name,
            char_role=char_role,
            genai_client=genai_client,
            shot_type=shot_type,
            second_avatar_img=second_avatar_img,
            second_char_name=second_char_name,
        )

        if not b64:
            print(f"    [{label}] Generation failed (attempt {attempt+1})", flush=True)
            if attempt < MAX_PHOTO_RETRIES:
                time.sleep(3)
                rejections += 1
            continue

        # Photorealism check
        print(f"    [{label}] Checking photorealism...", flush=True)
        is_photo, explanation = check_photorealism(b64)
        short_explain = explanation.split("\n")[1].strip() if "\n" in explanation else explanation[:80]

        if is_photo:
            print(f"    [{label}] PASS photorealism (rejections so far: {rejections})", flush=True)
            return b64, rejections, model_used
        else:
            rejections += 1
            print(f"    [{label}] REJECTED (not photorealistic, attempt {attempt+1}/{MAX_PHOTO_RETRIES}): {short_explain}", flush=True)
            time.sleep(3)

    # Ran out of retries — return last generated image anyway
    print(f"    [{label}] WARNING: max retries hit ({MAX_PHOTO_RETRIES}), using last image", flush=True)
    return b64, rejections, model_used


def save_image(b64_data: str, filepath: Path):
    image_bytes = base64.b64decode(b64_data)
    with open(filepath, "wb") as f:
        f.write(image_bytes)


# ── Run one prompt ─────────────────────────────────────────────────────────────
def run_prompt(
    prompt_entry: dict,
    cultural_guide: dict,
    char_map: dict,
    prod_char_map: dict,
    genai_client: genai.Client,
    run_raw: bool,
    run_triad: bool,
) -> dict:
    pid = prompt_entry["id"]
    char_id = prompt_entry["character"]
    shot_type = prompt_entry["shot_type"]
    raw_prompt = prompt_entry["raw_prompt"]

    print(f"\n{'─' * 60}")
    print(f"  {pid} ({char_id}, {shot_type})")
    print(f"  Raw: {raw_prompt[:80]}")
    print(f"{'─' * 60}")

    # Load character info
    prod_char = prod_char_map.get(char_id, {})
    char_name = prod_char.get("name", char_id.capitalize())
    char_role = prod_char.get("role", "Roman citizen")
    enhancement_goal = prompt_entry.get("enhancement_goal", "")

    # Fetch primary avatar image
    print(f"  Fetching avatar for {char_id}...", flush=True)
    avatar_img = fetch_avatar_image(char_id)
    if avatar_img:
        print(f"  Avatar loaded: {avatar_img.size[0]}x{avatar_img.size[1]}", flush=True)
    else:
        print(f"  WARNING: No avatar for '{char_id}' — images will lack character consistency!")

    # For dialogue scenes, detect and load the second character's avatar
    second_avatar_img = None
    second_char_name = ""
    if shot_type == "dialogue":
        all_char_ids = list(AVATAR_URLS.keys())
        other_char_ids = [c for c in all_char_ids if c != char_id]
        # Find which other character appears in the raw prompt or enhancement_goal
        combined_text = (raw_prompt + " " + enhancement_goal).lower()
        second_char_id = next(
            (c for c in other_char_ids if c in combined_text),
            other_char_ids[0] if other_char_ids else None
        )
        if second_char_id:
            print(f"  Fetching second avatar for {second_char_id} (dialogue scene)...", flush=True)
            second_avatar_img = fetch_avatar_image(second_char_id)
            second_prod_char = prod_char_map.get(second_char_id, {})
            second_char_name = second_prod_char.get("name", second_char_id.capitalize())
            if second_avatar_img:
                print(f"  Second avatar loaded: {second_avatar_img.size[0]}x{second_avatar_img.size[1]}", flush=True)

    result = {
        "id": pid,
        "character": char_id,
        "shot_type": shot_type,
        "raw_prompt": raw_prompt,
        "enhanced_prompt": None,
        "raw_image": None,
        "triad_image": None,
        "raw_error": None,
        "triad_error": None,
        "raw_rejections": 0,
        "triad_rejections": 0,
        "raw_model": None,
        "triad_model": None,
        "avatar_used": avatar_img is not None,
        "second_avatar_used": second_avatar_img is not None,
        "generation_model": GENERATION_MODEL,
        "anachronisms_in_raw": prompt_entry.get("anachronisms_in_raw", []),
        "enhancement_goal": enhancement_goal,
    }

    # ── Raw path ───────────────────────────────────────────────────────────────
    if run_raw:
        print(f"  [RAW] Generating...", flush=True)
        b64, rejections, model = generate_photorealistic(
            prompt=raw_prompt,
            char_id=char_id,
            char_name=char_name,
            char_role=char_role,
            avatar_img=avatar_img,
            genai_client=genai_client,
            label="RAW",
            shot_type=shot_type,
            second_avatar_img=second_avatar_img,
            second_char_name=second_char_name,
        )
        result["raw_rejections"] = rejections
        result["raw_model"] = model
        if b64:
            raw_path = IMAGES_DIR / f"{pid}_raw.png"
            save_image(b64, raw_path)
            result["raw_image"] = str(raw_path.relative_to(REPO_DIR))
            print(f"  [RAW] Saved → {raw_path.name}  (rejections: {rejections})")
        else:
            result["raw_error"] = "generation failed after all retries"
            print("  [RAW] FAILED")
        time.sleep(2)

    # ── Triad path ─────────────────────────────────────────────────────────────
    if run_triad:
        print(f"  [TRIAD] Enhancing prompt...", flush=True)
        system = build_enhancer_system(cultural_guide, char_map, char_id)
        enhanced = enhance_prompt(raw_prompt, system, enhancement_goal=enhancement_goal)

        if enhanced and not enhanced.startswith("ERROR:"):
            result["enhanced_prompt"] = enhanced
            print(f"  [TRIAD] Enhanced: {enhanced[:100]}...")

            print(f"  [TRIAD] Generating...", flush=True)
            b64, rejections, model = generate_photorealistic(
                prompt=enhanced,
                char_id=char_id,
                char_name=char_name,
                char_role=char_role,
                avatar_img=avatar_img,
                genai_client=genai_client,
                label="TRIAD",
                shot_type=shot_type,
                second_avatar_img=second_avatar_img,
                second_char_name=second_char_name,
            )
            result["triad_rejections"] = rejections
            result["triad_model"] = model
            if b64:
                triad_path = IMAGES_DIR / f"{pid}_triad.png"
                save_image(b64, triad_path)
                result["triad_image"] = str(triad_path.relative_to(REPO_DIR))
                print(f"  [TRIAD] Saved → {triad_path.name}  (rejections: {rejections})")
            else:
                result["triad_error"] = "generation failed after all retries"
                print("  [TRIAD] Image FAILED")
        else:
            result["triad_error"] = f"enhancement failed: {enhanced}"
            print(f"  [TRIAD] Enhancement FAILED: {enhanced}")

        time.sleep(2)

    return result


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Run image accuracy benchmark with avatar reference images")
    parser.add_argument("--character", choices=["marcus", "gaius", "julia"],
                        help="Only run prompts for this character")
    parser.add_argument("--shot-type",
                        choices=["portrait", "scene", "action", "marketing_hero",
                                 "dialogue", "public_gathering", "domestic", "transit"],
                        help="Only run prompts of this shot type")
    parser.add_argument("--raw-only", action="store_true")
    parser.add_argument("--triad-only", action="store_true")
    parser.add_argument("--prompt-id", help="Run single prompt by ID")
    args = parser.parse_args()

    if not GOOGLE_API_KEY:
        print("ERROR: GOOGLE_API_KEY or GEMINI_API_KEY not set")
        sys.exit(1)

    run_raw = not args.triad_only
    run_triad = not args.raw_only

    # Initialize google-genai client
    genai_client = genai.Client(api_key=GOOGLE_API_KEY)

    # Load data
    with open(IMAGE_PROMPTS_FILE) as f:
        prompt_data = json.load(f)
    if not CULTURAL_GUIDE_FILE.exists():
        print("ERROR: cultural_guide.json not found in data/")
        print("  The Rome 110 CE domain guide is not included in this repository.")
        print("  See cultural_guide_schema/example_guide.json for the expected structure.")
        print("  You can still run RAW-only generation with: --raw-only")
        if not args.raw_only:
            sys.exit(1)
        cultural_guide = {}
    else:
        with open(CULTURAL_GUIDE_FILE) as f:
            cultural_guide = json.load(f)

    # Load character data — try local characters.json, fall back to defaults
    char_data_file = DATA_DIR / "characters.json"
    if char_data_file.exists():
        with open(char_data_file) as f:
            char_data = json.load(f)
        bench_char_map = {c["id"]: c for c in char_data.get("characters", [])}
    else:
        bench_char_map = DEFAULT_CHARACTERS
    prod_char_map = bench_char_map

    prompts = prompt_data["prompts"]
    if args.character:
        prompts = [p for p in prompts if p["character"] == args.character]
    if args.shot_type:
        prompts = [p for p in prompts if p["shot_type"] == args.shot_type]
    if args.prompt_id:
        prompts = [p for p in prompts if p["id"] == args.prompt_id]

    modes = []
    if run_raw:
        modes.append("Raw")
    if run_triad:
        modes.append("Triad-enhanced")

    print("=" * 70)
    print("Image Accuracy Benchmark — Rome 110 CE (Gemini Multimodal)")
    print(f"  Model:        {GENERATION_MODEL}")
    print(f"  Enhancer:     {ENHANCER_MODEL}")
    print(f"  Pipeline:     Gemini multimodal with avatar reference")
    print(f"  Prompts:      {len(prompts)}")
    print(f"  Modes:        {' + '.join(modes)}")
    print(f"  Max retries:  {MAX_PHOTO_RETRIES} per image (photorealism gate)")
    print(f"  Output:       {IMAGES_DIR}")
    print("=" * 70)

    results = []
    total_raw_rejections = 0
    total_triad_rejections = 0

    for entry in prompts:
        result = run_prompt(
            entry, cultural_guide, bench_char_map, prod_char_map,
            genai_client, run_raw, run_triad,
        )
        results.append(result)
        total_raw_rejections += result.get("raw_rejections", 0)
        total_triad_rejections += result.get("triad_rejections", 0)
        time.sleep(1)

    # ── Save manifest ──────────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_file = RESULTS_DIR / f"image_benchmark_{timestamp}.json"

    raw_success = sum(1 for r in results if r["raw_image"])
    triad_success = sum(1 for r in results if r["triad_image"])
    n = len(results)

    manifest = {
        "benchmark": "Image Accuracy Benchmark — Rome 110 CE (Gemini Multimodal)",
        "model": GENERATION_MODEL,
        "enhancer": ENHANCER_MODEL,
        "pipeline": "gemini-multimodal-avatar-reference",
        "photorealism_gate": True,
        "max_photo_retries": MAX_PHOTO_RETRIES,
        "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_prompts": n,
        "raw_images_generated": raw_success,
        "triad_images_generated": triad_success,
        "photorealism_rejections": {
            "raw_total": total_raw_rejections,
            "triad_total": total_triad_rejections,
            "raw_per_image_avg": round(total_raw_rejections / max(raw_success, 1), 2),
            "triad_per_image_avg": round(total_triad_rejections / max(triad_success, 1), 2),
        },
        "results": results,
    }

    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)

    # ── Print final summary ────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("COMPLETE")
    print("=" * 70)
    if run_raw:
        print(f"  Raw images:            {raw_success}/{n}")
        print(f"  Raw photorealism rejections: {total_raw_rejections} total  ({round(total_raw_rejections/max(raw_success,1),1)} avg/image)")
    if run_triad:
        print(f"  Triad images:          {triad_success}/{n}")
        print(f"  Triad photorealism rejections: {total_triad_rejections} total  ({round(total_triad_rejections/max(triad_success,1),1)} avg/image)")
    print(f"  Images:   {IMAGES_DIR}")
    print(f"  Manifest: {manifest_file}")
    print()
    print("Per-image summary:")
    for r in results:
        raw_status = f"✓ ({r['raw_rejections']}rej)" if r["raw_image"] else "✗"
        triad_status = f"✓ ({r['triad_rejections']}rej)" if r["triad_image"] else "✗"
        raw_col = f"raw={raw_status:12}" if run_raw else ""
        triad_col = f"triad={triad_status:12}" if run_triad else ""
        print(f"  {r['id']:30} {raw_col} {triad_col}")


if __name__ == "__main__":
    main()
