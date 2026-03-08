#!/usr/bin/env python3
"""
Generate a PDF of the Image Cultural Accuracy article from the markdown content.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
    KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

SCRIPT_DIR = Path(__file__).parent
REPO_DIR = SCRIPT_DIR.parent
OUTPUT_PATH = REPO_DIR / "results" / "image_cultural_accuracy_article.pdf"

# Colors
HEADER_BG = HexColor("#1B2A4A")
ACCENT = HexColor("#2E7D32")
LIGHT_BG = HexColor("#F5F5F5")
CODE_BG = HexColor("#F0F0F0")
LINK_BLUE = HexColor("#1565C0")


def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ArticleTitle", parent=styles["Title"],
        fontSize=22, textColor=HEADER_BG, spaceAfter=4, alignment=TA_CENTER,
        leading=26
    )
    subtitle_style = ParagraphStyle(
        "ArticleSubtitle", parent=styles["Normal"],
        fontSize=13, textColor=HexColor("#444444"), alignment=TA_CENTER,
        spaceAfter=20, leading=16, fontName="Helvetica-Oblique"
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=15, textColor=HEADER_BG, spaceBefore=18, spaceAfter=8,
        leading=18, fontName="Helvetica-Bold"
    )
    h3_style = ParagraphStyle(
        "H3", parent=styles["Heading3"],
        fontSize=12, textColor=HexColor("#333333"), spaceBefore=14, spaceAfter=6,
        leading=15, fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, textColor=HexColor("#222222"), leading=14,
        spaceAfter=6, alignment=TA_JUSTIFY
    )
    body_italic = ParagraphStyle(
        "BodyItalic", parent=body_style,
        fontName="Helvetica-Oblique"
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=body_style,
        leftIndent=20, bulletIndent=8, spaceBefore=2, spaceAfter=2
    )
    code_style = ParagraphStyle(
        "Code", parent=styles["Normal"],
        fontSize=8.5, fontName="Courier", textColor=HexColor("#333333"),
        leading=11, backColor=CODE_BG, leftIndent=12, rightIndent=12,
        spaceBefore=4, spaceAfter=4, borderPadding=6
    )
    quote_style = ParagraphStyle(
        "Quote", parent=body_style,
        leftIndent=20, rightIndent=20, fontName="Helvetica-Oblique",
        textColor=HexColor("#555555"), fontSize=9.5, leading=13,
        borderColor=HexColor("#CCCCCC"), borderWidth=0, borderPadding=4
    )
    table_header_style = ParagraphStyle(
        "TableHeader", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold", textColor=white, leading=12
    )
    table_cell_style = ParagraphStyle(
        "TableCell", parent=styles["Normal"],
        fontSize=9, textColor=HexColor("#222222"), leading=12
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold", parent=table_cell_style,
        fontName="Helvetica-Bold"
    )
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=8, textColor=HexColor("#888888"), alignment=TA_CENTER,
        fontName="Helvetica-Oblique", spaceBefore=12
    )

    def make_table(headers, rows, col_widths=None):
        """Create a styled table with header row."""
        data = [[Paragraph(h, table_header_style) for h in headers]]
        for row in rows:
            data.append([Paragraph(str(c), table_cell_style) for c in row])

        if col_widths is None:
            avail = 6.3 * inch
            col_widths = [avail / len(headers)] * len(headers)

        tbl = Table(data, colWidths=col_widths)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return tbl

    def make_two_col_table(headers, rows, col_widths=None):
        """Two-column comparison table (Fails/Works style)."""
        data = [[Paragraph(h, table_header_style) for h in headers]]
        for row in rows:
            data.append([
                Paragraph(f'<font face="Courier" size="8.5">{row[0]}</font>', table_cell_style),
                Paragraph(f'<font face="Courier" size="8.5">{row[1]}</font>', table_cell_style),
            ])
        if col_widths is None:
            col_widths = [3.15 * inch, 3.15 * inch]
        tbl = Table(data, colWidths=col_widths)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), HexColor("#C62828")),
            ("BACKGROUND", (1, 0), (1, 0), ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return tbl

    story = []

    # ── Title ──
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("Image Cultural Accuracy Benchmark", title_style))
    story.append(Paragraph("AI Image Models Hallucinate History — and We Can Fix It", subtitle_style))
    story.append(Spacer(1, 0.3 * inch))

    # ── The Problem ──
    story.append(Paragraph("The Problem", h2_style))
    story.append(Paragraph(
        'Ask an AI image model to "draw a Roman senator giving a speech" and you\'ll get the '
        'Colosseum — a venue for gladiatorial combat, not political debate. Senators spoke in the '
        'Curia Julia or from the Rostra in the Forum Romanum. Ask for "a young Roman woman with '
        'flowers in her hair" and you\'ll get a Renaissance portrait, not a Trajanic-era coiffure '
        'with <i>acus crinales</i> hairpins.',
        body_style
    ))
    story.append(Paragraph(
        'AI image models hallucinate history the same way language models hallucinate facts. The '
        'images look plausible but are filled with anachronisms — wrong buildings, wrong clothing, '
        'wrong objects, wrong social dynamics. For applications in education, entertainment, and '
        'cultural preservation, this matters.',
        body_style
    ))
    story.append(Paragraph(
        'We built a benchmark to measure this problem and a system to fix it.',
        body_style
    ))

    # ── The Benchmark ──
    story.append(Paragraph("The Benchmark: Rome 110 CE", h2_style))
    story.append(Paragraph(
        '<b>3 characters</b> from a historical fiction setting in Trajan\'s Rome:',
        body_style
    ))
    story.append(make_table(
        ["Character", "Role", "Key Visual Markers"],
        [
            ["Senator Marcus Tullius", "Age 58, senior senator, Stoic", "Toga praetexta (purple border), Esquiline Hill villa"],
            ["Gaius the Merchant", "Age 35, freedman trader", "Tunica and pallium (NOT toga), bronze merchant disc"],
            ["Julia Aurelia", "Age 22, patrician daughter", "Stola and palla, Trajanic-era pinned coiffure"],
        ],
        [1.8 * inch, 1.8 * inch, 2.7 * inch]
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        '<b>8 shot types</b> per character = <b>24 image pairs</b> total:',
        body_style
    ))
    story.append(make_table(
        ["Shot Type", "What It Tests"],
        [
            ["Portrait", "Face, clothing, class markers"],
            ["Scene", "Character in a specific location"],
            ["Action", "Period-accurate activities and objects"],
            ["Marketing Hero", "Cinematic composition with historical grounding"],
            ["Dialogue", "Two characters interacting — social dynamics and class distinction"],
            ["Public Gathering", "Civic/religious events with period-accurate crowds"],
            ["Domestic", "Private home/workplace with household details"],
            ["Transit", "Moving through Rome — streets, harbors, transport"],
        ],
        [1.8 * inch, 4.5 * inch]
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        'Each prompt has a <b>deliberately naive "raw" version</b> (what a typical user would type) '
        'and <b>known anachronisms</b> that the raw prompt will produce:',
        body_style
    ))
    story.append(Paragraph(
        '<b>Raw prompt:</b> "Marcus, a Roman senator, writing with a pen and paper at his desk"',
        quote_style
    ))
    story.append(Paragraph(
        '<b>Known anachronisms:</b> Paper and modern pen don\'t exist in 110 CE. Should be wax '
        'tablet or papyrus scroll with a stylus.',
        quote_style
    ))

    # ── The Method ──
    story.append(Paragraph("The Method: Triad Engine Cultural Grounding", h2_style))
    story.append(Paragraph(
        'The Triad Engine is a multi-layer system for grounding AI outputs in domain-specific knowledge:',
        body_style
    ))
    story.append(Paragraph(
        '<bullet>&bull;</bullet><b>μ-layer (cultural guide):</b> A structured knowledge base of '
        'historically accurate details — clothing by social class, architecture by era, objects by '
        'period, social customs by context',
        bullet_style
    ))
    story.append(Paragraph(
        '<bullet>&bull;</bullet><b>Enhancer:</b> Takes the naive user prompt + cultural guide and '
        'produces a historically grounded prompt with period-accurate details',
        bullet_style
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        'The same character avatar image is passed to both the raw and enhanced pipelines, '
        'isolating <b>prompt quality</b> as the only variable.',
        body_style
    ))
    story.append(Paragraph("Pipeline:", body_style))
    story.append(Paragraph(
        'RAW path: &nbsp; avatar + naive prompt → image model → save<br/>'
        'TRIAD path: naive prompt → enhancer (grounded in μ-layer) → enhanced prompt<br/>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
        '→ avatar + enhanced prompt → image model → save',
        code_style
    ))
    story.append(Paragraph(
        'Both paths use the same image generation model with the same character reference image. '
        'The comparison purely isolates whether cultural grounding in the prompt improves historical accuracy.',
        body_style
    ))

    # ── Results ──
    story.append(PageBreak())
    story.append(Paragraph("The Results (Blinded Evaluation)", h2_style))
    story.append(Paragraph(
        'All 24 image pairs were evaluated using a <b>blinded A/B methodology</b> — the judge did '
        'not know which image was RAW and which was TRIAD-enhanced. Images were randomly ordered and '
        'evaluated against the same historical accuracy rubric.',
        body_style
    ))

    # Results comparison table
    results_data = [
        [Paragraph("<b>Metric</b>", table_header_style),
         Paragraph("<b>RAW (naive prompt)</b>", table_header_style),
         Paragraph("<b>TRIAD (enhanced)</b>", table_header_style)],
        [Paragraph("<b>PASS</b> (historically accurate)", table_cell_style),
         Paragraph("2/24 (8.3%)", table_cell_style),
         Paragraph("<b>10/24 (41.7%)</b>", table_cell_bold)],
        [Paragraph("<b>PARTIAL</b> (1-2 minor issues)", table_cell_style),
         Paragraph("20/24 (83.3%)", table_cell_style),
         Paragraph("14/24 (58.3%)", table_cell_style)],
        [Paragraph("<b>FAIL</b> (significant anachronisms)", table_cell_style),
         Paragraph("2/24 (8.3%)", table_cell_style),
         Paragraph("0/24 (0%)", table_cell_style)],
    ]
    results_tbl = Table(results_data, colWidths=[2.4 * inch, 1.95 * inch, 1.95 * inch])
    results_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(results_tbl)
    story.append(Spacer(1, 10))

    story.append(make_table(
        ["Metric", "Score"],
        [
            ["Triad judged more accurate", "19/24 (79.2%)"],
            ["Equal accuracy", "3/24 (12.5%)"],
            ["RAW judged more accurate", "2/24 (8.3%)"],
            ["Clear improvement (YES)", "19/24 (79.2%)"],
            ["Full prompt adherence", "10/24 (41.7%)"],
        ],
        [3.5 * inch, 2.8 * inch]
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        'Raw prompts are not catastrophically wrong — they produce images that are <i>mostly</i> '
        'period-appropriate (83% PARTIAL). But the Triad Engine shifts the distribution significantly '
        'upward: 5x more PASS results, zero FAIL results, and the judge identified TRIAD as more '
        'accurate in nearly 4 out of 5 pairs.',
        body_style
    ))

    # By character
    story.append(Paragraph("By character:", h3_style))
    char_data = [
        [Paragraph("<b>Character</b>", table_header_style),
         Paragraph("<b>RAW P/Pa/F</b>", table_header_style),
         Paragraph("<b>TRIAD P/Pa/F</b>", table_header_style),
         Paragraph("<b>Triad More Accurate</b>", table_header_style)],
        [Paragraph("Marcus", table_cell_style), Paragraph("1/5/2", table_cell_style),
         Paragraph("3/5/0", table_cell_style), Paragraph("7/8 (87.5%)", table_cell_style)],
        [Paragraph("Gaius", table_cell_style), Paragraph("0/8/0", table_cell_style),
         Paragraph("3/5/0", table_cell_style), Paragraph("6/8 (75%)", table_cell_style)],
        [Paragraph("Julia", table_cell_style), Paragraph("1/7/0", table_cell_style),
         Paragraph("4/4/0", table_cell_style), Paragraph("6/8 (75%)", table_cell_style)],
    ]
    char_tbl = Table(char_data, colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 1.8 * inch])
    char_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(char_tbl)
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Notable findings:</b>", body_style))
    story.append(Paragraph(
        '<bullet>&bull;</bullet>Marcus showed the largest gap — his RAW images had the most FAILs '
        '(wrong venue, wrong writing materials) while TRIAD corrected all of them',
        bullet_style
    ))
    story.append(Paragraph(
        '<bullet>&bull;</bullet>Julia had 2 cases where RAW was judged equal or better than TRIAD, '
        'suggesting the naive prompts happened to align with the model\'s training data for female '
        'Roman aesthetics',
        bullet_style
    ))
    story.append(Paragraph(
        '<bullet>&bull;</bullet>Gaius never scored a RAW PASS — freedman-specific details (tunica vs '
        'toga, merchant disc, trade goods) are consistently missed by naive prompts',
        bullet_style
    ))

    # ── What Raw Gets Wrong ──
    story.append(Paragraph("What the Raw Prompts Get Wrong", h2_style))
    story.append(Paragraph(
        'Raw prompts produce images that look plausible but contain subtle anachronisms. In our '
        'blinded evaluation, 92% of raw images were rated PARTIAL or FAIL — the images get the '
        '<i>general feel</i> right but miss period-specific details:',
        body_style
    ))
    story.append(make_table(
        ["Prompt", "Anachronism", "Why It's Wrong"],
        [
            ['"Senator giving a speech in the Colosseum"', "Wrong venue", "Senators spoke in the Curia Julia, not the Colosseum"],
            ['"Writing with a pen and paper"', "Wrong materials", "Romans used wax tablets with stylus, or papyrus with reed pen"],
            ['"Young Roman woman with flowers in her hair"', "Wrong era", "Renaissance aesthetic, not Roman — should be pinned Trajanic coiffure"],
            ['"Merchant wearing Roman clothes"', "Wrong class markers", "Freedmen wore tunica/pallium, NOT the toga (reserved for citizens)"],
            ['"Making a business deal" (handshake)', "Wrong gesture", "Modern handshake instead of Roman dextrarum iunctio (wrist-to-wrist clasp)"],
            ['"Watching a religious ceremony"', "Wrong religion", "Christian-style reverence instead of Roman state religion"],
            ['"Getting ready with her maids"', "Wrong objects", "Wall mirrors (Romans used small polished bronze hand mirrors)"],
            ['"Being carried through the streets in a chair"', "Wrong vehicle", "Generic palanquin instead of Roman lectica with period-correct bearers"],
        ],
        [2.1 * inch, 1.2 * inch, 3.0 * inch]
    ))

    # ── Prompt Engineering Insights ──
    story.append(PageBreak())
    story.append(Paragraph("Prompt Engineering Insights", h2_style))
    story.append(Paragraph(
        'Not all enhancement strategies work equally well. We identified specific failure modes '
        'and developed solutions:',
        body_style
    ))

    # 1. Visual Translation
    story.append(Paragraph("1. Visual Translation Over Terminology", h3_style))
    story.append(Paragraph(
        'Historical terms that image models don\'t know get silently dropped. The fix is describing '
        'what to <b>draw</b>, not what to <b>call</b> it.',
        body_style
    ))
    story.append(make_two_col_table(
        ["Fails", "Works"],
        [
            ['"dextrarum iunctio handshake"', '"two men clasping right hands wrist-to-wrist, elbows raised"'],
            ['"acus crinales hairpins"', '"elaborate pinned upswept hairstyle with metal hairpins"'],
            ['"Mercury amulet"', '"small bronze disc engraved with a winged staff on a leather cord"'],
            ['"collegium banner"', '"painted wooden guild sign with a winged staff symbol"'],
        ]
    ))

    # 2. Priority System
    story.append(Paragraph("2. MUST / SHOULD / BACKGROUND Priority System", h3_style))
    story.append(Paragraph(
        'Image models drop details when overloaded with concurrent specifics. Leading with 2-3 '
        'critical elements improves adherence:',
        body_style
    ))
    story.append(Paragraph(
        'MUST: Julia Aurelia in a deep saffron-yellow stola — vivid golden-yellow<br/>'
        'color, this is critical — with a white wool outer drape.<br/>'
        'MUST: standing OUTDOORS on stone steps of a Roman villa at dusk.<br/>'
        'BACKGROUND: Roman domus stone facade behind her, warm golden evening light.',
        code_style
    ))

    # 3. Outdoor/Indoor
    story.append(Paragraph("3. Explicit OUTDOOR / INDOOR Flagging", h3_style))
    story.append(Paragraph(
        'Without explicit instruction, models default to interior rendering for most prompts. '
        'Adding "OUTDOORS" with a sky description forces correct rendering:',
        body_style
    ))
    story.append(Paragraph(
        'MUST: Marcus Tullius standing OUTDOORS in the Forum Romanum — open sky,<br/>'
        'ancient Roman stone plaza.',
        code_style
    ))

    # 4. Color Emphasis
    story.append(Paragraph("4. Color Emphasis Through Repetition", h3_style))
    story.append(Paragraph(
        'Critical colors buried mid-sentence get lost. Stating the color early AND repeating it '
        'improves adherence:',
        body_style
    ))
    story.append(Paragraph(
        '"deep saffron-yellow stola — vivid golden-yellow color, this is critical"',
        code_style
    ))

    # 5. Ceremonial Scenes
    story.append(Paragraph("5. Ceremonial Scenes: Describe What the Viewer Sees", h3_style))
    story.append(Paragraph(
        'Named ceremonies are unknown to image models. Describe the visual scene instead:',
        body_style
    ))
    story.append(make_two_col_table(
        ["Fails", "Works"],
        [
            ['"Vestal Virgins performing sacred rites"',
             '"women in ankle-length white robes with white woolen bands woven through their '
             'upswept hair, tending a small fire burning on a circular stone altar"'],
        ]
    ))

    # ── Evaluation Methodology ──
    story.append(Paragraph("Evaluation Methodology", h2_style))
    story.append(Paragraph(
        'All 24 image pairs were evaluated using a <b>blinded A/B protocol</b> to eliminate '
        'confirmation bias:',
        body_style
    ))
    story.append(Paragraph(
        '<bullet>&bull;</bullet><b>Randomized order:</b> For each pair, images were randomly assigned '
        'as "Image A" and "Image B" — the judge did not know which was RAW and which was TRIAD',
        bullet_style
    ))
    story.append(Paragraph(
        '<bullet>&bull;</bullet><b>Same rubric for both:</b> Both images were evaluated against the '
        'same historical accuracy criteria, without being told which anachronisms to expect',
        bullet_style
    ))
    story.append(Paragraph(
        '<bullet>&bull;</bullet><b>De-blinding after scoring:</b> A/B verdicts were mapped back to '
        'RAW/TRIAD only after all scores were assigned',
        bullet_style
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        'The judge (Gemini Vision, gemini-2.0-flash) evaluates each image on:',
        body_style
    ))
    story.append(Paragraph(
        '<bullet>&bull;</bullet><b>Historical accuracy verdict:</b> PASS (period-accurate), '
        'PARTIAL (mostly accurate, 1-2 minor issues), or FAIL (significant anachronisms)',
        bullet_style
    ))
    story.append(Paragraph(
        '<bullet>&bull;</bullet><b>Specific details noted:</b> What historical elements are correct '
        'or incorrect',
        bullet_style
    ))
    story.append(Paragraph(
        '<bullet>&bull;</bullet><b>Which image is more accurate:</b> Direct A/B comparison without '
        'knowing which is enhanced',
        bullet_style
    ))
    story.append(Paragraph(
        '<bullet>&bull;</bullet><b>Overall improvement:</b> Whether one image is clearly better '
        '(YES/MARGINAL/NO)',
        bullet_style
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        'This blinded approach prevents the judge from rating RAW images as FAIL simply because it '
        '<i>knows</i> they should contain anachronisms, and prevents it from rating TRIAD images as '
        'PASS simply because it <i>knows</i> they were enhanced. The result is a more honest '
        'assessment of both approaches.',
        body_style
    ))

    # ── Key Takeaway ──
    story.append(Paragraph("Key Takeaway", h2_style))
    story.append(Paragraph(
        'AI image models don\'t catastrophically fail on historical scenes — naive prompts produce '
        '<i>mostly</i> plausible results (83% PARTIAL). But "mostly plausible" isn\'t good enough '
        'for education, entertainment, or cultural preservation. The difference between a generic '
        'toga and a <i>toga praetexta</i>, between the Colosseum and the Curia Julia, between a '
        'modern handshake and a Roman <i>dextrarum iunctio</i> — these details matter.',
        body_style
    ))
    story.append(Paragraph(
        'Cultural grounding through the Triad Engine shifts the accuracy distribution significantly '
        'upward: <b>5x more PASS results</b> (10 vs 2), <b>zero FAIL results</b> (vs 2), and '
        '<b>79% of pairs judged more accurate</b> in a blinded evaluation. The fix is not better '
        'models — it\'s better prompts, informed by domain expertise and structured as visual '
        'descriptions rather than historical terminology.',
        body_style
    ))
    story.append(Paragraph(
        'The same μ-layer architecture that achieved 100% accuracy on a Polish cultural text '
        'benchmark (RAW 91.1% → TRIAD 100.0% on 56 factual questions) transfers to image '
        'generation with consistent improvement.',
        body_style
    ))

    # Footer
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        'Benchmark conducted March 2026. Image generation: gemini-3-pro-image-preview. '
        'Enhancement: gemini-2.0-flash. Evaluation: gemini-2.0-flash (blinded A/B Gemini Vision judge). '
        'All images generated with character avatar reference for identity consistency.',
        footer_style
    ))

    doc.build(story)
    print(f"Article PDF saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
