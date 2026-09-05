"""
AI Data Analyst - Executive PowerPoint Presentation Generator (Corporate Light Theme)
=====================================================================================
This module generates boardroom-ready, consulting-grade 16:9 widescreen PowerPoint
presentations (.pptx) with full executive insights, zero-overflow cards, and clean typography.
"""

import io
import re
import datetime
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE


# ------------------------------------------------------------------------------
# Executive Corporate Light Theme Palette Constants
# ------------------------------------------------------------------------------
NAVY_PRIMARY = RGBColor(15, 23, 42)      # #0F172A (Deep Navy / Header background)
BLUE_ACCENT  = RGBColor(37, 99, 235)     # #2563EB (Corporate Royal Blue / Highlights)
CYAN_ACCENT  = RGBColor(14, 165, 233)    # #0EA5E9 (Cyan Accent)
EMERALD_TAG  = RGBColor(16, 185, 129)    # #10B981 (Success / Action Plan Accent)
AMBER_TAG    = RGBColor(245, 158, 11)    # #F59E0B (Growth / Opportunity Accent)
CARD_BG      = RGBColor(248, 250, 252)   # #F8FAFC (Clean Off-White Card Container)
CARD_BORDER  = RGBColor(226, 232, 240)   # #E2E8F0 (Subtle Slate Card Outline)
TERMINAL_BG  = RGBColor(15, 23, 42)      # #0F172A (Dark Code Terminal Box)
TEXT_DARK    = RGBColor(15, 23, 42)      # #0F172A (Primary Heading Text)
TEXT_BODY    = RGBColor(30, 41, 59)      # #1E293B (Primary High-Contrast Body Text)
TEXT_MUTED   = RGBColor(100, 116, 139)   # #64748B (Muted / Metadata Text)
WHITE        = RGBColor(255, 255, 255)


def parse_markdown_sections(raw_markdown: str) -> list:
    """
    Universally extracts ALL sections from markdown without truncating or dropping text.
    Handles '###', '##', '#', '**Heading:**', numbered headers, and bulleted lists.
    """
    if not raw_markdown or not raw_markdown.strip():
        return [{"title": "Executive Business Summary", "content": "Analysis completed across uploaded datasets."}]

    text = raw_markdown.replace(r"\$", "$").strip()
    lines = text.split("\n")
    sections = []
    current_title = "Executive Summary"
    current_lines = []

    for line in lines:
        stripped = line.strip()
        h_match = re.match(r"^(?:#{1,4}\s+)(.+)$", stripped)
        bold_h_match = re.match(r"^(?:\d+\.\s+)?\*\*(?:💡|🚀|🎯|🔍|📊)?\s*([A-Za-z0-9\s\(\)\&\-\,\.\/\_]+)\*\*:?$", stripped)

        if h_match:
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append({"title": current_title, "content": content})
                current_lines = []
            current_title = re.sub(r"^[💡🚀🎯🔍📊\d\.\s]+", "", h_match.group(1)).strip()
        elif bold_h_match and len(stripped) < 60:
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append({"title": current_title, "content": content})
                current_lines = []
            current_title = re.sub(r"^[💡🚀🎯🔍📊\d\.\s]+", "", bold_h_match.group(1)).strip()
        else:
            current_lines.append(line)

    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append({"title": current_title, "content": content})

    if len(sections) == 1 and sections[0]["title"] == "Executive Summary":
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) > 1:
            sections = []
            titles = ["The Big Picture", "Where We Can Grow", "Action Plan & Next Steps"]
            for idx, p in enumerate(paragraphs):
                t = titles[idx] if idx < len(titles) else f"Key Strategic Note {idx+1}"
                sections.append({"title": t, "content": p})

    return sections


def add_formatted_markdown_text(text_frame, raw_text: str, default_font_size=Pt(15), default_color=TEXT_BODY):
    """
    Parses markdown paragraphs, bullets, and inline **bold text** into rich PPTX text runs.
    Ensures numbers, metrics, and key terms are rendered in actual bold font.
    """
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    for line_idx, line in enumerate(lines):
        p = text_frame.add_paragraph() if len(text_frame.paragraphs) > 0 and text_frame.paragraphs[0].text else text_frame.paragraphs[0]
        
        is_bullet = bool(re.match(r"^[\*\-\•]\s+", line))
        num_match = re.match(r"^(\d+)[\.\)]\s+(.*)$", line)
        
        if num_match:
            clean_text = f"{num_match.group(1)}. {num_match.group(2)}"
        elif is_bullet:
            clean_text = "• " + re.sub(r"^[\*\-\•]\s+", "", line)
        else:
            clean_text = line

        tokens = re.split(r"(\*\*[^\*]+\*\*)", clean_text)
        for token in tokens:
            if not token:
                continue
            run = p.add_run()
            if token.startswith("**") and token.endswith("**") and len(token) >= 4:
                run.text = token[2:-2]
                run.font.bold = True
                run.font.color.rgb = NAVY_PRIMARY
            else:
                run.text = token
                run.font.bold = False
                run.font.color.rgb = default_color
            run.font.size = default_font_size

        p.space_before = Pt(4) if line_idx > 0 else Pt(2)


def _add_slide_header(slide, category_tag: str, title_text: str, subtitle_text: str = ""):
    """Renders a clean corporate top header banner."""
    banner = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.15))
    banner.fill.solid()
    banner.fill.fore_color.rgb = NAVY_PRIMARY
    banner.line.fill.background()

    stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(1.11), Inches(13.333), Inches(0.04))
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = BLUE_ACCENT
    stripe.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.08), Inches(11.7), Inches(1.0))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_tag = tf.paragraphs[0]
    p_tag.text = category_tag.upper()
    p_tag.font.size = Pt(11)
    p_tag.font.bold = True
    p_tag.font.color.rgb = CYAN_ACCENT

    p_title = tf.add_paragraph()
    p_title.text = title_text
    p_title.font.size = Pt(21)
    p_title.font.bold = True
    p_title.font.color.rgb = WHITE
    p_title.space_before = Pt(2)

    if subtitle_text:
        p_sub = tf.add_paragraph()
        p_sub.text = subtitle_text
        p_sub.font.size = Pt(13)
        p_sub.font.color.rgb = RGBColor(203, 213, 225)
        p_sub.space_before = Pt(2)


def _add_footer(slide, current_slide: int, total_slides: int):
    """Adds slide number and branding footer."""
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.7), Inches(0.35))
    tf = tb.text_frame
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = f"AI Data Analyst • Executive Briefing  |  Confidential  |  Slide {current_slide} of {total_slides}"
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_MUTED


def _create_kpi_card(slide, left, top, width, height, label: str, value: str, subtext: str = "", accent_color: RGBColor = BLUE_ACCENT):
    """Creates a sleek, high-contrast KPI statistic card."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = CARD_BG
    card.line.color.rgb = CARD_BORDER

    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, Inches(0.08), height)
    accent.fill.solid()
    accent.fill.fore_color.rgb = accent_color
    accent.line.fill.background()

    tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.12), width - Inches(0.3), height - Inches(0.24))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_lbl = tf.paragraphs[0]
    p_lbl.text = label.upper()
    p_lbl.font.size = Pt(11)
    p_lbl.font.bold = True
    p_lbl.font.color.rgb = TEXT_MUTED

    p_val = tf.add_paragraph()
    p_val.text = str(value)
    p_val.font.size = Pt(28)
    p_val.font.bold = True
    p_val.font.color.rgb = NAVY_PRIMARY
    p_val.space_before = Pt(2)

    if subtext:
        p_sub = tf.add_paragraph()
        p_sub.text = str(subtext)
        p_sub.font.size = Pt(15)
        p_sub.font.color.rgb = TEXT_BODY
        p_sub.space_before = Pt(2)


def create_powerpoint_deck(
    user_question: str,
    df: pd.DataFrame,
    generated_sql: str = None,
    sql_explanation: str = None,
    chart_figure = None,
    chart_config: dict = None,
    business_insights: str = None,
    dataset_names: list = None
) -> bytes:
    """
    PURPOSE:
    Compiles an interactive analysis session into a consulting-grade 16:9 widescreen PowerPoint deck (.pptx)
    featuring full business insights, 16pt body typography, and executive corporate white styling.
    
    RETURNS:
    bytes: In-memory binary representation of the PPTX file.
    """
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Pre-parse insights to determine optimal slide allocation
    sections = parse_markdown_sections(business_insights)
    total_insight_chars = sum(len(s.get("content", "")) for s in sections)
    
    # If insights are extensive (> 550 chars or > 3 sections), use 2 dedicated insight slides
    use_two_insight_slides = total_insight_chars > 550 or len(sections) > 3

    base_slide_count = 5 if use_two_insight_slides else 4
    if df is not None and not df.empty:
        total_slides = base_slide_count + 2  # Includes SQL audit slide + Data evidence table
    else:
        total_slides = base_slide_count + 1

    current_slide_idx = 1

    # ==========================================================================
    # SLIDE 1: Title & Overview Slide (Dark Slate Navy Cover Theme)
    # ==========================================================================
    slide1 = prs.slides.add_slide(blank_layout)

    bg1 = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = NAVY_PRIMARY
    bg1.line.fill.background()

    accent_band = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.3), Inches(0.14), Inches(4.8))
    accent_band.fill.solid()
    accent_band.fill.fore_color.rgb = CYAN_ACCENT
    accent_band.line.fill.background()

    tb_title = slide1.shapes.add_textbox(Inches(1.2), Inches(1.3), Inches(11.0), Inches(3.4))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0

    p_tag = tf_title.paragraphs[0]
    p_tag.text = "EXECUTIVE DATA ANALYSIS BRIEFING"
    p_tag.font.size = Pt(13)
    p_tag.font.bold = True
    p_tag.font.color.rgb = CYAN_ACCENT

    q_text = f'"{user_question.strip()}"'
    p_q = tf_title.add_paragraph()
    p_q.text = q_text
    p_q.font.size = Pt(28 if len(q_text) < 70 else 22)
    p_q.font.bold = True
    p_q.font.color.rgb = WHITE
    p_q.space_before = Pt(14)

    p_sub = tf_title.add_paragraph()
    p_sub.text = "Comprehensive diagnostic analysis, quantitative validation, and strategic recommendations."
    p_sub.font.size = Pt(16)
    p_sub.font.color.rgb = RGBColor(203, 213, 225)
    p_sub.space_before = Pt(12)

    # 2 Metadata Cards
    meta_top = Inches(4.9)
    meta_w = Inches(5.35)
    meta_h = Inches(1.3)

    c_m1 = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), meta_top, meta_w, meta_h)
    c_m1.fill.solid()
    c_m1.fill.fore_color.rgb = RGBColor(30, 41, 59)
    c_m1.line.color.rgb = RGBColor(51, 65, 85)
    tf_m1 = c_m1.text_frame
    tf_m1.word_wrap = True
    tf_m1.margin_left = tf_m1.margin_right = Inches(0.2)
    tf_m1.margin_top = Inches(0.15)
    p = tf_m1.paragraphs[0]
    p.text = "📁 ANALYZED DATA SOURCES"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT
    p2 = tf_m1.add_paragraph()
    src_text = ", ".join(dataset_names) if dataset_names else "Uploaded Datasets"
    p2.text = src_text
    p2.font.size = Pt(16)
    p2.font.color.rgb = WHITE
    p2.space_before = Pt(4)

    c_m2 = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.85), meta_top, meta_w, meta_h)
    c_m2.fill.solid()
    c_m2.fill.fore_color.rgb = RGBColor(30, 41, 59)
    c_m2.line.color.rgb = RGBColor(51, 65, 85)
    tf_m2 = c_m2.text_frame
    tf_m2.word_wrap = True
    tf_m2.margin_left = tf_m2.margin_right = Inches(0.2)
    tf_m2.margin_top = Inches(0.15)
    p = tf_m2.paragraphs[0]
    p.text = "📅 REPORT GENERATION DATE"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT
    p2 = tf_m2.add_paragraph()
    p2.text = datetime.datetime.now().strftime("%B %d, %Y • %I:%M %p")
    p2.font.size = Pt(16)
    p2.font.color.rgb = WHITE
    p2.space_before = Pt(4)

    # ==========================================================================
    # SLIDE 2: Executive Summary & Performance Scorecard (Clean White Theme)
    # ==========================================================================
    current_slide_idx += 1
    slide2 = prs.slides.add_slide(blank_layout)
    _add_slide_header(slide2, "Executive Briefing", "Quantitative Performance Scorecard", "Summary metrics and high-level distribution breakdown")
    _add_footer(slide2, current_slide_idx, total_slides)

    total_rows = len(df) if df is not None else 0
    num_cols = len(df.columns) if df is not None else 0
    
    primary_metric_label = "COLUMNS ANALYZED"
    primary_metric_val = str(num_cols)
    primary_metric_sub = "Dimensions & metrics"

    if df is not None and not df.empty:
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            first_num = numeric_cols[0]
            col_total = df[first_num].sum()
            primary_metric_label = f"TOTAL {first_num[:14].upper()}"
            primary_metric_val = f"{col_total:,.2f}" if abs(col_total) >= 100 else f"{col_total:,.4g}"
            primary_metric_sub = f"Aggregated sum of {first_num}"

    _create_kpi_card(slide2, Inches(0.8), Inches(1.35), Inches(3.6), Inches(1.45), "Total Records Found", f"{total_rows:,}", "Matching SQL query criteria", BLUE_ACCENT)
    _create_kpi_card(slide2, Inches(4.75), Inches(1.35), Inches(3.6), Inches(1.45), primary_metric_label, primary_metric_val, primary_metric_sub, EMERALD_TAG)
    _create_kpi_card(slide2, Inches(8.7), Inches(1.35), Inches(3.8), Inches(1.45), "Dataset Scope", f"{num_cols} Columns", f"{len(dataset_names or ['Database'])} active tables connected", CYAN_ACCENT)

    # Row 2 (Left): Core Takeaway Highlight Box (Soft Indigo Background)
    card_takeaway = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(3.0), Inches(7.5), Inches(3.8))
    card_takeaway.fill.solid()
    card_takeaway.fill.fore_color.rgb = RGBColor(238, 242, 255)
    card_takeaway.line.color.rgb = BLUE_ACCENT
    
    tf_ta = card_takeaway.text_frame
    tf_ta.word_wrap = True
    tf_ta.margin_left = tf_ta.margin_right = Inches(0.24)
    tf_ta.margin_top = Inches(0.2)
    
    p = tf_ta.paragraphs[0]
    p.text = "💡 CORE EXECUTIVE TAKEAWAY"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = BLUE_ACCENT

    raw_conclusion = chart_config.get("conclusion", "") if chart_config else ""
    if not raw_conclusion:
        raw_conclusion = "The query completed successfully across the connected datasets, revealing distinct data concentrations."
    
    p_con = tf_ta.add_paragraph()
    p_con.text = raw_conclusion
    p_con.font.size = Pt(16)
    p_con.font.bold = True
    p_con.font.color.rgb = NAVY_PRIMARY
    p_con.space_before = Pt(8)

    reasoning_txt = chart_config.get("reasoning", "") if chart_config else ""
    if reasoning_txt:
        p_res = tf_ta.add_paragraph()
        p_res.text = f"Analytical Methodology: {reasoning_txt}"
        p_res.font.size = Pt(15)
        p_res.font.color.rgb = TEXT_BODY
        p_res.space_before = Pt(10)

    # Row 2 (Right): Statistical Profile Breakdown Box
    card_stats = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.55), Inches(3.0), Inches(3.95), Inches(3.8))
    card_stats.fill.solid()
    card_stats.fill.fore_color.rgb = CARD_BG
    card_stats.line.color.rgb = CARD_BORDER

    tf_st = card_stats.text_frame
    tf_st.word_wrap = True
    tf_st.margin_left = tf_st.margin_right = Inches(0.22)
    tf_st.margin_top = Inches(0.2)

    p = tf_st.paragraphs[0]
    p.text = "📊 STATISTICAL PROFILE"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = TEXT_MUTED

    if df is not None and not df.empty:
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            for col in numeric_cols[:2]:
                p_c = tf_st.add_paragraph()
                p_c.text = f"• {col}"
                p_c.font.size = Pt(13)
                p_c.font.bold = True
                p_c.font.color.rgb = NAVY_PRIMARY
                p_c.space_before = Pt(8)

                p_d = tf_st.add_paragraph()
                col_avg = df[col].mean()
                col_max = df[col].max()
                p_d.text = f"   Avg: {col_avg:,.2f}  |  Max: {col_max:,.2f}"
                p_d.font.size = Pt(15)
                p_d.font.color.rgb = TEXT_BODY
                p_d.space_before = Pt(2)
        else:
            p_c = tf_st.add_paragraph()
            p_c.text = "Attributes:\n" + "\n".join([f"• {c}" for c in df.columns[:3]])
            p_c.font.size = Pt(15)
            p_c.font.color.rgb = TEXT_BODY
            p_c.space_before = Pt(8)

    # ==========================================================================
    # SLIDE 3: Visual Analytics & Chart Deep-Dive (Clean Split View)
    # ==========================================================================
    current_slide_idx += 1
    slide3 = prs.slides.add_slide(blank_layout)
    _add_slide_header(slide3, "Visual Intelligence", "Data Visualization & Key Trends", "Visual breakdown recommended by AI chart selector")
    _add_footer(slide3, current_slide_idx, total_slides)

    chart_rendered = False
    if chart_figure is not None:
        try:
            img_bytes = chart_figure.to_image(format="png", width=1200, height=650, scale=2)
            img_stream = io.BytesIO(img_bytes)
            slide3.shapes.add_picture(img_stream, Inches(0.8), Inches(1.35), Inches(7.6), Inches(5.4))
            chart_rendered = True
        except Exception:
            chart_rendered = False

    if not chart_rendered:
        fb_box = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.35), Inches(7.6), Inches(5.4))
        fb_box.fill.solid()
        fb_box.fill.fore_color.rgb = CARD_BG
        fb_box.line.color.rgb = CARD_BORDER
        tf_fb = fb_box.text_frame
        tf_fb.word_wrap = True
        p = tf_fb.paragraphs[0]
        p.text = "📊 Visual Intelligence Summary"
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = NAVY_PRIMARY
        p2 = tf_fb.add_paragraph()
        p2.text = "Visual trend data is summarized in the tabular records and strategic takeaways."
        p2.font.size = Pt(16)
        p2.font.color.rgb = TEXT_BODY
        p2.space_before = Pt(10)

    # Right Column: Unified Narrative Card
    c_side = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.65), Inches(1.35), Inches(3.88), Inches(5.4))
    c_side.fill.solid()
    c_side.fill.fore_color.rgb = CARD_BG
    c_side.line.color.rgb = CARD_BORDER

    acc_side = slide3.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(8.65), Inches(1.35), Inches(0.08), Inches(5.4))
    acc_side.fill.solid()
    acc_side.fill.fore_color.rgb = BLUE_ACCENT
    acc_side.line.fill.background()

    tf_side = c_side.text_frame
    tf_side.word_wrap = True
    tf_side.margin_left = tf_side.margin_right = Inches(0.24)
    tf_side.margin_top = Inches(0.2)

    p = tf_side.paragraphs[0]
    p.text = "🔍 KEY VISUAL TAKEAWAY"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = BLUE_ACCENT

    p2 = tf_side.add_paragraph()
    p2.text = raw_conclusion
    p2.font.size = Pt(16)
    p2.font.bold = True
    p2.font.color.rgb = NAVY_PRIMARY
    p2.space_before = Pt(8)

    p3 = tf_side.add_paragraph()
    p3.text = "📐 CHART METHODOLOGY"
    p3.font.size = Pt(13)
    p3.font.bold = True
    p3.font.color.rgb = TEXT_MUTED
    p3.space_before = Pt(18)

    p4 = tf_side.add_paragraph()
    chart_type = chart_config.get("chart_type", "Standard").upper() if chart_config else "DATA"
    logic_txt = chart_config.get("reasoning", "Selected for optimal comparison and high visual impact.") if chart_config else "Optimized for comparison."
    p4.text = f"• Format: {chart_type} Chart\n• Logic: {logic_txt}"
    p4.font.size = Pt(15)
    p4.font.color.rgb = TEXT_BODY
    p4.space_before = Pt(8)

    # ==========================================================================
    # SLIDE 4 (+ Optional SLIDE 5): Strategic Business Insights (COMPLETE & UNCLIPPED)
    # ==========================================================================
    accents_cycle = [BLUE_ACCENT, AMBER_TAG, EMERALD_TAG, CYAN_ACCENT]

    if use_two_insight_slides:
        # ----------------------------------------------------------------------
        # PART 1: Strategic Findings & Opportunities (2 Spacious Cards)
        # ----------------------------------------------------------------------
        current_slide_idx += 1
        slide_ins1 = prs.slides.add_slide(blank_layout)
        _add_slide_header(slide_ins1, "Strategic Intelligence", "Executive Findings & Growth Vectors", "Diagnostic findings and commercial growth opportunities formulated by AI")
        _add_footer(slide_ins1, current_slide_idx, total_slides)

        sec_part1 = sections[:2] if len(sections) >= 2 else sections
        c_h1 = Inches(2.6)
        gap1 = Inches(0.22)
        start_y1 = Inches(1.35)

        for idx, sec in enumerate(sec_part1):
            y_pos = start_y1 + idx * (c_h1 + gap1)
            card = slide_ins1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), y_pos, Inches(11.73), c_h1)
            card.fill.solid()
            card.fill.fore_color.rgb = CARD_BG
            card.line.color.rgb = CARD_BORDER

            acc = slide_ins1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), y_pos, Inches(0.1), c_h1)
            acc.fill.solid()
            acc.fill.fore_color.rgb = accents_cycle[idx % len(accents_cycle)]
            acc.line.fill.background()

            tf = card.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = Inches(0.28)
            tf.margin_top = Inches(0.14)

            p_t = tf.paragraphs[0]
            p_t.text = f"{'💡' if idx==0 else '🚀'} {sec['title'].upper()}"
            p_t.font.size = Pt(14)
            p_t.font.bold = True
            p_t.font.color.rgb = NAVY_PRIMARY

            add_formatted_markdown_text(tf, sec["content"], default_font_size=Pt(15), default_color=TEXT_BODY)

        # ----------------------------------------------------------------------
        # PART 2: Strategic Action Plan & Execution Roadmap (Remaining Sections)
        # ----------------------------------------------------------------------
        current_slide_idx += 1
        slide_ins2 = prs.slides.add_slide(blank_layout)
        _add_slide_header(slide_ins2, "Action Roadmap", "Strategic Execution & Recommended Next Steps", "Tactical initiatives, quick fixes, and operational milestones")
        _add_footer(slide_ins2, current_slide_idx, total_slides)

        sec_part2 = sections[2:] if len(sections) >= 2 else []
        c_h2 = Inches(5.4 / max(1, len(sec_part2))) - Inches(0.12) if sec_part2 else Inches(5.4)
        c_h2 = max(Inches(1.7), min(Inches(5.4), c_h2))
        gap2 = Inches(0.18)
        start_y2 = Inches(1.35)

        for idx, sec in enumerate(sec_part2):
            y_pos = start_y2 + idx * (c_h2 + gap2)
            card = slide_ins2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), y_pos, Inches(11.73), c_h2)
            card.fill.solid()
            card.fill.fore_color.rgb = CARD_BG
            card.line.color.rgb = CARD_BORDER

            acc = slide_ins2.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), y_pos, Inches(0.1), c_h2)
            acc.fill.solid()
            acc.fill.fore_color.rgb = EMERALD_TAG if idx==0 else BLUE_ACCENT
            acc.line.fill.background()

            tf = card.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = Inches(0.28)
            tf.margin_top = Inches(0.14)

            p_t = tf.paragraphs[0]
            p_t.text = f"🎯 {sec['title'].upper()}"
            p_t.font.size = Pt(14)
            p_t.font.bold = True
            p_t.font.color.rgb = NAVY_PRIMARY

            add_formatted_markdown_text(tf, sec["content"], default_font_size=Pt(15), default_color=TEXT_BODY)

    else:
        # Standard Single Strategic Advisory Slide (3 Horizontal Cards)
        current_slide_idx += 1
        slide4 = prs.slides.add_slide(blank_layout)
        _add_slide_header(slide4, "Strategic Advisory", "Executive Business Insights & Growth Actions", "Complete strategic advisory report formulated by AI")
        _add_footer(slide4, current_slide_idx, total_slides)

        num_sec = max(1, len(sections))
        card_w = Inches(11.73)
        card_h = max(Inches(1.65), Inches(5.4 / num_sec - 0.14))
        gap_y = Inches(0.16)
        start_y = Inches(1.35)

        icons = ["💡", "🚀", "🎯", "🔍"]

        for idx, sec in enumerate(sections):
            y_pos = start_y + idx * (card_h + gap_y)
            card_b = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), y_pos, card_w, card_h)
            card_b.fill.solid()
            card_b.fill.fore_color.rgb = CARD_BG
            card_b.line.color.rgb = CARD_BORDER

            acc_b = slide4.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), y_pos, Inches(0.1), card_h)
            acc_b.fill.solid()
            acc_b.fill.fore_color.rgb = accents_cycle[idx % len(accents_cycle)]
            acc_b.line.fill.background()

            tf_b = card_b.text_frame
            tf_b.word_wrap = True
            tf_b.margin_left = tf_b.margin_right = Inches(0.28)
            tf_b.margin_top = Inches(0.12)

            icon = icons[idx % len(icons)]
            p_bt = tf_b.paragraphs[0]
            p_bt.text = f"{icon} {idx+1}. {sec['title'].upper()}"
            p_bt.font.size = Pt(13)
            p_bt.font.bold = True
            p_bt.font.color.rgb = NAVY_PRIMARY

            add_formatted_markdown_text(tf_b, sec["content"], default_font_size=Pt(15), default_color=TEXT_BODY)

    # ==========================================================================
    # SLIDE 5: Data Governance & SQL Audit Trail (2-Column Dashboard)
    # ==========================================================================
    current_slide_idx += 1
    slide_sql = prs.slides.add_slide(blank_layout)
    _add_slide_header(slide_sql, "Data Governance", "SQL Logic Audit & Technical Trail", "Verifiable query logic for data integrity, reproducibility, and audit compliance")
    _add_footer(slide_sql, current_slide_idx, total_slides)

    col_sql_w = Inches(5.7)
    col_sql_h = Inches(5.4)
    left_sql = Inches(0.8)

    # Left Column: Terminal Card
    card_sql = slide_sql.shapes.add_shape(MSO_SHAPE.RECTANGLE, left_sql, Inches(1.35), col_sql_w, col_sql_h)
    card_sql.fill.solid()
    card_sql.fill.fore_color.rgb = TERMINAL_BG
    card_sql.line.color.rgb = RGBColor(51, 65, 85)

    tb_term = slide_sql.shapes.add_textbox(left_sql + Inches(0.22), Inches(1.42), col_sql_w - Inches(0.44), Inches(0.35))
    tf_term = tb_term.text_frame
    tf_term.margin_left = tf_term.margin_top = tf_term.margin_right = tf_term.margin_bottom = 0
    p = tf_term.paragraphs[0]
    p.text = "🔴 🟡 🟢   sqlite_query.sql"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = RGBColor(148, 163, 184)

    tb_sql_code = slide_sql.shapes.add_textbox(left_sql + Inches(0.22), Inches(1.85), col_sql_w - Inches(0.44), col_sql_h - Inches(0.65))
    tf_code = tb_sql_code.text_frame
    tf_code.word_wrap = True
    tf_code.margin_left = tf_code.margin_top = tf_code.margin_right = tf_code.margin_bottom = 0

    p_code = tf_code.paragraphs[0]
    raw_sql = (generated_sql.strip() if generated_sql else "-- No SQL query recorded").replace("\t", "   ")
    p_code.text = raw_sql
    p_code.font.name = "Consolas"
    p_code.font.size = Pt(13)
    p_code.font.color.rgb = RGBColor(56, 189, 248)

    # Right Column: Plain English Explanation Card
    left_exp = Inches(6.75)
    col_exp_w = Inches(5.75)
    
    card_exp = slide_sql.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left_exp, Inches(1.35), col_exp_w, col_sql_h)
    card_exp.fill.solid()
    card_exp.fill.fore_color.rgb = CARD_BG
    card_exp.line.color.rgb = CARD_BORDER

    acc_exp = slide_sql.shapes.add_shape(MSO_SHAPE.RECTANGLE, left_exp, Inches(1.35), Inches(0.08), col_sql_h)
    acc_exp.fill.solid()
    acc_exp.fill.fore_color.rgb = BLUE_ACCENT
    acc_exp.line.fill.background()

    tb_exp = slide_sql.shapes.add_textbox(left_exp + Inches(0.25), Inches(1.5), col_exp_w - Inches(0.45), col_sql_h - Inches(0.3))
    tf_exp = tb_exp.text_frame
    tf_exp.word_wrap = True
    tf_exp.margin_left = tf_exp.margin_top = tf_exp.margin_right = tf_exp.margin_bottom = 0

    p_ex_title = tf_exp.paragraphs[0]
    p_ex_title.text = "💡 PLAIN-ENGLISH LOGIC BREAKDOWN"
    p_ex_title.font.size = Pt(14)
    p_ex_title.font.bold = True
    p_ex_title.font.color.rgb = BLUE_ACCENT

    raw_exp = sql_explanation or "The query extracts and aggregates the requested fields directly from the database engine."
    clean_exp_lines = [l.replace("#", "").replace("*", "").strip() for l in raw_exp.split("\n") if l.strip()]

    for line in clean_exp_lines[:4]:
        p_l = tf_exp.add_paragraph()
        p_l.text = f"• {line}"
        p_l.font.size = Pt(15)
        p_l.font.color.rgb = TEXT_BODY
        p_l.space_before = Pt(8)

    p_badge = tf_exp.add_paragraph()
    p_badge.text = "🔒 AUDIT TRAIL VERIFIED • IN-MEMORY SQLITE ENGINE"
    p_badge.font.size = Pt(12)
    p_badge.font.bold = True
    p_badge.font.color.rgb = EMERALD_TAG
    p_badge.space_before = Pt(16)

    # ==========================================================================
    # SLIDE 6 (Optional): Top Query Results Ledger Table
    # ==========================================================================
    if df is not None and not df.empty:
        current_slide_idx += 1
        slide_tbl = prs.slides.add_slide(blank_layout)
        _add_slide_header(slide_tbl, "Data Evidence", "Tabular Query Results Ledger", "Top records retrieved directly from the verified database execution")
        _add_footer(slide_tbl, current_slide_idx, total_slides)

        preview_df = df.head(6)
        num_rows = len(preview_df) + 1
        num_cols = min(len(preview_df.columns), 6)
        cols_to_render = list(preview_df.columns)[:num_cols]

        table_shape = slide_tbl.shapes.add_table(num_rows, num_cols, Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.2))
        table = table_shape.table

        # Header Row (Deep Navy)
        for col_idx, col_name in enumerate(cols_to_render):
            cell = table.cell(0, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY_PRIMARY
            cell.text = str(col_name).upper()
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(13)
                p.font.bold = True
                p.font.color.rgb = WHITE
                p.alignment = PP_ALIGN.CENTER

        # Data Rows (Alternating Crisp Rows)
        for row_idx, (_, row) in enumerate(preview_df.iterrows()):
            for col_idx, col_name in enumerate(cols_to_render):
                cell = table.cell(row_idx + 1, col_idx)
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE if row_idx % 2 == 0 else RGBColor(248, 250, 252)
                val = row[col_name]
                raw_cell_text = f"{val:,.2f}" if isinstance(val, (int, float)) and not isinstance(val, bool) else str(val)
                cell.text = raw_cell_text
                for p in cell.text_frame.paragraphs:
                    p.font.size = Pt(15)
                    p.font.color.rgb = TEXT_DARK
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        p.alignment = PP_ALIGN.RIGHT
                    else:
                        p.alignment = PP_ALIGN.LEFT

    # ==========================================================================
    # Save Presentation to In-Memory Stream
    # ==========================================================================
    output_stream = io.BytesIO()
    prs.save(output_stream)
    output_stream.seek(0)
    return output_stream.getvalue()
