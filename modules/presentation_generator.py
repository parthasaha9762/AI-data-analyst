"""
AI Data Analyst - PowerPoint Presentation Generator Module
===========================================================
This module generates boardroom-ready, executive 16:9 widescreen PowerPoint
presentations (.pptx) summarizing an AI data analysis session.
"""

import io
import datetime
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE


# ------------------------------------------------------------------------------
# Corporate Color Palette Constants (Slate & Corporate Blue)
# ------------------------------------------------------------------------------
NAVY_PRIMARY = RGBColor(15, 23, 42)      # #0F172A (Deep Navy / Header background)
BLUE_ACCENT  = RGBColor(37, 99, 235)     # #2563EB (Corporate Blue / Highlights)
CARD_BG      = RGBColor(241, 245, 249)   # #F1F5F9 (Light Slate / Card containers)
TEXT_DARK    = RGBColor(15, 23, 42)      # #0F172A (Primary text)
TEXT_MUTED   = RGBColor(100, 116, 139)   # #64748B (Secondary / Subtitle text)
WHITE        = RGBColor(255, 255, 255)
GREEN_ACCENT = RGBColor(16, 185, 129)    # #10B981 (Success / Highlight)


def _add_slide_header(slide, title_text: str, subtitle_text: str = ""):
    """Adds a consistent branded top header bar to a slide."""
    banner = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.1))
    banner.fill.solid()
    banner.fill.fore_color.rgb = NAVY_PRIMARY
    banner.line.fill.background()

    stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(1.06), Inches(13.333), Inches(0.04))
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = BLUE_ACCENT
    stripe.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.15), Inches(11.7), Inches(0.8))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = WHITE
    
    if subtitle_text:
        p2 = tf.add_paragraph()
        p2.text = subtitle_text
        p2.font.size = Pt(11)
        p2.font.color.rgb = RGBColor(148, 163, 184)


def _add_footer(slide, current_slide: int, total_slides: int):
    """Adds slide number and branding footer."""
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(7.0), Inches(11.7), Inches(0.4))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = f"AI Data Analyst • Executive Briefing | Slide {current_slide} of {total_slides}"
    p.font.size = Pt(9)
    p.font.color.rgb = TEXT_MUTED


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
    Compiles an interactive analysis session into a 16:9 widescreen PowerPoint deck (.pptx).
    
    RETURNS:
    bytes: In-memory binary representation of the PPTX file.
    """
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    total_slides = 6 if (df is not None and not df.empty) else 5

    # ==========================================================================
    # SLIDE 1: Title & Overview Slide
    # ==========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    bg = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY_PRIMARY
    bg.line.fill.background()

    tb1 = slide1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.333), Inches(4.5))
    tf1 = tb1.text_frame
    tf1.word_wrap = True

    p_tag = tf1.paragraphs[0]
    p_tag.text = "EXECUTIVE DATA BRIEFING"
    p_tag.font.size = Pt(14)
    p_tag.font.bold = True
    p_tag.font.color.rgb = BLUE_ACCENT

    p_title = tf1.add_paragraph()
    p_title.text = f'"{user_question}"'
    p_title.font.size = Pt(30)
    p_title.font.bold = True
    p_title.font.color.rgb = WHITE
    p_title.space_before = Pt(16)
    p_title.space_after = Pt(24)

    sources = ", ".join(dataset_names) if dataset_names else "Uploaded Dataset(s)"
    date_str = datetime.datetime.now().strftime("%B %d, %Y • %I:%M %p")

    p_meta = tf1.add_paragraph()
    p_meta.text = f"📁 Data Source(s): {sources}\n📅 Generated: {date_str}\n🤖 Powered by: AI Data Analyst & Google Gemini"
    p_meta.font.size = Pt(12)
    p_meta.font.color.rgb = RGBColor(203, 213, 225)
    p_meta.line_spacing = 1.4

    # ==========================================================================
    # SLIDE 2: Executive Summary & High-Level Metrics
    # ==========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    _add_slide_header(slide2, "Executive Summary & Key Metrics", "Overview of quantitative query results and key figures")
    _add_footer(slide2, 2, total_slides)

    # Card 1: Total Records Returned
    card1 = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(3.6), Inches(2.2))
    card1.fill.solid()
    card1.fill.fore_color.rgb = CARD_BG
    card1.line.color.rgb = RGBColor(226, 232, 240)
    tf_c1 = card1.text_frame
    tf_c1.word_wrap = True
    p = tf_c1.paragraphs[0]
    p.text = "TOTAL RECORDS"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = TEXT_MUTED
    p2 = tf_c1.add_paragraph()
    p2.text = str(len(df)) if df is not None else "0"
    p2.font.size = Pt(38)
    p2.font.bold = True
    p2.font.color.rgb = BLUE_ACCENT
    p3 = tf_c1.add_paragraph()
    p3.text = f"{len(df.columns) if df is not None else 0} dimension/metric columns analyzed"
    p3.font.size = Pt(10)
    p3.font.color.rgb = TEXT_MUTED

    # Card 2: Core Conclusion Callout
    card2 = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.7), Inches(1.5), Inches(7.8), Inches(2.2))
    card2.fill.solid()
    card2.fill.fore_color.rgb = RGBColor(238, 242, 255)
    card2.line.color.rgb = BLUE_ACCENT
    tf_c2 = card2.text_frame
    tf_c2.word_wrap = True
    p = tf_c2.paragraphs[0]
    p.text = "💡 CORE ANALYTICAL TAKEAWAY"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = BLUE_ACCENT
    p2 = tf_c2.add_paragraph()
    conclusion_txt = chart_config.get("conclusion", "Quantitative analysis completed successfully.") if chart_config else "Quantitative analysis completed successfully."
    p2.text = conclusion_txt
    p2.font.size = Pt(13)
    p2.font.bold = True
    p2.font.color.rgb = TEXT_DARK
    p2.space_before = Pt(8)

    # Card 3: Numeric Summary Box (Below)
    card3 = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.0), Inches(11.7), Inches(2.7))
    card3.fill.solid()
    card3.fill.fore_color.rgb = CARD_BG
    card3.line.color.rgb = RGBColor(226, 232, 240)
    tf_c3 = card3.text_frame
    tf_c3.word_wrap = True
    p = tf_c3.paragraphs[0]
    p.text = "📊 STATISTICAL DISTRIBUTION BREAKDOWN"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = TEXT_MUTED

    if df is not None and not df.empty:
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            for col in numeric_cols[:4]:
                p_stat = tf_c3.add_paragraph()
                col_sum = df[col].sum()
                col_avg = df[col].mean()
                col_max = df[col].max()
                p_stat.text = f"• {col}: Total = {col_sum:,.2f} | Avg = {col_avg:,.2f} | Max = {col_max:,.2f}"
                p_stat.font.size = Pt(12)
                p_stat.font.color.rgb = TEXT_DARK
                p_stat.space_before = Pt(6)
        else:
            p_stat = tf_c3.add_paragraph()
            p_stat.text = "• Categorical result set containing textual dimensions."
            p_stat.font.size = Pt(12)
            p_stat.font.color.rgb = TEXT_DARK

    # ==========================================================================
    # SLIDE 3: Visual Analytics Chart
    # ==========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    _add_slide_header(slide3, "Visual Analytics & Trends", "AI-recommended visual representation of query results")
    _add_footer(slide3, 3, total_slides)

    chart_rendered = False
    if chart_figure is not None:
        try:
            img_bytes = chart_figure.to_image(format="png", width=1100, height=480, scale=2)
            img_stream = io.BytesIO(img_bytes)
            slide3.shapes.add_picture(img_stream, Inches(1.2), Inches(1.5), Inches(10.9), Inches(4.7))
            chart_rendered = True
        except Exception:
            chart_rendered = False

    if not chart_rendered:
        box = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.5), Inches(2.2), Inches(10.3), Inches(3.5))
        box.fill.solid()
        box.fill.fore_color.rgb = CARD_BG
        box.line.color.rgb = RGBColor(226, 232, 240)
        tf_fb = box.text_frame
        p = tf_fb.paragraphs[0]
        p.text = "📊 Chart Visualization Summary"
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = TEXT_DARK
        p2 = tf_fb.add_paragraph()
        reason = chart_config.get("reasoning", "Tabular data preview available on subsequent slide.") if chart_config else "Tabular results available."
        p2.text = f"Visual takeaway: {reason}"
        p2.font.size = Pt(13)
        p2.font.color.rgb = TEXT_MUTED
        p2.space_before = Pt(12)

    # ==========================================================================
    # SLIDE 4: Strategic Business Insights & Growth Actions
    # ==========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    _add_slide_header(slide4, "Strategic Business Insights & Growth Actions", "Executive recommendations generated by Google Gemini Pro")
    _add_footer(slide4, 4, total_slides)

    card_ins = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3))
    card_ins.fill.solid()
    card_ins.fill.fore_color.rgb = CARD_BG
    card_ins.line.color.rgb = RGBColor(226, 232, 240)
    tf_ins = card_ins.text_frame
    tf_ins.word_wrap = True

    if business_insights and business_insights.strip():
        lines = [line.strip() for line in business_insights.split("\n") if line.strip()]
        first = True
        for line in lines[:10]:
            cleaned = line.replace("#", "").replace("*", "").strip()
            if cleaned:
                p_item = tf_ins.paragraphs[0] if first else tf_ins.add_paragraph()
                p_item.text = f"•  {cleaned}"
                p_item.font.size = Pt(11)
                p_item.font.color.rgb = TEXT_DARK
                p_item.space_before = Pt(4)
                first = False
    else:
        p_item = tf_ins.paragraphs[0]
        p_item.text = "• Business insights were not requested for this query execution."
        p_item.font.size = Pt(13)
        p_item.font.color.rgb = TEXT_MUTED

    # ==========================================================================
    # SLIDE 5: Data Governance & SQL Audit Trail
    # ==========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    _add_slide_header(slide5, "Data Governance & SQL Audit Trail", "Verifiable query logic for data integrity and technical compliance")
    _add_footer(slide5, 5, total_slides)

    sql_box = slide5.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.4), Inches(11.7), Inches(2.6))
    sql_box.fill.solid()
    sql_box.fill.fore_color.rgb = RGBColor(30, 41, 59)
    sql_box.line.color.rgb = RGBColor(51, 65, 85)
    tf_sql = sql_box.text_frame
    tf_sql.word_wrap = True
    p = tf_sql.paragraphs[0]
    p.text = "-- Executed SQLite Query"
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = RGBColor(148, 163, 184)
    p_sql = tf_sql.add_paragraph()
    p_sql.text = generated_sql if generated_sql else "-- No SQL generated"
    p_sql.font.size = Pt(12)
    p_sql.font.color.rgb = RGBColor(56, 189, 248)
    p_sql.space_before = Pt(6)

    exp_box = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.2), Inches(11.7), Inches(2.5))
    exp_box.fill.solid()
    exp_box.fill.fore_color.rgb = CARD_BG
    exp_box.line.color.rgb = RGBColor(226, 232, 240)
    tf_exp = exp_box.text_frame
    tf_exp.word_wrap = True
    p = tf_exp.paragraphs[0]
    p.text = "💡 Plain-English Query Logic Explanation"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = BLUE_ACCENT
    p_exp = tf_exp.add_paragraph()
    clean_exp = (sql_explanation or "").replace("#", "").replace("*", "")
    p_exp.text = clean_exp[:600] + ("..." if len(clean_exp) > 600 else "") if clean_exp else "Standard aggregation query executed."
    p_exp.font.size = Pt(11)
    p_exp.font.color.rgb = TEXT_DARK
    p_exp.space_before = Pt(6)

    # ==========================================================================
    # SLIDE 6 (Optional): Top Query Results Table
    # ==========================================================================
    if df is not None and not df.empty:
        slide6 = prs.slides.add_slide(blank_layout)
        _add_slide_header(slide6, "Query Results Tabular Preview", "Top records extracted from database")
        _add_footer(slide6, 6, total_slides)

        preview_df = df.head(8)
        num_rows = len(preview_df) + 1
        num_cols = min(len(preview_df.columns), 7)
        cols_to_render = list(preview_df.columns)[:num_cols]

        table_shape = slide6.shapes.add_table(num_rows, num_cols, Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.0))
        table = table_shape.table

        for col_idx, col_name in enumerate(cols_to_render):
            cell = table.cell(0, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY_PRIMARY
            cell.text = str(col_name)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)
                p.font.bold = True
                p.font.color.rgb = WHITE

        for row_idx, (_, row) in enumerate(preview_df.iterrows()):
            for col_idx, col_name in enumerate(cols_to_render):
                cell = table.cell(row_idx + 1, col_idx)
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE if row_idx % 2 == 0 else RGBColor(248, 250, 252)
                val = row[col_name]
                cell.text = f"{val:,.2f}" if isinstance(val, (int, float)) and not isinstance(val, bool) else str(val)
                for p in cell.text_frame.paragraphs:
                    p.font.size = Pt(10)
                    p.font.color.rgb = TEXT_DARK

    # ==========================================================================
    # Save Presentation to In-Memory Stream
    # ==========================================================================
    output_stream = io.BytesIO()
    prs.save(output_stream)
    output_stream.seek(0)
    return output_stream.getvalue()
