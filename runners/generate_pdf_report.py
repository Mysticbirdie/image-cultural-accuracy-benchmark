#!/usr/bin/env python3
"""
Generate a PDF report with all 24 image pairs side by side,
including evaluation verdicts and notes from the Gemini Vision judge.
"""

import json
from pathlib import Path
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

SCRIPT_DIR = Path(__file__).parent
REPO_DIR = SCRIPT_DIR.parent
RESULTS_DIR = REPO_DIR / "results"
IMAGES_DIR = RESULTS_DIR / "images"

# Colors
PASS_GREEN = HexColor("#2E7D32")
FAIL_RED = HexColor("#C62828")
PARTIAL_AMBER = HexColor("#F57F17")
HEADER_BG = HexColor("#1B2A4A")
RAW_BG = HexColor("#FFF3E0")
TRIAD_BG = HexColor("#E8F5E9")


def load_evaluations():
    """Load the most recent evaluation with all 24 image pairs."""
    # Find the most recent evaluation file
    import glob
    eval_files = glob.glob(str(RESULTS_DIR / "image_evaluation_*.json"))
    eval_files.sort()
    
    if not eval_files:
        print("No evaluation files found!")
        return {}
    
    latest_file = eval_files[-1]  # Get the most recent one
    print(f"Loading evaluation from: {latest_file}")
    
    with open(latest_file) as f:
        main_data = json.load(f)

    results = {}
    for r in main_data["results"]:
        results[r["id"]] = r

    return results


def verdict_color(verdict):
    if verdict == "PASS":
        return PASS_GREEN
    elif verdict == "FAIL":
        return FAIL_RED
    elif verdict in ("PARTIAL", "MARGINAL"):
        return PARTIAL_AMBER
    return black


def build_pdf():
    evaluations = load_evaluations()

    output_path = RESULTS_DIR / "image_benchmark_report.pdf"
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(letter),
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title2", parent=styles["Title"],
        fontSize=22, textColor=HEADER_BG, spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "Subtitle2", parent=styles["Normal"],
        fontSize=11, textColor=HexColor("#555555"), alignment=TA_CENTER, spaceAfter=12
    )
    heading_style = ParagraphStyle(
        "Heading2", parent=styles["Heading2"],
        fontSize=14, textColor=HEADER_BG, spaceBefore=4, spaceAfter=4
    )
    prompt_style = ParagraphStyle(
        "Prompt", parent=styles["Normal"],
        fontSize=8, textColor=HexColor("#333333"), leading=10
    )
    verdict_style_pass = ParagraphStyle(
        "VerdictPass", parent=styles["Normal"],
        fontSize=11, textColor=PASS_GREEN, alignment=TA_CENTER, leading=14
    )
    verdict_style_fail = ParagraphStyle(
        "VerdictFail", parent=styles["Normal"],
        fontSize=11, textColor=FAIL_RED, alignment=TA_CENTER, leading=14
    )
    notes_style = ParagraphStyle(
        "Notes", parent=styles["Normal"],
        fontSize=7.5, textColor=HexColor("#333333"), leading=9.5, spaceBefore=2
    )
    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"],
        fontSize=10, textColor=white, alignment=TA_CENTER,
    )
    summary_header = ParagraphStyle(
        "SummaryHeader", parent=styles["Normal"],
        fontSize=10, textColor=HEADER_BG, leading=13
    )
    summary_val = ParagraphStyle(
        "SummaryVal", parent=styles["Normal"],
        fontSize=10, leading=13
    )

    story = []

    # Title page
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("Image Accuracy Benchmark", title_style))
    story.append(Paragraph("Ancient Rome 110 CE — Triad Engine Evaluation", subtitle_style))
    story.append(Spacer(1, 0.3 * inch))

    # Summary stats
    total = len(evaluations)
    triad_pass = sum(1 for r in evaluations.values()
                     if r.get("evaluation", {}).get("triad_verdict") == "PASS")
    triad_partial = sum(1 for r in evaluations.values()
                        if r.get("evaluation", {}).get("triad_verdict") == "PARTIAL")
    raw_fail = sum(1 for r in evaluations.values()
                   if r.get("evaluation", {}).get("raw_verdict") == "FAIL")
    full_adherence = sum(1 for r in evaluations.values()
                         if r.get("evaluation", {}).get("prompt_adherence") == "FULL")
    improved_yes = sum(1 for r in evaluations.values()
                       if r.get("evaluation", {}).get("overall_improvement") == "YES")
    improved_marginal = sum(1 for r in evaluations.values()
                            if r.get("evaluation", {}).get("overall_improvement") == "MARGINAL")

    summary_data = [
        ["Metric", "Result"],
        ["Total image pairs", str(total)],
        ["Raw shows anachronism (expected)", f"{raw_fail}/{total} ({round(raw_fail/total*100)}%)"],
        ["Triad PASS (historically accurate)", f"{triad_pass}/{total} ({round(triad_pass/total*100)}%)"],
        ["Triad PARTIAL", f"{triad_partial}/{total}"],
        ["Full prompt adherence", f"{full_adherence}/{total} ({round(full_adherence/total*100)}%)"],
        ["Clear improvement (YES)", f"{improved_yes}/{total} ({round(improved_yes/total*100)}%)"],
        ["Any improvement (YES + MARGINAL)", f"{improved_yes + improved_marginal}/{total} ({round((improved_yes+improved_marginal)/total*100)}%)"],
    ]

    summary_table = Table(summary_data, colWidths=[3.5 * inch, 3 * inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#F5F5F5")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3 * inch))

    legend_text = (
        "<b>How to read:</b> Each page shows a RAW image (naive prompt) vs TRIAD image "
        "(Triad Engine-enhanced prompt). RAW verdict FAIL = image correctly shows the known "
        "anachronism (expected). TRIAD verdict PASS = Triad Engine successfully produced a "
        "historically accurate image. Prompt adherence measures whether Imagen followed "
        "the enhanced prompt (not Triad's fault if POOR)."
    )
    story.append(Paragraph(legend_text, notes_style))
    story.append(PageBreak())

    # Order: marcus, gaius, julia x portrait, scene, action, hero, dialogue, public, domestic, transit
    prompt_order = [
        "marcus_portrait", "marcus_scene", "marcus_action", "marcus_hero",
        "marcus_dialogue", "marcus_public", "marcus_domestic", "marcus_transit",
        "gaius_portrait", "gaius_scene", "gaius_action", "gaius_hero",
        "gaius_dialogue", "gaius_public", "gaius_domestic", "gaius_transit",
        "julia_portrait", "julia_scene", "julia_action", "julia_hero",
        "julia_dialogue", "julia_public", "julia_domestic", "julia_transit",
    ]

    img_width = 2.5 * inch  # Reduced from 3.4
    img_height = 2.0 * inch  # Reduced from 2.8

    # Only include avatar-enhanced images (not old text-only ones)
    for pid in prompt_order:
        if pid not in evaluations:
            continue
        
        r = evaluations[pid]
        ev = r.get("evaluation", {})
        if "error" in ev:
            continue
        
        # Check if this is an avatar-enhanced image
        raw_path = IMAGES_DIR / f"{pid}_raw.png"
        triad_path = IMAGES_DIR / f"{pid}_triad.png"
        
        # Only include if both images exist and are recent (avatar-enhanced)
        if raw_path.exists() and triad_path.exists():
            # Check file modification time to ensure these are the new avatar-enhanced ones
            import os
            raw_mtime = os.path.getmtime(raw_path)
            triad_mtime = os.path.getmtime(triad_path)
            
            # Include only if images are recent (avatar-enhanced)
            if raw_mtime > 1677628800 and triad_mtime > 1677628800:  # After 2023
                # Header
                char_name = {"marcus": "Senator Marcus Tullius", "gaius": "Gaius Merchant", "julia": "Julia Aurelia"}
                char = r.get("character", "")
                shot = r.get("shot_type", "")
                story.append(Paragraph(
                    f"{char_name.get(char, char)} — {shot.replace('_', ' ').title()}",
                    heading_style
                ))

                # Raw prompt
                story.append(Spacer(1, 4))

                # Images side by side
                raw_img = Image(str(raw_path), width=img_width, height=img_height)
                triad_img = Image(str(triad_path), width=img_width, height=img_height)
            else:
                # Skip old text-only images
                continue

        rv = ev.get("raw_verdict", "?")
        tv = ev.get("triad_verdict", "?")
        pa = ev.get("prompt_adherence", "?")
        oi = ev.get("overall_improvement", "?")

        rv_color = verdict_color(rv)
        tv_color = verdict_color(tv)
        oi_color = PASS_GREEN if oi == "YES" else (PARTIAL_AMBER if oi == "MARGINAL" else FAIL_RED)

        # Build the comparison table
        data = [
            # Row 0: Labels
            [
                Paragraph(f"<b><font color='white'>RAW — {rv}</font></b>", label_style),
                Paragraph(f"<b><font color='white'>TRIAD — {tv}</font></b>", label_style),
            ],
            # Row 1: Images
            [raw_img, triad_img],
            # Row 2: Notes
            [
                Paragraph(f"<b>Raw notes:</b> {ev.get('raw_notes', 'N/A')}", notes_style),
                Paragraph(f"<b>Triad notes:</b> {ev.get('triad_notes', 'N/A')}", notes_style),
            ],
            # Row 3: Details
            [
                Paragraph(
                    f"<b>Anachronisms found:</b> {', '.join(ev.get('raw_anachronisms_found', []))}",
                    notes_style
                ),
                Paragraph(
                    f"<b>Corrections:</b> {', '.join(ev.get('triad_corrections', []))}<br/>"
                    f"<b>Remaining issues:</b> {', '.join(ev.get('triad_remaining_issues', [])) or 'None'}",
                    notes_style
                ),
            ],
            # Row 4: Adherence + Overall
            [
                Paragraph(
                    f"<b>Enhancement goal:</b> {r.get('enhancement_goal', 'N/A')}",
                    notes_style
                ),
                Paragraph(
                    f"<b>Prompt adherence:</b> <font color='{tv_color}'>{pa}</font> — {ev.get('prompt_adherence_notes', '')[:150]}<br/>"
                    f"<b>Overall improvement:</b> <font color='{oi_color}'>{oi}</font> — {ev.get('overall_notes', '')}",
                    notes_style
                ),
            ],
        ]

        col_width = 4.8 * inch
        tbl = Table(data, colWidths=[col_width, col_width])

        raw_label_bg = FAIL_RED
        triad_label_bg = PASS_GREEN if tv == "PASS" else (PARTIAL_AMBER if tv == "PARTIAL" else FAIL_RED)

        tbl.setStyle(TableStyle([
            # Label row backgrounds
            ("BACKGROUND", (0, 0), (0, 0), raw_label_bg),
            ("BACKGROUND", (1, 0), (1, 0), triad_label_bg),
            # Image row
            ("ALIGN", (0, 1), (-1, 1), "CENTER"),
            ("VALIGN", (0, 1), (-1, 1), "MIDDLE"),
            # Notes rows background
            ("BACKGROUND", (0, 2), (0, -1), RAW_BG),
            ("BACKGROUND", (1, 2), (1, -1), TRIAD_BG),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 2), (-1, -1), "TOP"),
        ]))

        story.append(tbl)
        story.append(PageBreak())

    doc.build(story)
    print(f"PDF saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    build_pdf()
