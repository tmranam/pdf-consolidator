import io
import math
import os
import zipfile
import pandas as pd
from pypdf import PdfReader, PdfWriter, PageObject, Transformation
from pypdf.generic import RectangleObject
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
import streamlit as st

# Set page layout once at the top
st.set_page_config(
    page_title="PDF Toolsuite Dashboard", page_icon="🛠️", layout="wide"
)

# Global Font Size Override CSS Injection
st.markdown(
    """
    <style>
    [data-testid="stWidgetLabel"] p { font-size: 1.1rem !important; }
    input, textarea { font-size: 1.1rem !important; }
    [data-testid="stSelectbox"] div[data-baseweb="select"] * { font-size: 1.1rem !important; }
    [data-testid="stRadio"] label p, [data-testid="stCheckbox"] label p { font-size: 1.1rem !important; }
    [data-testid="stCaptionContainer"] p { font-size: 1.0rem !important; }
    h4 { font-size: 1.3rem !important; }
    .stButton button, [data-testid="stButton"] button,
    .stDownloadButton button, [data-testid="stDownloadButton"] button {
        font-size: 1.2rem !important;
        padding: 0.7rem 1.2rem !important;
        height: auto !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize navigation state
if "current_page" not in st.session_state:
    st.session_state.current_page = "batch_consolidator"
if "batches_subtab" not in st.session_state:
    st.session_state.batches_subtab = "batch_headers"

# --- MAIN NAVIGATION MENU ---
with st.sidebar:
    st.title("🛠️ Main Menu")
    
    page_options = {
        "📦 PDF Store Batch Consolidator": "batch_consolidator",
        "📐 PDF Impose Layout Engine": "impose",
        "📄 Duplicate Pages Tool": "duplicate",
        "🏷️ Batches & Labels Dashboard": "batches_and_labels",
        "⚙️ General Settings": "general"
    }
    
    display_names = list(page_options.keys())
    internal_keys = list(page_options.values())
    default_index = internal_keys.index(st.session_state.current_page) if st.session_state.current_page in internal_keys else 0
    
    selected_display = st.radio(
        "Navigate to:",
        options=display_names,
        index=default_index
    )
    
    st.session_state.current_page = page_options[selected_display]
# -------------------------------------
    
def create_header_pdf(metadata_dict, total_pages, page_width=612, page_height=792):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(float(page_width), float(page_height)))
    center_x = float(page_width) / 2.0
    center_y = float(page_height) / 2.0
    total_lines = len(metadata_dict) + 1
    line_height = 30
    start_y = center_y + ((total_lines * line_height) / 2.0)
    current_y = start_y

    for idx, (label, val) in enumerate(metadata_dict.items()):
        val_str = "" if pd.isna(val) else str(val)
        if idx == 0:
            can.setFont("Helvetica-Bold", 22)
            can.drawCentredString(center_x, current_y, f"{val_str}")
        else:
            can.setFont("Helvetica", 13)
            can.drawCentredString(center_x, current_y, f"{label}: {val_str}")
        current_y -= line_height

    can.setFont("Helvetica-Bold", 14)
    can.drawCentredString(center_x, current_y, f"Total Pages: {total_pages}")
    can.save()
    packet.seek(0)
    return PdfReader(packet)

def create_batch_header_file(job_no, description, total_batches, auto_number=True, side_margin=50):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    page_width, page_height = letter
    center_x = page_width / 2.0
    desc_style = ParagraphStyle("DescStyle", fontName="Helvetica-Bold", fontSize=32, leading=38, alignment=1, textColor=HexColor("#000000"))

    for i in range(1, total_batches + 1):
        can.setFont("Helvetica-Bold", 70)
        can.drawCentredString(center_x, page_height - 110, str(job_no))
        max_desc_width = page_width - (2 * side_margin)
        desc_para = Paragraph(str(description), desc_style)
        para_w, para_h = desc_para.wrap(max_desc_width, page_height)
        desc_para.drawOn(can, side_margin, page_height - 140 - para_h)

        can.setFont("Helvetica-Bold", 90)
        can.drawCentredString(center_x, page_height - 290, str(i))
        can.setFont("Helvetica-Bold", 50)
        can.drawCentredString(center_x, page_height - 370, "OF")
        can.setFont("Helvetica-Bold", 90)
        total_str = str(total_batches) if auto_number else "______"
        can.drawCentredString(center_x, page_height - 470, total_str)
        can.showPage()

    can.save()
    packet.seek(0)
    return packet

def create_outside_work_label_file(supplier, job_no, client, job_title, qty_this_pallet, total_pallets, auto_number_pallets=True):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    page_width, page_height = A4
    cyan_bg, dark_frame, text_dark = HexColor("#00AEEF"), HexColor("#1A1A1A"), HexColor("#1A1A1A")
    top_clearance_pt = 80 * 2.83465

    for i in range(1, total_pallets + 1):
        can.setFillColor(cyan_bg)
        can.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        margin_x, margin_bottom, margin_top, corner_cut = 35, 35, top_clearance_pt, 25
        frame_top_y = page_height - margin_top

        path = can.beginPath()
        path.moveTo(margin_x + corner_cut, frame_top_y)
        path.lineTo(page_width - margin_x - corner_cut, frame_top_y)
        path.lineTo(page_width - margin_x, frame_top_y - corner_cut)
        path.lineTo(page_width - margin_x, margin_bottom)
        path.lineTo(margin_x, margin_bottom)
        path.lineTo(margin_x, frame_top_y - corner_cut)
        path.close()

        can.setStrokeColor(dark_frame)
        can.setLineWidth(5)
        can.drawPath(path, fill=0, stroke=1)

        can.setFillColor(text_dark)
        can.setFont("Helvetica-Bold", 11)
        can.drawString(margin_x + 20, frame_top_y - 40, "From:")
        can.setFont("Helvetica-Bold", 14)
        can.drawString(margin_x + 20, frame_top_y - 58, "IVE Print")
        can.setFont("Helvetica", 11)
        can.drawString(margin_x + 20, frame_top_y - 74, "24-36 Beyer Rd, Braeside")
        can.drawString(margin_x + 20, frame_top_y - 88, "Victoria 3195")
        can.setFont("Helvetica-Bold", 46)
        can.drawRightString(page_width - margin_x - 25, frame_top_y - 70, "ive")

        banner_y, banner_h = frame_top_y - 260, 160
        can.setFillColor(dark_frame)
        can.rect(margin_x, banner_y, page_width - (margin_x * 2), banner_h, fill=1, stroke=0)
        can.setFillColor(HexColor("#FFFFFF"))
        can.setFont("Helvetica-Bold", 80)
        can.drawCentredString(page_width / 2.0, banner_y + 92, "OUTSIDE")
        can.drawCentredString(page_width / 2.0, banner_y + 32, "WORK")

        fields = [("Supplier:", supplier), ("Job No:", job_no), ("Client:", client), ("Job Title:", job_title), ("Qty this pallet:", qty_this_pallet)]
        y_start, line_gap = banner_y - 38, 36
        can.setFillColor(text_dark)

        for idx, (label, val) in enumerate(fields):
            curr_y = y_start - (idx * line_gap)
            can.setFont("Helvetica", 15)
            can.drawString(margin_x + 20, curr_y, label)
            dots_x_start = margin_x + 25 + can.stringWidth(label, "Helvetica", 15)

            if val:
                can.setFont("Helvetica-Bold", 18)
                can.drawString(dots_x_start + 10, curr_y, str(val))

            can.setStrokeColor(dark_frame)
            can.setLineWidth(1)
            can.setDash([1, 3], 0)
            can.line(dots_x_start, curr_y - 2, page_width - margin_x - 20, curr_y - 2)

        y_pallet = y_start - (len(fields) * line_gap)
        can.setFont("Helvetica", 15)
        can.drawString(margin_x + 20, y_pallet, "Pallet:")
        can.setFont("Helvetica-Bold", 18)
        can.drawString(margin_x + 90, y_pallet, str(i))
        can.setFont("Helvetica", 15)
        can.drawString(margin_x + 145, y_pallet, "of:")
        total_str = str(total_pallets) if auto_number_pallets else ""
        if total_str:
            can.setFont("Helvetica-Bold", 18)
            can.drawString(margin_x + 180, y_pallet, total_str)

        can.setStrokeColor(dark_frame)
        can.setLineWidth(1)
        can.setDash([1, 3], 0)
        can.line(margin_x + 20, y_pallet - 2, page_width - margin_x - 20, y_pallet - 2)
        can.setDash([], 0)
        can.showPage()

    can.save()
    packet.seek(0)
    return packet

def create_labels_pdf(media_w_pt, media_h_pt, rows, cols, label_w_pt, label_h_pt, gutter_x_pt, gutter_y_pt, margin_x_pt, margin_y_pt, lines_config, total_labels, include_numbering, start_num=1, prefix_num="", background_pdf_bytes=None, breaks_configs=None):
    # 1. Generate text overlay PDF
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(media_w_pt, media_h_pt))
    
    if not breaks_configs:
        breaks_configs = [{"count": total_labels, "include_numbering": include_numbering, "start_num": start_num, "prefix_num": prefix_num, "lines": lines_config, "total_labels_global": total_labels}]
    
    all_computed_labels = []
    for batch in breaks_configs:
        b_count = batch.get("count", 0)
        b_lines = batch.get("lines", [])
        b_inc_num = batch.get("include_numbering", True)
        b_start = batch.get("start_num", 1)
        b_prefix = batch.get("prefix_num", "")
        
        # Calculate total target labels for "X of Y" string
        b_global_total = batch.get("total_labels_global", b_count)
        total_end_val = (b_start - 1) + b_global_total
        
        for i in range(b_count):
            curr_val = b_start + i
            # Format as: [Prefix][Current] of [Total]
            seq_str = f"{b_prefix}{curr_val} of {total_end_val}"
            all_computed_labels.append({
                "lines": list(b_lines), 
                "show_num": b_inc_num, 
                "seq_str": seq_str
            })
            
    total_to_render = len(all_computed_labels)
    label_ptr = 0
    
    while label_ptr < total_to_render:
        for r in range(rows):
            for c in range(cols):
                if label_ptr >= total_to_render:
                    break
                
                x_left = margin_x_pt + c * (label_w_pt + gutter_x_pt)
                y_top = media_h_pt - margin_y_pt - r * (label_h_pt + gutter_y_pt)
                center_x = x_left + (label_w_pt / 2.0)
                
                current_label_data = all_computed_labels[label_ptr]
                active_lines = list(current_label_data["lines"])
                
                if current_label_data["show_num"]:
                    active_lines.append({"text": current_label_data['seq_str'], "font_size": 10, "bold": True})
                
                total_content_lines = len(active_lines)
                if total_content_lines > 0:
                    line_height = label_h_pt / (total_content_lines + 1)
                    current_y = y_top - line_height
                    for line in active_lines:
                        can.setFont("Helvetica-Bold" if line.get("bold", False) else "Helvetica", line.get("font_size", 12))
                        can.drawCentredString(center_x, current_y, str(line.get("text", "")))
                        current_y -= line_height
                label_ptr += 1
        can.showPage()
        
    can.save()
    packet.seek(0)
    text_pdf_reader = PdfReader(packet)
    
    # 2. Merge with background PDF if provided, using pypdf
    writer = PdfWriter()
    bg_pages = []
    if background_pdf_bytes:
        bg_reader = PdfReader(io.BytesIO(background_pdf_bytes))
        bg_pages = bg_reader.pages
    
    for page_idx, text_page in enumerate(text_pdf_reader.pages):
        if bg_pages:
            # Loop background pages if text spans multiple pages
            bg_page = bg_pages[page_idx % len(bg_pages)]
            # Merge text page on top of background page
            bg_page.merge_page(text_page)
            writer.add_page(bg_page)
        else:
            writer.add_page(text_page)
            
    final_output = io.BytesIO()
    writer.write(final_output)
    final_output.seek(0)
    return final_output

def compute_grid_positions(media_w, media_h, trim_w, trim_h, gutter_x, gutter_y, margin_left, margin_right, margin_top, margin_bottom, cols, rows):
    avail_w = media_w - margin_left - margin_right
    avail_h = media_h - margin_top - margin_bottom
    step_x = trim_w + gutter_x
    step_y = trim_h + gutter_y
    grid_w = (cols * trim_w) + ((cols - 1) * gutter_x)
    grid_h = (rows * trim_h) + ((rows - 1) * gutter_y)
    center_offset_x = margin_left + (avail_w - grid_w) / 2.0
    center_offset_y = margin_top + (avail_h - grid_h) / 2.0

    positions = []
    for r in range(rows):
        for c in range(cols):
            positions.append({'row': r, 'col': c, 'x': center_offset_x + (c * step_x), 'y': media_h - center_offset_y - (r * step_y) - trim_h})
    return {'positions': positions, 'grid_w': grid_w, 'grid_h': grid_h, 'avail_w': avail_w, 'avail_h': avail_h, 'center_offset_x': center_offset_x, 'center_offset_y': center_offset_y}

def execute_pdf_imposition(input_bytes, config):
    MM_TO_PT = 72.0 / 25.4
    media_w = float(config.get('media_w', 320.0)) * MM_TO_PT
    media_h = float(config.get('media_h', 450.0)) * MM_TO_PT
    trim_w = float(config.get('trim_w', 250.0)) * MM_TO_PT
    trim_h = float(config.get('trim_h', 145.0)) * MM_TO_PT
    bleed = float(config.get('bleed', 0.0)) * MM_TO_PT
    gutter_x = float(config.get('gutter_x', 0.0)) * MM_TO_PT
    gutter_y = float(config.get('gutter_y', 0.0)) * MM_TO_PT

    margins = config.get('margins', {}) if isinstance(config.get('margins'), dict) else {}
    margin_left = float(margins.get('left', 0.0)) * MM_TO_PT
    margin_right = float(margins.get('right', 0.0)) * MM_TO_PT
    margin_top = float(margins.get('top', 0.0)) * MM_TO_PT
    margin_bottom = float(margins.get('bottom', 0.0)) * MM_TO_PT

    page_id_enabled = config.get('page_id_enabled', False)
    page_id_text = config.get('page_id_text', "")
    page_id_font_size = float(config.get('page_id_font_size', 8.0))
    page_id_margin = float(config.get('page_id_margin', 5.0)) * MM_TO_PT
    page_id_position = config.get('page_id_position', "Bottom")
    page_id_sides = config.get('page_id_sides', "Both Sides")

    reader = PdfReader(io.BytesIO(input_bytes))
    layout_mode = config.get('layout_mode', "Repeat / Step & Repeat")
    is_mix_mode = "Mix" in layout_mode
    mix_sections = int(config.get('mix_sections', 1)) if is_mix_mode else None

    if "Cut and Stack" in layout_mode or is_mix_mode:
        page_pool = list(reader.pages)
    else:
        page_pool = []
        repeat_count = int(config.get('repeat_per_page', 1))
        for original_page in reader.pages:
            for _ in range(repeat_count):
                page_pool.append(original_page)

    total_input_pages = len(page_pool)
    if total_input_pages == 0:
        raise ValueError("Uploaded PDF has no printable pages.")

    cols = int(config.get('cols', 1))
    rows = int(config.get('rows', 1))

    geo = compute_grid_positions(media_w, media_h, trim_w, trim_h, gutter_x, gutter_y, margin_left, margin_right, margin_top, margin_bottom, cols, rows)
    avail_w, avail_h, grid_w, grid_h = geo['avail_w'], geo['avail_h'], geo['grid_w'], geo['grid_h']
    center_offset_x, center_offset_y = geo['center_offset_x'], geo['center_offset_y']
    ups_per_page = cols * rows

    if grid_w > avail_w + 0.01 or grid_h > avail_h + 0.01:
        raise ValueError(f"Grid setup does not fit sheet parameters.")

    center_offset_x_right = margin_right + (avail_w - grid_w) / 2.0
    stack_depth = math.ceil(total_input_pages / mix_sections) if is_mix_mode else math.ceil(total_input_pages / ups_per_page)

    is_duplex = config.get('duplex', False)
    if is_duplex and (stack_depth % 2 != 0):
        stack_depth += 1

    total_sheets = stack_depth
    total_physical_sheets = (total_sheets // 2) if is_duplex else total_sheets
    fit_to_size = config.get('fit_to_size', True)
    mag_factor = float(config.get('magnification_pct', 100.0)) / 100.0
    last_computed_scale = 1.0

    is_booklet = "Booklet" in layout_mode
    b_copies = int(config.get('booklet_copies', 1))
    creep_per_sheet_pt = float(config.get('booklet_creep', 0.0)) * (72.0 / 25.4)

    if is_booklet:
        booklet_pool = list(reader.pages)
        while len(booklet_pool) % 4 != 0:
            booklet_pool.append(PageObject.create_blank_page(width=media_w, height=media_h))
        total_input_pages = len(booklet_pool)
        total_distinct_signature_leaves = total_input_pages // 4
        press_sheets_needed = math.ceil(total_distinct_signature_leaves / rows) if "Cut and Stack" in layout_mode else total_distinct_signature_leaves
        total_sheets = press_sheets_needed * 2
        total_physical_sheets = press_sheets_needed
    writer = PdfWriter()
    total_stack_layers = math.ceil(total_input_pages / mix_sections) if is_mix_mode else math.ceil(total_input_pages / ups_per_page)
    if is_duplex and (total_stack_layers % 2 != 0):
        total_stack_layers += 1

    for sheet_idx in range(total_sheets):
        sheet = PageObject.create_blank_page(width=media_w, height=media_h)
        is_back_page = (sheet_idx % 2 == 1)
        press_layer_idx = sheet_idx // 2
        physical_sheet_number = press_layer_idx + 1
        current_stack_layer = press_layer_idx if is_duplex else sheet_idx

        mark_packet = io.BytesIO()
        mark_can = canvas.Canvas(mark_packet, pagesize=(media_w, media_h))
        mark_can.setStrokeColorCMYK(0, 0, 0, 1)
        mark_can.setFillColorCMYK(0, 0, 0, 1)
        mark_can.setLineWidth(0.5)
        mark_style = config.get('trim_marks_style', "None")

        for r in range(rows):
            for c in range(cols):
                if is_booklet:
                    booklet_instance_idx = c // 2
                    if booklet_instance_idx >= b_copies:
                        continue
                    is_slot_right_side = (c % 2 == 1)
                    target_booklet_sheet = (press_layer_idx * rows) + r if "Cut and Stack" in layout_mode else press_layer_idx
                    if target_booklet_sheet >= total_distinct_signature_leaves:
                        continue
                    low_page = (target_booklet_sheet * 2) + 1
                    high_page = total_input_pages - (target_booklet_sheet * 2)

                    if not is_back_page:
                        input_page_idx = (high_page - 1) if not is_slot_right_side else (low_page - 1)
                    else:
                        input_page_idx = ((low_page + 1) - 1) if not is_slot_right_side else ((high_page - 1) - 1)

                    if input_page_idx >= len(booklet_pool):
                        continue
                    original_page = booklet_pool[input_page_idx]
                else:
                    if "Cut and Stack" in layout_mode:
                        if is_duplex:
                            if is_back_page:
                                grid_position_idx = (r * cols) + (cols - 1 - c)
                                input_page_idx = (grid_position_idx * (total_stack_layers * 2)) + (current_stack_layer * 2) + 1
                            else:
                                grid_position_idx = (r * cols) + c
                                input_page_idx = (grid_position_idx * (total_stack_layers * 2)) + (current_stack_layer * 2)
                        else:
                            input_page_idx = (((r * cols) + c) * total_stack_layers) + current_stack_layer
                    elif is_mix_mode:
                        group_id = ((cols - 1 - c) if is_back_page else c) % mix_sections
                        input_page_idx = ((group_id * (total_stack_layers * 2)) + (current_stack_layer * 2) + (1 if is_back_page else 0)) if is_duplex else (group_id * total_stack_layers) + current_stack_layer
                    else:
                        input_page_idx = (sheet_idx * ups_per_page) + (r * cols + c)

                    if input_page_idx >= total_input_pages:
                        continue
                    original_page = page_pool[input_page_idx]

                isolate_writer = PdfWriter()
                isolate_writer.add_page(original_page)
                isolate_buf = io.BytesIO()
                isolate_writer.write(isolate_buf)
                isolate_buf.seek(0)
                input_page = PdfReader(isolate_buf).pages[0]

                orig_ll_x = float(input_page.mediabox.lower_left[0])
                orig_ll_y = float(input_page.mediabox.lower_left[1])
                orig_w = float(input_page.mediabox.width)
                orig_h = float(input_page.mediabox.height)

                if cols > 1:
                    max_safe_bleed_x = min(bleed, gutter_x / 2.0) if gutter_x > 0 else 0.0
                else:
                    max_safe_bleed_x = bleed

                if rows > 1:
                    max_safe_bleed_y = min(bleed, gutter_y / 2.0) if gutter_y > 0 else 0.0
                else:
                    max_safe_bleed_y = bleed

                crop_w_pt = trim_w + (2 * max_safe_bleed_x)
                crop_h_pt = trim_h + (2 * max_safe_bleed_y)

                crop_ll_x = orig_ll_x + ((orig_w - crop_w_pt) / 2.0)
                crop_ll_y = orig_ll_y + ((orig_h - crop_h_pt) / 2.0)
                crop_rect = RectangleObject([crop_ll_x, crop_ll_y, crop_ll_x + crop_w_pt, crop_ll_y + crop_h_pt])
                input_page.mediabox = crop_rect
                input_page.cropbox = crop_rect

                if is_back_page:
                    x_pos = media_w - center_offset_x_right - ((cols - 1 - c) * (trim_w + gutter_x)) - trim_w
                else:
                    x_pos = center_offset_x + (c * (trim_w + gutter_x))
                y_pos = media_h - center_offset_y - (r * (trim_h + gutter_y)) - trim_h

                scale = min(trim_w / trim_w, trim_h / trim_h) if fit_to_size else 1.0 * mag_factor
                last_computed_scale = scale
                tx = x_pos - (max_safe_bleed_x * scale) - (crop_ll_x * scale)
                ty = y_pos - (max_safe_bleed_y * scale) - (crop_ll_y * scale)

                if is_booklet and creep_per_sheet_pt > 0:
                    current_creep_offset = target_booklet_sheet * creep_per_sheet_pt * scale
                    tx += (-current_creep_offset if is_slot_right_side else current_creep_offset)

                sheet.merge_transformed_page(input_page, Transformation().scale(scale, scale).translate(tx, ty), expand=False)

                if mark_style != "None":
                    mark_len = 12.0
                    offset = max(3.0 * MM_TO_PT, max_safe_bleed_x, max_safe_bleed_y)
                    x1, x2 = x_pos, x_pos + trim_w
                    y1, y2 = y_pos, y_pos + trim_h

                    is_left_edge = (c == 0) if not is_back_page else (c == cols - 1)
                    is_right_edge = (c == cols - 1) if not is_back_page else (c == 0)
                    is_top_edge, is_bottom_edge = (r == 0), (r == rows - 1)

                    s_left = mark_len if is_left_edge else max(1.0, (gutter_x / 2.0) - offset)
                    s_right = mark_len if is_right_edge else max(1.0, (gutter_x / 2.0) - offset)
                    s_top = mark_len if is_top_edge else max(1.0, (gutter_y / 2.0) - offset)
                    s_bottom = mark_len if is_bottom_edge else max(1.0, (gutter_y / 2.0) - offset)

                    if mark_style == "All Individual Items" or (is_left_edge or is_top_edge):
                        if s_top > 0: mark_can.line(x1, y2 + offset, x1, y2 + offset + s_top)
                        if s_left > 0: mark_can.line(x1 - offset, y2, x1 - offset - s_left, y2)
                    if mark_style == "All Individual Items" or (is_right_edge or is_top_edge):
                        if s_top > 0: mark_can.line(x2, y2 + offset, x2, y2 + offset + s_top)
                        if s_right > 0: mark_can.line(x2 + offset, y2, x2 + offset + s_right, y2)
                    if mark_style == "All Individual Items" or (is_left_edge or is_bottom_edge):
                        if s_bottom > 0: mark_can.line(x1, y1 - offset, x1, y1 - offset - s_bottom)
                        if s_left > 0: mark_can.line(x1 - offset, y1, x1 - offset - s_left, y1)
                    if mark_style == "All Individual Items" or (is_right_edge or is_bottom_edge):
                        if s_bottom > 0: mark_can.line(x2, y1 - offset, x2, y1 - offset - s_bottom)
                        if s_right > 0: mark_can.line(x2 + offset, y1, x2 + offset + s_right, y1)
        should_draw_id = page_id_enabled and page_id_text.strip() != ""
        if should_draw_id and is_back_page and page_id_sides == "Front Only":
            should_draw_id = False

        if should_draw_id:
            id_string = f"{page_id_text.strip()} Page {physical_sheet_number} of {total_physical_sheets}"
            mark_can.setFont("Helvetica", page_id_font_size)
            if page_id_position == "Top":
                mark_can.drawCentredString(media_w / 2.0, media_h - page_id_margin - page_id_font_size, id_string)
            elif page_id_position == "Bottom":
                mark_can.drawCentredString(media_w / 2.0, page_id_margin, id_string)
            elif page_id_position == "Left":
                mark_can.saveState()
                mark_can.translate(page_id_margin + page_id_font_size, media_h / 2.0)
                mark_can.rotate(90)
                mark_can.drawCentredString(0, 0, id_string)
                mark_can.restoreState()
            elif page_id_position == "Right":
                mark_can.saveState()
                mark_can.translate(media_w - page_id_margin - page_id_font_size, media_h / 2.0)
                mark_can.rotate(-90)
                mark_can.drawCentredString(0, 0, id_string)
                mark_can.restoreState()

        mark_can.save()
        mark_packet.seek(0)
        mark_reader = PdfReader(mark_packet)
        if len(mark_reader.pages) > 0:
            sheet.merge_page(mark_reader.pages[0], over=True, expand=False)

        box_rect = RectangleObject([0, 0, media_w, media_h])
        sheet.mediabox = box_rect
        sheet.cropbox = box_rect
        sheet.trimbox = box_rect
        sheet.bleedbox = box_rect
        writer.add_page(sheet)

    output_stream = io.BytesIO()
    writer.write(output_stream)
    return output_stream.getvalue(), ups_per_page, round(last_computed_scale * 100.0, 1)

def render_layout_preview(media_w_mm, media_h_mm, trim_w_mm, trim_h_mm, bleed_mm, gutter_x_mm, gutter_y_mm, margin_top_mm, margin_bottom_mm, margin_left_mm, margin_right_mm, cols, rows, page_id_enabled, page_id_position, page_id_text, layout_mode=None, mix_sections=None):
    geo = compute_grid_positions(media_w_mm, media_h_mm, trim_w_mm, trim_h_mm, gutter_x_mm, gutter_y_mm, margin_left_mm, margin_right_mm, margin_top_mm, margin_bottom_mm, cols, rows)
    fits = geo['grid_w'] <= geo['avail_w'] + 0.01 and geo['grid_h'] <= geo['avail_h'] + 0.01
    grid_color = "#4a90d9" if fits else "#d94a4a"
    is_mix_mode = bool(layout_mode) and ("Mix" in layout_mode) and mix_sections
    mix_palette = ["#4a90d9", "#e0a13a", "#5cb85c", "#b565d9", "#d95c8f", "#5cc9d9"]

    canvas_w, canvas_h = 480, 480
    pad = 20
    scale = min((canvas_w - 2 * pad) / media_w_mm, (canvas_h - 2 * pad) / media_h_mm) if media_w_mm > 0 and media_h_mm > 0 else 1
    offset_x, offset_y = pad, pad

    def to_svg_xy(x_mm, y_mm):
        return offset_x + x_mm * scale, offset_y + (media_h_mm - y_mm) * scale

    svg_parts = [f'<svg viewBox="0 0 {canvas_w} {canvas_h}" width="100%" height="auto" preserveAspectRatio="xMidYMid meet" xmlns="http://w3.org" style="background:#fafafa;border:1px solid #ddd; display:block; max-width:100%;">']
    sx, sy = to_svg_xy(0, media_h_mm)
    svg_parts.append(f'<rect x="{sx}" y="{sy}" width="{media_w_mm*scale}" height="{media_h_mm*scale}" fill="#f2f2f2" stroke="black" stroke-width="1.2" />')

    mx, my = to_svg_xy(margin_left_mm, media_h_mm - margin_top_mm)
    svg_parts.append(f'<rect x="{mx}" y="{my}" width="{geo["avail_w"]*scale}" height="{geo["avail_h"]*scale}" fill="none" stroke="#888888" stroke-width="0.8" stroke-dasharray="4,3" />')

    for idx, pos in enumerate(geo['positions']):
        r, c = divmod(idx, cols)
        x, y = pos['x'], pos['y']
        cell_color = mix_palette[(c % int(mix_sections)) % len(mix_palette)] if is_mix_mode and fits else grid_color
        tx, ty = to_svg_xy(x, y + trim_h_mm)
        svg_parts.append(f'<rect x="{tx}" y="{ty}" width="{trim_w_mm*scale}" height="{trim_h_mm*scale}" fill="{cell_color}" fill-opacity="0.35" stroke="{cell_color}" stroke-width="1.0" />')
        if bleed_mm > 0:
            bx, by = to_svg_xy(x - bleed_mm, y + trim_h_mm + bleed_mm)
            svg_parts.append(f'<rect x="{bx}" y="{by}" width="{(trim_w_mm+2*bleed_mm)*scale}" height="{(trim_h_mm+2*bleed_mm)*scale}" fill="none" stroke="red" stroke-width="0.6" stroke-dasharray="2,2" />')

    if page_id_enabled and page_id_text.strip() != "":
        label = f'{page_id_text.strip()} Page 1 of N'
        cx, _ = to_svg_xy(media_w_mm / 2.0, 0)
        if page_id_position == "Top":
            _, ty2 = to_svg_xy(0, media_h_mm - 4)
            svg_parts.append(f'<text x="{cx}" y="{ty2}" font-size="11" fill="green" text-anchor="middle">{label}</text>')
        elif page_id_position == "Bottom":
            _, by2 = to_svg_xy(0, 4)
            svg_parts.append(f'<text x="{cx}" y="{by2}" font-size="11" fill="green" text-anchor="middle">{label}</text>')
        elif page_id_position == "Left":
            lx, ly = to_svg_xy(4, media_h_mm / 2.0)
            svg_parts.append(f'<text x="{lx}" y="{ly}" font-size="11" fill="green" text-anchor="middle" transform="rotate(-90 {lx} {ly})">{label}</text>')
        elif page_id_position == "Right":
            rx, ry = to_svg_xy(media_w_mm - 4, media_h_mm / 2.0)
            svg_parts.append(f'<text x="{rx}" y="{ry}" font-size="11" fill="green" text-anchor="middle" transform="rotate(90 {rx} {ry})">{label}</text>')

    title = f'{cols} x {rows} = {cols*rows}-up on {media_w_mm:.0f}x{media_h_mm:.0f}mm'
    if not fits: title += "  \u26A0 DOES NOT FIT"
    svg_parts.append(f'<text x="{canvas_w/2}" y="14" font-size="12" fill="#333" text-anchor="middle">{title}</text></svg>')
    return "".join(svg_parts)

if st.session_state.current_page == "impose":
    st.subheader("📐 PDF Impose Layout Engine")
    st.write("Upload source materials to impose, scale, and arrange pages for high-volume production presses.")

    if "system_auto_scale_feedback" not in st.session_state:
        st.session_state.system_auto_scale_feedback = 100.0

    uploaded_impose_pdf = st.file_uploader("Upload Target PDF File to Impose", type=["pdf"], key="impose_file_uploader")
    st.divider()

    main_preview_col, main_settings_col = st.columns([1, 2])

    with main_settings_col:
        st.markdown("#### 🛠️ Press Signature Configurations")
        col_imp1, col_imp2 = st.columns(2)

        with col_imp1:
            st.markdown("**Output Media Sheet Footprint (mm):**")
            media_w_mm = st.number_input("Custom Sheet Width (mm):", min_value=50.0, max_value=2000.0, value=210.0, step=1.0)
            media_h_mm = st.number_input("Custom Sheet Height (mm):", min_value=50.0, max_value=2000.0, value=297.0, step=1.0)
            st.write("---")
            st.markdown("**Grid Layout (Columns x Rows):**")
            grid_col1, grid_col2 = st.columns(2)
            with grid_col1: cols_input = st.number_input("Columns:", min_value=1, max_value=100, value=2, step=1, key="cols_input_widget")
            with grid_col2: rows_input = st.number_input("Rows:", min_value=1, max_value=100, value=4, step=1, key="rows_input_widget")

            total_ups_preview = int(cols_input) * int(rows_input)
            st.caption(f"➡️ This will place **{total_ups_preview}-up** per sheet.")

            mix_sections_value, booklet_sub_layout, booklet_copies, booklet_creep_mm = 1, "Cut and Stack", 1, 0.0
            layout_choice = st.radio("Step Sequencing Route Pattern:", ["Repeat / Step & Repeat", "Cut and Stack", "Mix (Sections + Copies)", "Booklet"], horizontal=False)
            print_style = st.radio("Output Surface Type:", ["Simplex", "Duplex"], index=1 if layout_choice == "Booklet" else 0, disabled=(layout_choice == "Booklet"), horizontal=True)

            if layout_choice == "Mix (Sections + Copies)":
                mix_copies_value = st.number_input("How many copies do you want?:", min_value=1, max_value=max(1, total_ups_preview), value=min(20, max(1, total_ups_preview)), step=1)
                mix_sections_value = min(max(1, total_ups_preview // int(mix_copies_value)), int(cols_input))
            elif layout_choice == "Booklet":
                st.markdown("#### 📖 Booklet Structural Sub-Configurations")
                booklet_sub_layout = st.radio("Multi-Up Layout Matrix Rule:", ["Cut and Stack", "Repeat / Step & Repeat"])
                booklet_copies = st.number_input("Booklet Copies on One Sheet:", min_value=1, max_value=max(1, total_ups_preview // 2), value=1, step=1)
                booklet_creep_mm = st.number_input("Spine Creep Offset Shift Value (mm):", min_value=0.0, max_value=10.0, value=0.0, step=0.05)

        with col_imp2:
            trim_w = st.number_input("Finished Trim Width (mm):", min_value=5.0, max_value=media_w_mm, value=90.0, step=0.5)
            trim_h = st.number_input("Finished Trim Height (mm):", min_value=5.0, max_value=media_h_mm, value=55.0, step=0.5)
            bleed_w = st.number_input("Bleed Envelope Margin (mm):", min_value=0.0, max_value=25.0, value=2.0, step=0.5)
            gut_x = st.number_input("Horizontal Gutter Gap (mm):", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            gut_y = st.number_input("Vertical Gutter Gap (mm):", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            st.write("---")
            fit_to_size_option = st.checkbox("Auto-Fit Content to Selected Trim Box?", value=True)
            magnification_pct = st.number_input("Artwork Magnification Scale (%):", min_value=10.0, max_value=200.0, value=float(st.session_state.system_auto_scale_feedback) if fit_to_size_option else 98.0, disabled=fit_to_size_option)
            trim_style_selection = st.selectbox("Select Trim Marks Option style:", ["Outer Perimeter Only", "All Individual Items", "None"], index=0)

        st.write("---")
        st.markdown("**Sheet Margins (mm):**")
        margin_col1, margin_col2, margin_col3, margin_col4 = st.columns(4)
        with margin_col1: margin_top_mm = st.number_input("Top:", min_value=0.0, max_value=200.0, value=25.0, step=1.0)
        with margin_col2: margin_bottom_mm = st.number_input("Bottom:", min_value=0.0, max_value=200.0, value=25.0, step=1.0)
        with margin_col3: margin_left_mm = st.number_input("Left:", min_value=0.0, max_value=200.0, value=25.0, step=1.0)
        with margin_col4: margin_right_mm = st.number_input("Right:", min_value=0.0, max_value=200.0, value=25.0, step=1.0)

        st.write("---")
        page_id_enabled = st.checkbox("Enable Page Identifier?", value=False)
        if page_id_enabled:
            page_id_text = st.text_input("Custom Label Text:", value="File One")
            id_col1, id_col2, id_col3 = st.columns(3)
            with id_col1: page_id_font_size = st.number_input("Font Size (pt):", min_value=4.0, max_value=72.0, value=8.0, step=0.5)
            with id_col2: page_id_margin = st.number_input("Margin from Edge (mm):", min_value=0.0, max_value=100.0, value=5.0, step=0.5)
            with id_col3: page_id_position = st.selectbox("Position on Sheet:", ["Top", "Bottom", "Left", "Right"], index=1)
            page_id_sides = st.radio("Apply Identifier To:", ["Both Sides", "Front Only"], horizontal=True)
        else:
            page_id_text, page_id_font_size, page_id_margin, page_id_position, page_id_sides = "", 8.0, 5.0, "Bottom", "Both Sides"

    with main_preview_col:
        st.markdown("**Live Layout Preview:**")
        preview_svg = render_layout_preview(media_w_mm, media_h_mm, trim_w, trim_h, bleed_w, gut_x, gut_y, margin_top_mm, margin_bottom_mm, margin_left_mm, margin_right_mm, int(cols_input), int(rows_input), page_id_enabled, page_id_position, page_id_text, layout_mode=layout_choice, mix_sections=int(mix_sections_value) if layout_choice == "Mix (Sections + Copies)" else None)
        st.markdown(f'<div style="width:100%; max-width:100%; overflow:hidden;">{preview_svg}</div>', unsafe_allow_html=True)

    st.divider()
    if st.button("Run Sheet Imposition Processing", type="primary", use_container_width=True):
        if not uploaded_impose_pdf: st.error("⚠️ Active source PDF file stream data must be staged.")
        else:
            with st.spinner("Processing..."):
                try:
                    runtime_layout_string = f"Booklet - {booklet_sub_layout}" if layout_choice == "Booklet" else layout_choice
                    config_pack = {'media_w': media_w_mm, 'media_h': media_h_mm, 'trim_w': trim_w, 'trim_h': trim_h, 'bleed': bleed_w, 'gutter_x': gut_x, 'gutter_y': gut_y, 'cols': int(cols_input), 'rows': int(rows_input), 'margins': {'top': margin_top_mm, 'bottom': margin_bottom_mm, 'left': margin_left_mm, 'right': margin_right_mm}, 'layout_mode': runtime_layout_string, 'mix_sections': int(mix_sections_value), 'duplex': (print_style == "Duplex"), 'repeat_per_page': int(cols_input) * int(rows_input), 'trim_marks_style': trim_style_selection, 'fit_to_size': fit_to_size_option, 'magnification_pct': float(magnification_pct), 'page_id_enabled': page_id_enabled, 'page_id_text': page_id_text, 'page_id_font_size': float(page_id_font_size), 'page_id_margin': float(page_id_margin), 'page_id_position': page_id_position, 'page_id_sides': page_id_sides, 'booklet_creep': float(booklet_creep_mm)}
                    compiled_output_pdf, total_calculated_ups, computed_percentage = execute_pdf_imposition(uploaded_impose_pdf.read(), config_pack)
                    st.session_state.system_auto_scale_feedback = computed_percentage
                    st.success(f"🎉 Success! ({total_calculated_ups}-up)")
                    st.download_button(label="⬇️ Download Output", data=compiled_output_pdf, file_name=f"{os.path.splitext(uploaded_impose_pdf.name)[0]}_Imposed_{total_calculated_ups}Up.pdf", mime="application/pdf", use_container_width=True)
                except Exception as ex_err: st.error(f"Error: {str(ex_err)}")

elif st.session_state.current_page == "duplicate":
    st.subheader("📄 Duplicate Pages Tool")
    col_a, col_b = st.columns(2)
    with col_a: uploaded_pdf = st.file_uploader("1. Upload PDF File", type=["pdf"])
    with col_b: uploaded_excel = st.file_uploader("2. Upload Excel Control Sheet", type=["xlsx", "xls"], key="dup_excel")
    mode = st.radio("3. Select Printing Mode:", ["Simplex", "Duplex"], horizontal=True)

    if uploaded_pdf and uploaded_excel:
        df_dup = pd.read_excel(uploaded_excel)
        qty_col = st.selectbox("Select Quantity Column:", df_dup.columns, index=len(df_dup.columns) - 1)
        st.divider()
        if st.button("Generate Duplicated PDF", type="primary"):
            reader, pdf_writer = PdfReader(uploaded_pdf), PdfWriter()
            multiplier = 2 if mode == "Duplex" else 1
            for idx in range(len(reader.pages)):
                raw_qty = df_dup.iloc[idx][qty_col] if idx < len(df_dup) else 0
                try: qty = int(raw_qty) if pd.notna(raw_qty) else 0
                except ValueError: qty = 0
                for _ in range(qty * multiplier): pdf_writer.add_page(reader.pages[idx])
            buf = io.BytesIO()
            pdf_writer.write(buf)
            st.success("Done!")
            st.download_button(label="⬇️ Download", data=buf.getvalue(), file_name="Duplicated.pdf", mime="application/pdf")

elif st.session_state.current_page == "batch_consolidator":
    st.subheader("📦 PDF Store Batch Consolidator")
    uploaded_excel = st.file_uploader("1. Upload Excel Control Sheet First", type=["xlsx", "xls"])
    selected_metadata_cols, file_columns = [], []

    if uploaded_excel:
        df_control = pd.read_excel(uploaded_excel)
        all_columns = [str(col) for col in df_control.columns if not str(col).startswith("Unnamed:")]
        non_pdf_candidates = [col for col in all_columns if not col.strip().lower().endswith(".pdf")]
        file_columns = [col for col in all_columns if col.strip().lower().endswith(".pdf")]

        st.markdown("#### 📋 Select Metadata for Cover Header Page")
        cols_per_row = st.columns(min(len(non_pdf_candidates), 3) or 1)
        for idx, col_name in enumerate(non_pdf_candidates):
            with cols_per_row[idx % 3]:
                if st.checkbox(col_name, value=True, key=f"meta_{col_name}"): selected_metadata_cols.append(col_name)

        st.divider()
        uploaded_pdfs = st.file_uploader("2. Upload PDF Files", type=["pdf"], accept_multiple_files=True)
        max_pages_per_file = st.number_input("Maximum Target Pages Per PDF File:", min_value=1, max_value=10000, value=50, step=5)

        if st.button("Generate Master PDF(s)", type="primary"):
            if not uploaded_pdfs: st.error("Please upload the target PDF files.")
            else:
                pdf_dict = {pdf_file.name.lower(): pdf_file for pdf_file in uploaded_pdfs}
                store_data_list, grand_total_pages = [], 0
                for index, row in df_control.iterrows():
                    metadata_dict = {col: row[col] for col in selected_metadata_cols if col in row}
                    content_page_count, valid_files_to_add, d_w, d_h = 0, [], 612, 792
                    for file_name in file_columns:
                        qty_value = row[file_name]
                        if pd.notna(qty_value):
                            try: qty = int(qty_value)
                            except ValueError: continue
                            if qty > 0:
                                pdf_key = str(file_name).strip().lower() if str(file_name).strip().lower().endswith(".pdf") else f"{str(file_name).strip().lower()}.pdf"
                                if pdf_key in pdf_dict:
                                    pdf_file_obj = pdf_dict[pdf_key]
                                    pdf_file_obj.seek(0)
                                    rdr = PdfReader(pdf_file_obj)
                                    if rdr.pages:
                                        d_w, d_h = float(rdr.pages[0].mediabox.width), float(rdr.pages[0].mediabox.height)
                                    content_page_count += len(rdr.pages) * qty
                                    valid_files_to_add.append((pdf_file_obj, qty))
                    store_data_list.append({"metadata": metadata_dict, "total_pages": 1 + content_page_count, "files": valid_files_to_add, "width": d_w, "height": d_h})
                    grand_total_pages += 1 + content_page_count

                batches, current_batch, current_batch_page_count = [], [], 0
                for store in store_data_list:
                    if current_batch_page_count + store["total_pages"] > max_pages_per_file and current_batch:
                        batches.append(current_batch)
                        current_batch, current_batch_page_count = [], 0
                    current_batch.append(store)
                    current_batch_page_count += store["total_pages"]
                if current_batch: batches.append(current_batch)

                generated_files = []
                for batch_idx, batch_stores in enumerate(batches, start=1):
                    pdf_writer = PdfWriter()
                    for store in batch_stores:
                        header_pdf = create_header_pdf(store["metadata"], store["total_pages"], page_width=store["width"], page_height=store["height"])
                        pdf_writer.add_page(header_pdf.pages[0])
                        for pdf_file_obj, qty in store["files"]:
                            pdf_file_obj.seek(0)
                            rdr = PdfReader(pdf_file_obj)
                            for _ in range(qty):
                                for page in rdr.pages: pdf_writer.add_page(page)
                    buf = io.BytesIO()
                    pdf_writer.write(buf)
                    generated_files.append((f"Batch_{batch_idx}_of_{len(batches)}.pdf", buf.getvalue()))

                if len(generated_files) == 1:
                    st.download_button(label="⬇️ Download PDF", data=generated_files[0][1], file_name=generated_files[0][0], mime="application/pdf")
                else:
                    z_buf = io.BytesIO()
                    with zipfile.ZipFile(z_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                        for fn, fb in generated_files: zf.writestr(fn, fb)
                    st.download_button(label="⬇️ Download ZIP", data=z_buf.getvalue(), file_name="Consolidated_Batches.zip", mime="application/zip")

elif st.session_state.current_page == "batches_and_labels":
    st.subheader("🏷️ Batches & Labels Dashboard")
    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        if st.button("🏷️ Batch Headers", use_container_width=True, key="nav_btn_headers"): st.session_state.batches_subtab = "batch_headers"
    with sub_col2:
        if st.button("🖨️ Print Labels", use_container_width=True, key="nav_btn_labels"): st.session_state.batches_subtab = "print_labels"
    with sub_col3:
        if st.button("📁 Print from File", use_container_width=True, key="nav_btn_file"): st.session_state.batches_subtab = "print_from_file"
    st.divider()

    if st.session_state.batches_subtab == "batch_headers":
        is_outside_work = st.checkbox("Create Outside Work Label?", value=False)
        if is_outside_work:
            col1, col2 = st.columns(2)
            with col1:
                supplier = st.text_input("Supplier:")
                job_no = st.text_input("Job No:", value="1615699")
                client = st.text_input("Client:", value="Precision Mail Pty Ltd")
            with col2:
                job_title = st.text_input("Job Title:", value="Rase Spares Scratchys")
                qty_this_pallet = st.text_input("Qty this Pallet:", value="1025")
                total_pallets = st.number_input("Total Pallets:", min_value=1, value=1)
            auto_number_pallets = st.checkbox("Include Total Pallet Count?", value=True)
            if st.button("Generate Outside Work Label PDF", type="primary"):
                pdf_bytes = create_outside_work_label_file(supplier, job_no, client, job_title, qty_this_pallet, int(total_pallets), auto_number_pallets)
                st.download_button(label="⬇️ Download", data=pdf_bytes, file_name="Outside_Work_Label.pdf", mime="application/pdf")
        else:
            col1, col2 = st.columns(2)
            with col1: job_no = st.text_input("Job No.:", value="054520")
            with col2: description = st.text_input("Description:", value="Fragrance Wk5-6")
            col3, col4 = st.columns(2)
            with col3: side_margin = st.number_input("Side Margin (pt):", min_value=0, value=50)
            with col4: total_batches = st.number_input("Total Batches:", min_value=1, value=20)
            auto_number = st.checkbox("Include Total Count?", value=True)
            if st.button("Generate Batch Headers PDF", type="primary"):
                pdf_bytes = create_batch_header_file(job_no, description, int(total_batches), auto_number, int(side_margin))
                st.download_button(label="⬇️ Download", data=pdf_bytes, file_name="Batch_Headers.pdf", mime="application/pdf")
                
    elif st.session_state.batches_subtab == "print_labels":
        col_grid1, col_grid2 = st.columns(2)
        with col_grid1:
            media_w_mm = st.number_input("Sheet Width (mm):", min_value=50.0, value=210.0, key="label_sheet_w")
            media_h_mm = st.number_input("Sheet Height (mm):", min_value=50.0, value=297.0, key="label_sheet_h")
            rows = st.number_input("Rows per Page:", min_value=1, value=7)
            cols = st.number_input("Columns per Page:", min_value=1, value=2)
            label_w_mm = st.number_input("Label Width (mm):", min_value=10.0, value=99.1)
            label_h_mm = st.number_input("Label Height (mm):", min_value=10.0, value=38.1)
        with col_grid2:
            gutter_x_mm = st.number_input("Horizontal Gutter (mm):", min_value=0.0, value=2.5)
            gutter_y_mm = st.number_input("Vertical Gutter (mm):", min_value=0.0, value=0.0)
            margin_x_mm = st.number_input("Page Side Margin (mm):", min_value=0.0, value=4.5)
            margin_y_mm = st.number_input("Page Top Margin (mm):", min_value=0.0, value=15.0)

        num_lines = st.number_input("Number of Text Lines per Label:", min_value=1, value=2)
        master_lines = []
        for i in range(int(num_lines)):
            l_col1, l_col2, l_col3 = st.columns([3, 1, 1])
            with l_col1: m_text = st.text_input(f"Line {i+1} Master Text:", value=f"Sample Text {i+1}", key=f"master_text_{i}")
            with l_col2: m_sz = st.number_input(f"Line {i+1} Master Size:", min_value=6, value=12, key=f"master_size_{i}")
            with l_col3: m_bld = st.checkbox("Bold", value=(i == 0), key=f"master_bold_{i}")
            master_lines.append({"text": m_text, "font_size": m_sz, "bold": m_bld})

        total_labels = st.number_input("Total Labels to Print:", min_value=1, value=14)
        
        # Sequential Numbering configuration controls
        include_num = st.checkbox("Need sequential numbers?", value=True)
        start_num = 1
        prefix_num = ""
        if include_num:
            seq_col1, seq_col2 = st.columns(2)
            with seq_col1:
                start_num = st.number_input("Starting Number:", min_value=0, value=1, key="label_start_num")
            with seq_col2:
                prefix_num = st.text_input("Text before starting number (Prefix):", value="", key="label_prefix_num")

        # Background PDF configuration controls
        add_bg = st.checkbox("Do you want to add a background?", value=False, key="label_add_bg")
        background_bytes = None
        if add_bg:
            bg_file = st.file_uploader("Upload Background PDF File", type=["pdf"], key="label_bg_file")
            if bg_file is not None:
                background_bytes = bg_file.read()

        if st.button("Generate Imposed Labels PDF", type="primary"):
            mm_to_pt = 2.83465
            pdf_buffer = create_labels_pdf(
                media_w_mm * mm_to_pt, media_h_mm * mm_to_pt,
                int(rows), int(cols),
                label_w_mm * mm_to_pt, label_h_mm * mm_to_pt,
                gutter_x_mm * mm_to_pt, gutter_y_mm * mm_to_pt,
                margin_x_mm * mm_to_pt, margin_y_mm * mm_to_pt,
                master_lines, int(total_labels), include_num,
                start_num=int(start_num), prefix_num=prefix_num,
                background_pdf_bytes=background_bytes
            )
            st.success("Label sheet generated successfully!")
            st.download_button(label="⬇ Download Labels", data=pdf_buffer, file_name="Labels_Output.pdf", mime="application/pdf")

    elif st.session_state.batches_subtab == "print_from_file":
        data_mode = st.radio("Select Processing Engine Mode:", ["Use Excel Data Source File", "Repeat Manual Entry Override Mode"], horizontal=True)
        df_labels, columns_list = None, []

        if data_mode == "Use Excel Data Source File":
            uploaded_data = st.file_uploader("Upload Excel Data Sheet", type=["xlsx", "xls"], key="label_data_uploader")
            if uploaded_data:
                df_labels = pd.read_excel(uploaded_data)
                columns_list = [str(c) for c in df_labels.columns]
                st.success(f"Tracked file with {len(df_labels)} rows.")

        col_grid1, col_grid2 = st.columns(2)
        with col_grid1:
            file_media_w_mm = st.number_input("Sheet Width (mm):", min_value=50.0, value=210.0, key="file_sheet_w")
            file_media_h_mm = st.number_input("Sheet Height (mm):", min_value=50.0, value=297.0, key="file_sheet_h")
            rows = st.number_input("Rows per Page:", min_value=1, value=7, key="file_rows")
            cols = st.number_input("Columns per Page:", min_value=1, value=2, key="file_cols")
            label_w_mm = st.number_input("Label Width (mm):", min_value=10.0, value=99.1, key="file_w")
            label_h_mm = st.number_input("Label Height (mm):", min_value=10.0, value=38.1, key="file_h")
        with col_grid2:
            gutter_x_mm = st.number_input("Horizontal Gutter (mm):", min_value=0.0, value=2.5, key="file_gx")
            gutter_y_mm = st.number_input("Vertical Gutter (mm):", min_value=0.0, value=0.0, key="file_gy")
            margin_x_mm = st.number_input("Page Side Margin (mm):", min_value=0.0, value=4.5, key="file_mx")
            margin_y_mm = st.number_input("Page Top Margin (mm):", min_value=0.0, value=15.0, key="file_my")

        num_lines = st.number_input("Number of Text Lines per Label:", min_value=1, value=2, key="file_num_lines")
        line_mappings = []
        for i in range(int(num_lines)):
            l_col1, l_col2, l_col3, l_col4 = st.columns([2, 3, 1, 1])
            with l_col1: source_type = st.radio(f"Line {i+1} Data Source:", ["Manual Entry Only", "Excel Column Header Bind"], key=f"src_type_{i}")
            with l_col2:
                bound_col, manual_text = None, ""
                if source_type == "Excel Column Header Bind" and columns_list:
                    bound_col = st.selectbox(f"Bind Column:", columns_list, key=f"bind_col_{i}")
                    manual_text = st.text_input(f"Append Text:", key=f"append_txt_{i}")
                else:
                    manual_text = st.text_input(f"Static String:", value=f"Sample Text {i+1}", key=f"manual_txt_{i}")
            with l_col3: line_sz = st.number_input(f"Size:", min_value=6, value=12, key=f"file_sz_{i}")
            with l_col4: line_bld = st.checkbox("Bold", value=(i == 0), key=f"file_bld_{i}")
            line_mappings.append({"type": source_type, "column": bound_col, "text": manual_text, "font_size": line_sz, "bold": line_bld})

        total_clones = st.number_input("Total Repeated Labels:", min_value=1, value=30) if data_mode != "Use Excel Data Source File" else len(df_labels) if df_labels is not None else 0

        # Sequential Numbering configuration controls for Print from File
        include_num_file = st.checkbox("Need sequential numbers?", value=False, key="file_include_num")
        start_num_file = 1
        prefix_num_file = ""
        if include_num_file:
            seq_col1, seq_col2 = st.columns(2)
            with seq_col1:
                start_num_file = st.number_input("Starting Number:", min_value=0, value=1, key="file_start_num")
            with seq_col2:
                prefix_num_file = st.text_input("Text before starting number (Prefix):", value="", key="file_prefix_num")

        # Background PDF configuration controls for Print from File
        add_bg_file = st.checkbox("Do you want to add a background?", value=False, key="file_add_bg")
        background_bytes_file = None
        if add_bg_file:
            bg_file_obj = st.file_uploader("Upload Background PDF File", type=["pdf"], key="file_bg_file")
            if bg_file_obj is not None:
                background_bytes_file = bg_file_obj.read()

        if st.button("Generate Imposed Data Labels PDF", type="primary"):
            processed_breaks_configs = []
            if data_mode == "Use Excel Data Source File" and df_labels is not None:
                for r_idx in range(int(total_clones)):
                    row_data = df_labels.iloc[r_idx]
                    row_lines = []
                    for mapping in line_mappings:
                        if mapping["type"] == "Excel Column Header Bind" and mapping["column"]:
                            val = row_data[mapping["column"]]
                            txt = f"{mapping['text']} {val}".strip() if mapping["text"] else str(val)
                        else: txt = mapping["text"]
                        row_lines.append({"text": txt, "font_size": mapping["font_size"], "bold": mapping["bold"]})
                    processed_breaks_configs.append({
                        "count": 1, 
                        "include_numbering": include_num_file, 
                        "start_num": int(start_num_file) + r_idx, 
                        "prefix_num": prefix_num_file, 
                        "lines": row_lines, 
                        "total_labels_global": int(total_clones)
                    })
            else:
                clone_lines = [{"text": m["text"], "font_size": m["font_size"], "bold": m["bold"]} for m in line_mappings]
                processed_breaks_configs.append({
                    "count": int(total_clones), 
                    "include_numbering": include_num_file, 
                    "start_num": int(start_num_file), 
                    "prefix_num": prefix_num_file, 
                    "lines": clone_lines, 
                    "total_labels_global": int(total_clones)
                })

            mm_to_pt = 2.83465
            pdf_buffer = create_labels_pdf(
                file_media_w_mm * mm_to_pt, file_media_h_mm * mm_to_pt,
                int(rows), int(cols),
                label_w_mm * mm_to_pt, label_h_mm * mm_to_pt,
                gutter_x_mm * mm_to_pt, gutter_y_mm * mm_to_pt,
                margin_x_mm * mm_to_pt, margin_y_mm * mm_to_pt,
                [], int(total_clones), include_num_file,
                start_num=int(start_num_file), prefix_num=prefix_num_file,
                background_pdf_bytes=background_bytes_file, breaks_configs=processed_breaks_configs
            )
            st.success("Data Labels Sheet generated!")
            st.download_button(label="⬇ Download", data=pdf_buffer, file_name="Data_Labels.pdf", mime="application/pdf")

elif st.session_state.current_page == "general":
    st.subheader("⚙️ General Settings")
    st.write("Configure application parameters and system defaults.")
    st.info("System operational. All dependencies loaded.")
