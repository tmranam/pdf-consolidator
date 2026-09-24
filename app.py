import io
import math
import os
import zipfile
import pandas as pd
from pypdf import PdfReader, PdfWriter
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

# Initialize navigation state
if "current_page" not in st.session_state:
    st.session_state.current_page = "batch_consolidator"
if "batches_subtab" not in st.session_state:
    st.session_state.batches_subtab = "batch_headers"


# Helper function for consolidator cover pages
def create_header_pdf(
    metadata_dict, total_pages, page_width=612, page_height=792
):
    packet = io.BytesIO()
    can = canvas.Canvas(
        packet, pagesize=(float(page_width), float(page_height))
    )

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


# Helper function for Standard Batch Header generation
def create_batch_header_file(
    job_no, description, total_batches, auto_number=True, side_margin=50
):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    page_width, page_height = letter

    center_x = page_width / 2.0

    # Define paragraph style for multi-line wrapped description text
    desc_style = ParagraphStyle(
        "DescStyle",
        fontName="Helvetica-Bold",
        fontSize=32,
        leading=38,
        alignment=1,  # 1 = TA_CENTER
        textColor=HexColor("#000000"),
    )

    # Draw pages
    for i in range(1, total_batches + 1):
        # 1. Job No. (Large font at the top)
        can.setFont("Helvetica-Bold", 70)
        can.drawCentredString(center_x, page_height - 110, str(job_no))

        # 2. Wrapped Description with side margins
        max_desc_width = page_width - (2 * side_margin)
        desc_para = Paragraph(str(description), desc_style)
        para_w, para_h = desc_para.wrap(max_desc_width, page_height)

        # Base Y positioning adjusted so multi-line wraps go downwards neatly
        desc_y = page_height - 140 - para_h
        desc_para.drawOn(can, side_margin, desc_y)

        # 3. Batch Numbering on 3 separate lines
        can.setFont("Helvetica-Bold", 90)

        # Line 1: Current Batch Number (e.g. 1)
        can.drawCentredString(center_x, page_height - 290, str(i))

        # Line 2: OF
        can.setFont("Helvetica-Bold", 50)
        can.drawCentredString(center_x, page_height - 370, "OF")

        # Line 3: Total Batches (e.g. 12 or ______ )
        can.setFont("Helvetica-Bold", 90)
        if auto_number:
            total_str = str(total_batches)
        else:
            total_str = "______"

        can.drawCentredString(center_x, page_height - 470, total_str)

        can.showPage()

    can.save()
    packet.seek(0)
    return packet


# Helper function for Outside Work Label generator matching image format exactly
def create_outside_work_label_file(
    supplier,
    job_no,
    client,
    job_title,
    qty_this_pallet,
    total_pallets,
    auto_number_pallets=True,
):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    page_width, page_height = A4

    # Theme colors extracted from reference design
    cyan_bg = HexColor("#00AEEF")
    dark_frame = HexColor("#1A1A1A")
    text_dark = HexColor("#1A1A1A")

    # 80mm top clearance conversion (1 mm = ~2.83465 points)
    top_clearance_pt = 80 * 2.83465

    for i in range(1, total_pallets + 1):
        # 1. Fill Page Background (Bright Cyan/Blue)
        can.setFillColor(cyan_bg)
        can.rect(0, 0, page_width, page_height, fill=1, stroke=0)

        # 2. Outer Chamfered Border Frame (starts below the 80mm clearance)
        margin_x = 35
        margin_bottom = 35
        margin_top = top_clearance_pt
        corner_cut = 25  # Corner angle cutout at the top

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

        # 3. Top Section: From Address & Logo (shifted down below 80mm gap)
        can.setFillColor(text_dark)
        can.setFont("Helvetica-Bold", 11)
        can.drawString(margin_x + 20, frame_top_y - 40, "From:")
        can.setFont("Helvetica-Bold", 14)
        can.drawString(margin_x + 20, frame_top_y - 58, "IVE Print")
        can.setFont("Helvetica", 11)
        can.drawString(margin_x + 20, frame_top_y - 74, "24-36 Beyer Rd, Braeside")
        can.drawString(margin_x + 20, frame_top_y - 88, "Victoria 3195")

        # Top Right "ive" logo
        can.setFont("Helvetica-Bold", 46)
        can.drawRightString(
            page_width - margin_x - 25, frame_top_y - 70, "ive"
        )

        # 4. Dark Block Banner: "OUTSIDE WORK"
        banner_y = frame_top_y - 260
        banner_h = 160
        can.setFillColor(dark_frame)
        can.rect(
            margin_x,
            banner_y,
            page_width - (margin_x * 2),
            banner_h,
            fill=1,
            stroke=0,
        )

        can.setFillColor(HexColor("#FFFFFF"))
        can.setFont("Helvetica-Bold", 80)
        can.drawCentredString(page_width / 2.0, banner_y + 92, "OUTSIDE")
        can.drawCentredString(page_width / 2.0, banner_y + 32, "WORK")

        # 5. Form Fields with Dotted Baseline Guides
        fields = [
            ("Supplier:", supplier),
            ("Job No:", job_no),
            ("Client:", client),
            ("Job Title:", job_title),
            ("Qty this pallet:", qty_this_pallet),
        ]

        y_start = banner_y - 38
        line_gap = 36

        can.setFillColor(text_dark)

        for idx, (label, val) in enumerate(fields):
            curr_y = y_start - (idx * line_gap)

            # Field Label
            can.setFont("Helvetica", 15)
            can.drawString(margin_x + 20, curr_y, label)

            label_width = can.stringWidth(label, "Helvetica", 15)
            dots_x_start = margin_x + 25 + label_width

            # Render Form Entry Text
            if val:
                can.setFont("Helvetica-Bold", 18)
                can.drawString(dots_x_start + 10, curr_y, str(val))

            # Render Dotted Line Baseline
            can.setStrokeColor(dark_frame)
            can.setLineWidth(1)
            can.setDash([1, 3], 0)
            can.line(
                dots_x_start,
                curr_y - 2,
                page_width - margin_x - 20,
                curr_y - 2,
            )

        # 6. Bottom Row: Pallet X of Y
        y_pallet = y_start - (len(fields) * line_gap)

        can.setFont("Helvetica", 15)
        can.drawString(margin_x + 20, y_pallet, "Pallet:")

        # Draw Pallet Number
        can.setFont("Helvetica-Bold", 18)
        can.drawString(margin_x + 90, y_pallet, str(i))

        # "of:" text
        can.setFont("Helvetica", 15)
        can.drawString(margin_x + 145, y_pallet, "of:")

        # Draw Total Pallets value
        total_str = str(total_pallets) if auto_number_pallets else ""
        if total_str:
            can.setFont("Helvetica-Bold", 18)
            can.drawString(margin_x + 180, y_pallet, total_str)

        # Final Dotted Line across the bottom
        can.setStrokeColor(dark_frame)
        can.setLineWidth(1)
        can.setDash([1, 3], 0)
        can.line(
            margin_x + 20,
            y_pallet - 2,
            page_width - margin_x - 20,
            y_pallet - 2,
        )

        # Reset Dash Pattern for clean next page rendering
        can.setDash([], 0)

        can.showPage()

    can.save()
    packet.seek(0)
    return packet


# Helper function for Print Labels Imposition
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def create_labels_pdf(
    rows,
    cols,
    label_w_pt,
    label_h_pt,
    gutter_x_pt,
    gutter_y_pt,
    margin_x_pt,
    margin_y_pt,
    lines_config,
    total_labels,
    include_numbering,
    breaks_configs=None
):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    a4_w, a4_h = A4
    
    # 1. Standard Fallback to single batch mode if breaks_configs is missing
    if not breaks_configs:
        breaks_configs = [{
            "count": total_labels,
            "include_numbering": include_numbering,
            "num_mode": "Restart from new number",
            "start_num": 1,
            "end_num": total_labels,
            "lines": lines_config,
            "total_labels_global": total_labels
        }]
    
    # 2. Flatten all labels into a linear sequence across batches
    all_computed_labels = []
    for batch in breaks_configs:
        b_count = batch.get("count", 0)
        b_lines = batch.get("lines", [])
        b_inc_num = batch.get("include_numbering", True)
        b_start = batch.get("start_num", 1)
        b_global_total = batch.get("total_labels_global", b_count)
        
        for i in range(b_count):
            label_data = {
                "lines": list(b_lines),
                "show_num": b_inc_num,
                "current_idx": b_start + i,
                "total_idx": b_global_total
            }
            all_computed_labels.append(label_data)
            
    # 3. Impose the flattened label array onto A4 grid layout matrix
    total_to_render = len(all_computed_labels)
    label_ptr = 0
    
    while label_ptr < total_to_render:
        for r in range(rows):
            for c in range(cols):
                if label_ptr >= total_to_render:
                    break
                
                # Fetch calculated positions
                x_left = margin_x_pt + c * (label_w_pt + gutter_x_pt)
                y_top = a4_h - margin_y_pt - r * (label_h_pt + gutter_y_pt)
                center_x = x_left + (label_w_pt / 2.0)
                
                current_label_data = all_computed_labels[label_ptr]
                active_lines = list(current_label_data["lines"])
                
                # Append sequential indexing if active
                if current_label_data["show_num"]:
                    active_lines.append({
                        "text": f"{current_label_data['current_idx']} of {current_label_data['total_idx']}",
                        "font_size": 10,
                        "bold": True
                    })
                
                # Render content blocks inside grid margins
                total_content_lines = len(active_lines)
                if total_content_lines > 0:
                    line_height = label_h_pt / (total_content_lines + 1)
                    current_y = y_top - line_height
                    
                    for line in active_lines:
                        font_name = "Helvetica-Bold" if line.get("bold", False) else "Helvetica"
                        can.setFont(font_name, line.get("font_size", 12))
                        can.drawCentredString(center_x, current_y, str(line.get("text", "")))
                        current_y -= line_height
                
                label_ptr += 1
                
        # Commit the grid canvas page configuration and break cleanly to next page sheet
        can.showPage()
        
    can.save()
    packet.seek(0)
    return packet


# =====================================================================
# SHARED IMPOSITION HELPERS
# (compute_grid_positions + execute_pdf_imposition were previously
# missing from this file — both are required by the Impose page below)
# =====================================================================

def compute_grid_positions(media_w, media_h, trim_w, trim_h, gutter_x, gutter_y,
                            margin_left, margin_right, margin_top, margin_bottom,
                            cols, rows):
    """
    Pure geometry helper — works in ANY consistent unit (mm or pt), since it only
    depends on ratios/sums of the inputs. Used by both execute_pdf_imposition (pt)
    and the on-screen layout preview (mm), so the two always stay perfectly in sync.

    Returns a dict with:
        positions: list of {row, col, x, y} — x,y = bottom-left corner of each
                   trim box, measured from the sheet's bottom-left corner (0,0).
        grid_w, grid_h: total footprint of the populated grid (no margins).
        avail_w, avail_h: printable area (sheet minus margins).
        center_offset_x/y: offsets used to center the grid within the margins.
    """
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
            x = center_offset_x + (c * step_x)
            y = media_h - center_offset_y - (r * step_y) - trim_h
            positions.append({'row': r, 'col': c, 'x': x, 'y': y})

    return {
        'positions': positions,
        'grid_w': grid_w,
        'grid_h': grid_h,
        'avail_w': avail_w,
        'avail_h': avail_h,
        'center_offset_x': center_offset_x,
        'center_offset_y': center_offset_y,
    }


def execute_pdf_imposition(input_bytes, config):
    import math
    import io
    from pypdf import PdfReader, PdfWriter, PageObject, Transformation
    from pypdf.generic import RectangleObject
    from reportlab.pdfgen import canvas

    # 1 mm = 2.83464566929 PDF Points (72 / 25.4)
    MM_TO_PT = 72.0 / 25.4

    # Parse dimensions and lock explicitly to points
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

    # --- Page Identifier config ---
    page_id_enabled = config.get('page_id_enabled', False)
    page_id_text = config.get('page_id_text', "")
    page_id_font_size = float(config.get('page_id_font_size', 8.0))
    page_id_margin = float(config.get('page_id_margin', 5.0)) * MM_TO_PT
    page_id_position = config.get('page_id_position', "Bottom")  # Top/Bottom/Left/Right
    page_id_sides = config.get('page_id_sides', "Both Sides")    # "Both Sides" / "Front Only"

    reader = PdfReader(io.BytesIO(input_bytes))
    layout_mode = config.get('layout_mode', "Repeat / Step & Repeat")

    # --- "Mix" config -------------------------------------------------
    # Mix mode splits the document into `mix_sections` parallel streams and
    # assigns them to columns by (column index) % mix_sections -- i.e. the
    # pattern of sections REPEATS every `mix_sections` columns across the
    # sheet's width (interleaved striping), not clustered into one block of
    # adjacent columns. Every row within a given column shows the identical
    # page (rows are pure copies, they never affect which section a
    # position belongs to). This is why:
    #   mix_sections == 1     -> identical to "Repeat / Step & Repeat"
    #   mix_sections == cols  -> every column is its own section (rows-only
    #                            copies per column -- the classic case where
    #                            mix_sections == number of distinct blocks)
    is_mix_mode = "Mix" in layout_mode
    mix_sections = int(config.get('mix_sections', 1)) if is_mix_mode else None
    # -------------------------------------------------------------------

    # Build Page Pool
    # Mix mode uses the full unique page list too -- replication for copies
    # happens via placement (below), not by duplicating pool entries.
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

    config_cols = config.get('cols')
    config_rows = config.get('rows')

    avail_w_tmp = media_w - margin_left - margin_right
    avail_h_tmp = media_h - margin_top - margin_bottom
    step_x = trim_w + gutter_x
    step_y = trim_h + gutter_y

    if config_cols is not None and int(config_cols) > 0:
        cols = int(config_cols)
    else:
        cols = max(1, int((avail_w_tmp + gutter_x) / step_x))

    if config_rows is not None and int(config_rows) > 0:
        rows = int(config_rows)
    else:
        rows = max(1, int((avail_h_tmp + gutter_y) / step_y))

    # --- Use shared helper for grid geometry (front-side positions) ---
    geo = compute_grid_positions(
        media_w, media_h, trim_w, trim_h, gutter_x, gutter_y,
        margin_left, margin_right, margin_top, margin_bottom,
        cols, rows
    )
    avail_w = geo['avail_w']
    avail_h = geo['avail_h']
    grid_w = geo['grid_w']
    grid_h = geo['grid_h']
    center_offset_x = geo['center_offset_x']
    center_offset_y = geo['center_offset_y']

    ups_per_page = cols * rows

    # --- SAFETY CHECK: make sure the requested grid actually fits on the sheet ---
    if grid_w > avail_w + 0.01 or grid_h > avail_h + 0.01:
        raise ValueError(
            f"Requested layout of {cols} cols x {rows} rows does not fit on the sheet. "
            f"Grid needs {grid_w/MM_TO_PT:.2f}mm x {grid_h/MM_TO_PT:.2f}mm, but only "
            f"{avail_w/MM_TO_PT:.2f}mm x {avail_h/MM_TO_PT:.2f}mm is available "
            f"(sheet size minus margins). Reduce cols/rows, trim size, gutters, or margins."
        )

    # Mirrored offset for duplex back pages, measured from the right edge
    center_offset_x_right = margin_right + (avail_w - grid_w) / 2.0

    # --- Mix-mode grouping ---------------------------------------------
    mix_num_groups = None
    if is_mix_mode:
        if mix_sections < 1 or mix_sections > cols:
            raise ValueError(
                f"'Number of sections' ({mix_sections}) must be between 1 and the "
                f"number of columns ({cols}) -- each section needs at least one "
                f"dedicated column to repeat through."
            )
        mix_num_groups = mix_sections
    # -------------------------------------------------------------------

    if is_mix_mode:
        # One page advances per section per sheet -- same shape of formula as
        # Cut and Stack's stack_depth, just keyed on sections instead of
        # individual positions.
        stack_depth = math.ceil(total_input_pages / mix_num_groups)
    else:
        stack_depth = math.ceil(total_input_pages / ups_per_page)

    is_duplex = config.get('duplex', False)
    if is_duplex and (stack_depth % 2 != 0):
        stack_depth += 1

    total_sheets = stack_depth
    # --- Physical sheet numbering: front+back of the same paper share one number ---
    total_physical_sheets = (total_sheets // 2) if is_duplex else total_sheets

    writer = PdfWriter()

    fit_to_size = config.get('fit_to_size', True)
    mag_factor = float(config.get('magnification_pct', 100.0)) / 100.0
    last_computed_scale = 1.0

    for sheet_idx in range(total_sheets):
        sheet = PageObject.create_blank_page(width=media_w, height=media_h)
        is_back_page = is_duplex and (sheet_idx % 2 == 1)

        if is_duplex:
            current_stack_layer = sheet_idx // 2
            total_stack_layers = total_sheets // 2
        else:
            current_stack_layer = sheet_idx
            total_stack_layers = total_sheets

        physical_sheet_number = (sheet_idx // 2) + 1 if is_duplex else sheet_idx + 1

        mark_packet = io.BytesIO()
        mark_can = canvas.Canvas(mark_packet, pagesize=(media_w, media_h))
        # Draw in pure CMYK black (K-plate only) — never RGB — to keep the file
        # consistently CMYK end-to-end.
        mark_can.setStrokeColorCMYK(0, 0, 0, 1)
        mark_can.setFillColorCMYK(0, 0, 0, 1)
        mark_can.setLineWidth(0.5)
        mark_style = config.get('trim_marks_style', "None")

        for r in range(rows):
            for c in range(cols):
                if "Cut and Stack" in layout_mode:
                    if is_duplex:
                        if is_back_page:
                            c_front = cols - 1 - c
                            grid_position_idx = (r * cols) + c_front
                            input_page_idx = (grid_position_idx * (total_stack_layers * 2)) + (current_stack_layer * 2) + 1
                        else:
                            grid_position_idx = (r * cols) + c
                            input_page_idx = (grid_position_idx * (total_stack_layers * 2)) + (current_stack_layer * 2)
                    else:
                        grid_position_idx = (r * cols) + c
                        input_page_idx = (grid_position_idx * total_stack_layers) + current_stack_layer

                elif is_mix_mode:
                    # Interleaved column striping: the section pattern repeats
                    # every `mix_sections` columns across the sheet's width, and
                    # every row within a column shows the identical page (rows
                    # are pure copies -- they never affect the section). Mirror
                    # the column on the back side (same trick Cut and Stack
                    # uses) so front/back line up physically after a duplex flip.
                    c_logical = (cols - 1 - c) if is_back_page else c
                    group_id = c_logical % mix_sections

                    if is_duplex:
                        input_page_idx = (
                            (group_id * (total_stack_layers * 2))
                            + (current_stack_layer * 2)
                            + (1 if is_back_page else 0)
                        )
                    else:
                        input_page_idx = (group_id * total_stack_layers) + current_stack_layer

                else:
                    input_page_idx = (sheet_idx * ups_per_page) + (r * cols + c)

                if input_page_idx >= total_input_pages:
                    continue

                input_page = page_pool[input_page_idx]

                # --- FIX 1: NORMALIZE SOURCE PAGE ORIGIN TO (0,0) ---
                ll_x = float(input_page.mediabox.lower_left[0])
                ll_y = float(input_page.mediabox.lower_left[1])
                orig_w = float(input_page.mediabox.width)
                orig_h = float(input_page.mediabox.height)

                # --- CENTERED POSITIONING ---
                if is_back_page:
                    c_eff = cols - 1 - c
                    x_pos = media_w - center_offset_x_right - (c_eff * step_x) - trim_w
                else:
                    x_pos = center_offset_x + (c * step_x)

                y_pos = media_h - center_offset_y - (r * step_y) - trim_h

                target_w = trim_w + (2 * bleed)
                target_h = trim_h + (2 * bleed)

                if fit_to_size:
                    scale = min(target_w / orig_w, target_h / orig_h)
                else:
                    scale = 1.0 * mag_factor

                last_computed_scale = scale

                # --- FIX 2: ACCOUNT FOR ORIGINAL LOWER-LEFT SHIFTS ---
                tx = x_pos - bleed + (target_w - (orig_w * scale)) / 2 - (ll_x * scale)
                ty = y_pos - bleed + (target_h - (orig_h * scale)) / 2 - (ll_y * scale)

                op_transform = Transformation().scale(scale, scale).translate(tx, ty)
                sheet.merge_transformed_page(input_page, op_transform, expand=False)

                # Trim marks logic
                if mark_style != "None":
                    mark_len = 12.0
                    offset = bleed + 3.0
                    x1, x2 = x_pos, x_pos + trim_w
                    y1, y2 = y_pos, y_pos + trim_h

                    is_left_edge = (c == 0) if not is_back_page else (c == cols - 1)
                    is_right_edge = (c == cols - 1) if not is_back_page else (c == 0)
                    is_top_edge = (r == 0)
                    is_bottom_edge = (r == rows - 1)
                    draw_all = (mark_style == "All Individual Items")

                    if draw_all or (is_left_edge and is_top_edge):
                        mark_can.line(x1, y2 + offset, x1, y2 + offset + mark_len)
                        mark_can.line(x1 - offset, y2, x1 - offset - mark_len, y2)
                    if draw_all or (is_right_edge and is_top_edge):
                        mark_can.line(x2, y2 + offset, x2, y2 + offset + mark_len)
                        mark_can.line(x2 + offset, y2, x2 + offset + mark_len, y2)
                    if draw_all or (is_left_edge and is_bottom_edge):
                        mark_can.line(x1, y1 - offset, x1, y1 - offset - mark_len)
                        mark_can.line(x1 - offset, y1, x1 - offset - mark_len, y1)
                    if draw_all or (is_right_edge and is_bottom_edge):
                        mark_can.line(x2, y1 - offset, x2, y1 - offset - mark_len)
                        mark_can.line(x2 + offset, y1, x2 + offset + mark_len, y1)

        # --- PAGE IDENTIFIER: draw "{text} Page X of N" at the chosen edge ---
        should_draw_id = page_id_enabled and page_id_text.strip() != ""
        if should_draw_id and is_back_page and page_id_sides == "Front Only":
            should_draw_id = False

        if should_draw_id:
            id_string = f"{page_id_text.strip()} Page {physical_sheet_number} of {total_physical_sheets}"
            mark_can.setFont("Helvetica", page_id_font_size)

            if page_id_position == "Top":
                baseline_y = media_h - page_id_margin - page_id_font_size
                mark_can.drawCentredString(media_w / 2.0, baseline_y, id_string)
            elif page_id_position == "Bottom":
                baseline_y = page_id_margin
                mark_can.drawCentredString(media_w / 2.0, baseline_y, id_string)
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

        # --- FIX 3: HARD LOCK OUTPUT BOUNDING BOXES TO EXACT SHEET SIZE ---
        box_rect = RectangleObject([0, 0, media_w, media_h])
        sheet.mediabox = box_rect
        sheet.cropbox = box_rect
        sheet.trimbox = box_rect
        sheet.bleedbox = box_rect

        writer.add_page(sheet)

    output_stream = io.BytesIO()
    writer.write(output_stream)
    return output_stream.getvalue(), ups_per_page, round(last_computed_scale * 100.0, 1)


def render_layout_preview(media_w_mm, media_h_mm, trim_w_mm, trim_h_mm,
                           bleed_mm, gutter_x_mm, gutter_y_mm,
                           margin_top_mm, margin_bottom_mm, margin_left_mm, margin_right_mm,
                           cols, rows, page_id_enabled, page_id_position, page_id_text,
                           layout_mode=None, mix_sections=None):
    """
    Builds a live SVG diagram of the current sheet/grid settings, entirely in
    millimeters — no external plotting library needed. Uses the SAME
    compute_grid_positions helper as execute_pdf_imposition, so what you see
    here always matches the real output geometry.

    When layout_mode contains "Mix" and mix_sections is given, columns are
    tinted by (column index) % mix_sections -- the same interleaved striping
    execute_pdf_imposition uses -- so you can visually confirm the section
    pattern (and that every row in a striped column matches) before running
    the job.
    Returns an SVG string (render with st.markdown(svg, unsafe_allow_html=True)).
    """
    import math

    geo = compute_grid_positions(
        media_w_mm, media_h_mm, trim_w_mm, trim_h_mm, gutter_x_mm, gutter_y_mm,
        margin_left_mm, margin_right_mm, margin_top_mm, margin_bottom_mm,
        cols, rows
    )

    fits = geo['grid_w'] <= geo['avail_w'] + 0.01 and geo['grid_h'] <= geo['avail_h'] + 0.01
    grid_color = "#4a90d9" if fits else "#d94a4a"

    is_mix_mode = bool(layout_mode) and ("Mix" in layout_mode) and mix_sections
    mix_palette = ["#4a90d9", "#e0a13a", "#5cb85c", "#b565d9", "#d95c8f", "#5cc9d9"]

    # Fit the sheet into a fixed-size canvas, preserving aspect ratio
    canvas_w, canvas_h = 480, 480
    pad = 20
    scale = min((canvas_w - 2 * pad) / media_w_mm, (canvas_h - 2 * pad) / media_h_mm) if media_w_mm > 0 and media_h_mm > 0 else 1
    offset_x, offset_y = pad, pad

    def to_svg_xy(x_mm, y_mm):
        # PDF-style y-up coords -> SVG y-down coords
        svg_x = offset_x + x_mm * scale
        svg_y = offset_y + (media_h_mm - y_mm) * scale
        return svg_x, svg_y

    svg_parts = []
    svg_parts.append(
        f'<svg viewBox="0 0 {canvas_w} {canvas_h}" width="100%" height="auto" '
        f'preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" '
        f'style="background:#fafafa;border:1px solid #ddd; display:block; max-width:100%;">'
    )

    # Sheet outline
    sx, sy = to_svg_xy(0, media_h_mm)
    svg_parts.append(
        f'<rect x="{sx}" y="{sy}" width="{media_w_mm*scale}" height="{media_h_mm*scale}" '
        f'fill="#f2f2f2" stroke="black" stroke-width="1.2" />'
    )

    # Margin boundary (printable area), dashed
    mx, my = to_svg_xy(margin_left_mm, media_h_mm - margin_top_mm)
    svg_parts.append(
        f'<rect x="{mx}" y="{my}" width="{geo["avail_w"]*scale}" height="{geo["avail_h"]*scale}" '
        f'fill="none" stroke="#888888" stroke-width="0.8" stroke-dasharray="4,3" />'
    )

    # Grid cells (trim boxes + bleed boxes)
    for idx, pos in enumerate(geo['positions']):
        # geo['positions'] is row-major (r*cols+c), matching the main fill
        # loop's r,c iteration order -- recover r,c to compute the Mix-mode
        # column-major group color.
        r, c = divmod(idx, cols)
        x, y = pos['x'], pos['y']

        cell_color = grid_color
        if is_mix_mode and fits:
            group_id = c % int(mix_sections)
            cell_color = mix_palette[group_id % len(mix_palette)]

        tx, ty = to_svg_xy(x, y + trim_h_mm)  # top-left corner in mm -> svg
        svg_parts.append(
            f'<rect x="{tx}" y="{ty}" width="{trim_w_mm*scale}" height="{trim_h_mm*scale}" '
            f'fill="{cell_color}" fill-opacity="0.35" stroke="{cell_color}" stroke-width="1.0" />'
        )
        if bleed_mm > 0:
            bx, by = to_svg_xy(x - bleed_mm, y + trim_h_mm + bleed_mm)
            svg_parts.append(
                f'<rect x="{bx}" y="{by}" width="{(trim_w_mm+2*bleed_mm)*scale}" height="{(trim_h_mm+2*bleed_mm)*scale}" '
                f'fill="none" stroke="red" stroke-width="0.6" stroke-dasharray="2,2" />'
            )

    # Page identifier indicator
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
            svg_parts.append(
                f'<text x="{lx}" y="{ly}" font-size="11" fill="green" text-anchor="middle" '
                f'transform="rotate(-90 {lx} {ly})">{label}</text>'
            )
        elif page_id_position == "Right":
            rx, ry = to_svg_xy(media_w_mm - 4, media_h_mm / 2.0)
            svg_parts.append(
                f'<text x="{rx}" y="{ry}" font-size="11" fill="green" text-anchor="middle" '
                f'transform="rotate(90 {rx} {ry})">{label}</text>'
            )

    # Title / fit warning
    title = f'{cols} x {rows} = {cols*rows}-up on {media_w_mm:.0f}x{media_h_mm:.0f}mm'
    if is_mix_mode:
        s = int(mix_sections)
        base_cols = cols // s
        extra = cols % s
        min_copies = rows * base_cols
        max_copies = rows * (base_cols + (1 if extra else 0))
        if extra == 0:
            title += f'  |  Mix: {s} sections x {min_copies} copies'
        else:
            title += f'  |  Mix: {s} sections, {min_copies}-{max_copies} copies (uneven)'
    if not fits:
        title += "  \u26A0 DOES NOT FIT"
    svg_parts.append(f'<text x="{canvas_w/2}" y="14" font-size="12" fill="#333" text-anchor="middle">{title}</text>')

    svg_parts.append('</svg>')
    return "".join(svg_parts)
# ---------------------------------------------------------
# DASHBOARD NAVIGATION BAR
# ---------------------------------------------------------
st.title("🛠️ PDF Toolsuite Dashboard")
st.write("Select a tool below to begin processing your files:")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("📐 Impose", use_container_width=True):
        st.session_state.current_page = "impose"

with col2:
    if st.button("📄 Duplicate", use_container_width=True):
        st.session_state.current_page = "duplicate"

with col3:
    if st.button("📦 Consolidator", use_container_width=True):
        st.session_state.current_page = "batch_consolidator"

with col4:
    if st.button("🏷️ Batches & Labels", use_container_width=True):
        st.session_state.current_page = "batches_and_labels"

with col5:
    if st.button("⚙️ General", use_container_width=True):
        st.session_state.current_page = "general"

st.divider()

# PAGE 1: IMPOSE (FIXED INTERFACE BUTTON & ST.RERUN BUGS)
# ---------------------------------------------------------
if st.session_state.current_page == "impose":
    st.subheader("📐 PDF Impose Layout Engine")
    st.write("Upload source materials to impose, scale, and arrange pages for high-volume production presses.")

    # State parameter check loop initialization
    if "system_auto_scale_feedback" not in st.session_state:
        st.session_state.system_auto_scale_feedback = 100.0

    # 1. Primary Work File Dropzone
    uploaded_impose_pdf = st.file_uploader("Upload Target PDF File to Impose", type=["pdf"], key="impose_file_uploader")

    st.divider()

    # --- Main layout: live preview (left) + all settings (right) ---
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
            with grid_col1:
                cols_input = st.number_input("Columns:", min_value=1, max_value=100, value=2, step=1, key="cols_input_widget")
            with grid_col2:
                rows_input = st.number_input("Rows:", min_value=1, max_value=100, value=4, step=1, key="rows_input_widget")

            total_ups_preview = int(cols_input) * int(rows_input)
            st.caption(f"➡️ This will place **{total_ups_preview}-up** per sheet ({int(cols_input)} cols x {int(rows_input)} rows).")

            print_style = st.radio("Output Surface Type:", ["Simplex", "Duplex"], horizontal=True)
            layout_choice = st.radio(
                "Step Sequencing Route Pattern:",
                ["Repeat / Step & Repeat", "Cut and Stack", "Mix (Sections + Copies)"],
                horizontal=False,
                help=(
                    "Repeat: every position on the sheet shows the same page, N-up -- best for 1 page, many copies. "
                    "Cut and Stack: every position is a unique page-slot, 1 copy per full run -- best for 1 copy of a huge document. "
                    "Mix: enter how many copies you want. The document is split into "
                    "(up-count ÷ copies) sections striped across the columns, so one print run "
                    "produces all your copies together in far fewer sheets than running Cut and "
                    "Stack once per copy, and with one simple final collation instead of "
                    "hand-picking pages across hundreds of sheets."
                ),
            )

            mix_sections_value = 1
            if layout_choice == "Mix (Sections + Copies)":
                mix_copies_value = st.number_input(
                    "How many copies do you want?:",
                    min_value=1,
                    max_value=max(1, total_ups_preview),
                    value=min(20, max(1, total_ups_preview)),
                    step=1,
                    key="mix_copies_input",
                    help=(
                        f"With {total_ups_preview}-up on the sheet, this many positions will be "
                        "dedicated to identical copies of each page. The document then splits into "
                        "(up-count ÷ copies) sections, each running down its own dedicated column(s) -- "
                        "see the summary below for exactly what that works out to."
                    ),
                )
                c_total = int(cols_input)
                r_total = int(rows_input)
                requested_copies = int(mix_copies_value)

                # Derive the section count from the requested copies: sections = ups / copies.
                mix_sections_value = max(1, total_ups_preview // requested_copies)
                # A section needs at least one dedicated column to stripe through.
                mix_sections_value = min(mix_sections_value, c_total)

                base_cols = c_total // mix_sections_value
                extra = c_total % mix_sections_value
                achieved_min = r_total * base_cols
                achieved_max = r_total * (base_cols + (1 if extra else 0))

                sheets_hint = ""
                if uploaded_impose_pdf is not None:
                    try:
                        uploaded_impose_pdf.seek(0)
                        _tmp_total_pages = len(PdfReader(uploaded_impose_pdf).pages)
                        uploaded_impose_pdf.seek(0)
                        sheets_needed = math.ceil(_tmp_total_pages / mix_sections_value)
                        sheets_hint = f" For your uploaded {_tmp_total_pages}-page file, that's **{sheets_needed} sheets**."
                    except Exception:
                        sheets_hint = ""

                if extra == 0 and achieved_min == requested_copies:
                    st.caption(
                        f"➡️ Splits the document into **{mix_sections_value} section(s)**, "
                        f"producing exactly **{requested_copies} copies** per sheet.{sheets_hint}"
                    )
                elif extra == 0:
                    st.caption(
                        f"➡️ Closest clean fit: **{mix_sections_value} section(s)**, "
                        f"producing **{achieved_min} copies** per sheet (you asked for {requested_copies}; "
                        f"{total_ups_preview}-up doesn't divide evenly by {requested_copies}).{sheets_hint}"
                    )
                else:
                    st.caption(
                        f"➡️ Splits the document into **{mix_sections_value} section(s)**, producing "
                        f"**{achieved_min}-{achieved_max} copies** per sheet (uneven -- {c_total} columns "
                        f"doesn't divide evenly by {mix_sections_value} sections).{sheets_hint}"
                    )

        with col_imp2:
            trim_w = st.number_input("Finished Trim Width (mm):", min_value=5.0, max_value=500.0, value=90.0, step=0.5)
            trim_h = st.number_input("Finished Trim Height (mm):", min_value=5.0, max_value=500.0, value=55.0, step=0.5)
            bleed_w = st.number_input("Bleed Envelope Margin (mm):", min_value=0.0, max_value=25.0, value=2.0, step=0.5)
            gut_x = st.number_input("Horizontal Gutter Gap (mm):", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            gut_y = st.number_input("Vertical Gutter Gap (mm):", min_value=0.0, max_value=100.0, value=0.0, step=0.5)

            st.write("---")
            fit_to_size_option = st.checkbox("Auto-Fit Content to Selected Trim Box?", value=True, help="When checked, automatically scales your design up or down to lock onto the trim size boundaries perfectly.")

            if fit_to_size_option:
                magnification_pct = st.number_input(
                    f"Artwork Magnification Scale (%):",
                    min_value=10.0, max_value=200.0,
                    value=float(st.session_state.system_auto_scale_feedback),
                    step=1.0, disabled=True,
                    help="Showing the calculated scale ratio performed by the Auto-Fit layout machine framework."
                )
            else:
                magnification_pct = st.number_input(
                    "Artwork Magnification Scale (%):",
                    min_value=10.0, max_value=200.0,
                    value=98.0, step=1.0,
                    help="Type any precise manual percentage scale constraint layout size rule."
                )

            trim_style_selection = st.selectbox(
                "Select Trim Marks Option style:",
                ["Outer Perimeter Only", "All Individual Items", "None"],
                index=0,
                help="Outer Perimeter Only ensures that no marks cut into the middle of the sheet or cross over adjacent artwork cells."
            )

        st.write("---")
        st.markdown("**Sheet Margins (mm):**")
        margin_col1, margin_col2, margin_col3, margin_col4 = st.columns(4)
        with margin_col1:
            margin_top_mm = st.number_input("Top:", min_value=0.0, max_value=200.0, value=25.0, step=1.0, key="margin_top_input")
        with margin_col2:
            margin_bottom_mm = st.number_input("Bottom:", min_value=0.0, max_value=200.0, value=25.0, step=1.0, key="margin_bottom_input")
        with margin_col3:
            margin_left_mm = st.number_input("Left:", min_value=0.0, max_value=200.0, value=25.0, step=1.0, key="margin_left_input")
        with margin_col4:
            margin_right_mm = st.number_input("Right:", min_value=0.0, max_value=200.0, value=25.0, step=1.0, key="margin_right_input")

        st.write("---")
        st.markdown("**Page Identifier (Counter):**")
        page_id_enabled = st.checkbox("Enable Page Identifier?", value=False, key="page_id_enabled_input")

        if page_id_enabled:
            page_id_text = st.text_input(
                "Custom Label Text:", value="File One", key="page_id_text_input",
                help='This text is followed automatically by "Page X of N" — e.g. "File One Page 1 of 8".'
            )

            id_col1, id_col2, id_col3 = st.columns(3)
            with id_col1:
                page_id_font_size = st.number_input("Font Size (pt):", min_value=4.0, max_value=72.0, value=8.0, step=0.5, key="page_id_font_size_input")
            with id_col2:
                page_id_margin = st.number_input("Margin from Edge (mm):", min_value=0.0, max_value=100.0, value=5.0, step=0.5, key="page_id_margin_input")
            with id_col3:
                page_id_position = st.selectbox("Position on Sheet:", ["Top", "Bottom", "Left", "Right"], index=1, key="page_id_position_input")

            page_id_sides = st.radio(
                "Apply Identifier To:", ["Both Sides", "Front Only"], horizontal=True, key="page_id_sides_input",
                help="For Duplex jobs: print the identifier on both the front and back of each sheet, or the front only."
            )
        else:
            page_id_text = ""
            page_id_font_size = 8.0
            page_id_margin = 5.0
            page_id_position = "Bottom"
            page_id_sides = "Both Sides"

    with main_preview_col:
        st.markdown("**Live Layout Preview:**")
        preview_svg = render_layout_preview(
            media_w_mm, media_h_mm, trim_w, trim_h,
            bleed_w, gut_x, gut_y,
            margin_top_mm, margin_bottom_mm, margin_left_mm, margin_right_mm,
            int(cols_input), int(rows_input),
            page_id_enabled, page_id_position, page_id_text,
            layout_mode=layout_choice,
            mix_sections=int(mix_sections_value) if layout_choice == "Mix (Sections + Copies)" else None,
        )
        st.markdown(
            f'<div style="width:100%; max-width:100%; overflow:hidden;">{preview_svg}</div>',
            unsafe_allow_html=True,
        )
        if layout_choice == "Mix (Sections + Copies)":
            st.caption("Each color band = one section of the document, repeated across its positions for your copies. Dotted red = bleed, dashed gray = margin boundary.")
        else:
            st.caption("Blue = trim boxes, dotted red = bleed, dashed gray = margin boundary. Updates live as you adjust settings.")

    st.divider()

    # Form Submission Trigger Action Button Hook
    if st.button("Run Sheet Imposition Processing", type="primary", use_container_width=True):
        if not uploaded_impose_pdf:
            st.error("⚠️ Active source PDF file stream data must be staged before layout processing.")
        else:
            with st.spinner("Calculating layout transformations and packing pages..."):
                try:
                    imposition_runtime_config = {
                        'media_w': media_w_mm,
                        'media_h': media_h_mm,
                        'trim_w': trim_w,
                        'trim_h': trim_h,
                        'bleed': bleed_w,
                        'gutter_x': gut_x,
                        'gutter_y': gut_y,
                        'cols': int(cols_input),
                        'rows': int(rows_input),
                        'margins': {
                            'top': margin_top_mm,
                            'bottom': margin_bottom_mm,
                            'left': margin_left_mm,
                            'right': margin_right_mm,
                        },
                        'layout_mode': layout_choice,
                        'mix_sections': int(mix_sections_value),
                        'duplex': (print_style == "Duplex"),
                        'repeat_per_page': int(cols_input) * int(rows_input),
                        'trim_marks_style': trim_style_selection,
                        'fit_to_size': fit_to_size_option,
                        'magnification_pct': float(magnification_pct),
                        'page_id_enabled': page_id_enabled,
                        'page_id_text': page_id_text,
                        'page_id_font_size': float(page_id_font_size),
                        'page_id_margin': float(page_id_margin),
                        'page_id_position': page_id_position,
                        'page_id_sides': page_id_sides,
                    }

                    raw_input_bytes = uploaded_impose_pdf.read()

                    compiled_output_pdf, total_calculated_ups, computed_percentage = execute_pdf_imposition(raw_input_bytes, imposition_runtime_config)

                    st.session_state.system_auto_scale_feedback = computed_percentage

                    st.success(f"🎉 Imposition Matrix Calculated Successfully! ({total_calculated_ups}-up per sheet)")

                    if fit_to_size_option:
                        st.info(f"📊 **Auto-Fit Metric:** Source artwork was automatically scaled to **{computed_percentage}%** of its original size to fit the requested trim window bounds.")

                    base_name = os.path.splitext(uploaded_impose_pdf.name)[0]

                    st.download_button(
                        label=f"⬇️ Download Imposed Output File",
                        data=compiled_output_pdf,
                        file_name=f"{base_name}_Imposed_{total_calculated_ups}Up.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

                except Exception as ex_err:
                    st.error(f"An unexpected failure sequence broke the layout engine logic block execution path: {str(ex_err)}")
# ---------------------------------------------------------
# PAGE 2: DUPLICATE PAGES
# ---------------------------------------------------------
elif st.session_state.current_page == "duplicate":
    st.subheader("📄 Duplicate Pages Tool")
    st.write(
        "Upload a multi-page PDF and an Excel sheet specifying the repeat quantity for each page."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        uploaded_pdf = st.file_uploader("1. Upload PDF File", type=["pdf"])
    with col_b:
        uploaded_excel = st.file_uploader(
            "2. Upload Excel Control Sheet",
            type=["xlsx", "xls"],
            key="dup_excel",
        )

    mode = st.radio(
        "3. Select Printing Mode:",
        ["Simplex", "Duplex"],
        horizontal=True,
        help="Simplex repeats each page N times. Duplex doubles the repeat count (2 × N times).",
    )

    if uploaded_pdf and uploaded_excel:
        df_dup = pd.read_excel(uploaded_excel)

        qty_col = st.selectbox(
            "Select Quantity/Copies Column from Excel:",
            df_dup.columns,
            index=len(df_dup.columns) - 1,
        )

        st.divider()

        if st.button("Generate Duplicated PDF", type="primary"):
            with st.spinner("Processing PDF page duplications..."):
                reader = PdfReader(uploaded_pdf)
                pdf_writer = PdfWriter()
                total_pdf_pages = len(reader.pages)

                multiplier = 2 if mode == "Duplex" else 1

                for idx in range(total_pdf_pages):
                    if idx < len(df_dup):
                        raw_qty = df_dup.iloc[idx][qty_col]
                        try:
                            qty = int(raw_qty) if pd.notna(raw_qty) else 0
                        except ValueError:
                            qty = 0
                    else:
                        qty = 0

                    total_copies = qty * multiplier

                    if total_copies > 0:
                        page_obj = reader.pages[idx]
                        for _ in range(total_copies):
                            pdf_writer.add_page(page_obj)

                output_buffer = io.BytesIO()
                pdf_writer.write(output_buffer)
                output_buffer.seek(0)

                pdf_basename = os.path.splitext(uploaded_pdf.name)[0]
                out_filename = f"{pdf_basename}_{mode}_Duplicated.pdf"

                st.success(
                    f"Successfully generated duplicated PDF in **{mode}** mode!"
                )
                st.download_button(
                    label=f"⬇️ Download {out_filename}",
                    data=output_buffer,
                    file_name=out_filename,
                    mime="application/pdf",
                )
# ---------------------------------------------------------
# PAGE 3: PDF STORE BATCH CONSOLIDATOR
# ---------------------------------------------------------
elif st.session_state.current_page == "batch_consolidator":
    st.subheader("📦 PDF Store Batch Consolidator")
    st.write(
        "Upload your Excel control sheet, select cover page fields, set batch limits, and process target PDFs."
    )

    uploaded_excel = st.file_uploader(
        "1. Upload Excel Control Sheet First", type=["xlsx", "xls"]
    )

    selected_metadata_cols = []
    file_columns = []
    df_control = None

    if uploaded_excel:
        df_control = pd.read_excel(uploaded_excel)

        all_columns = [
            str(col)
            for col in df_control.columns
            if not str(col).startswith("Unnamed:")
        ]

        non_pdf_candidates = []
        file_columns = []

        for col in all_columns:
            if col.strip().lower().endswith(".pdf"):
                file_columns.append(col)
            else:
                non_pdf_candidates.append(col)

        st.markdown("#### 📋 Select Metadata for Cover Header Page")
        st.write(
            "Check the column headers below that you want displayed on each store's cover page:"
        )

        cols_per_row = st.columns(min(len(non_pdf_candidates), 3) or 1)
        for idx, col_name in enumerate(non_pdf_candidates):
            with cols_per_row[idx % 3]:
                if st.checkbox(col_name, value=True, key=f"meta_{col_name}"):
                    selected_metadata_cols.append(col_name)

        st.divider()

        uploaded_pdfs = st.file_uploader(
            "2. Upload PDF Files", type=["pdf"], accept_multiple_files=True
        )

        st.divider()

        st.markdown("#### ⚙️ Batch Splitting Options")
        max_pages_per_file = st.number_input(
            "Maximum Target Pages Per PDF File:",
            min_value=1,
            max_value=10000,
            value=50,
            step=5,
            help="To fit multiple stores into one PDF, set this equal to or higher than their combined total pages.",
        )

        st.divider()

        if st.button("Generate Master PDF(s)", type="primary"):
            if not uploaded_pdfs:
                st.error("Please upload the target PDF files.")
            else:
                with st.spinner(
                    "Analyzing document sizes and organizing batches..."
                ):
                    pdf_dict = {
                        pdf_file.name.lower(): pdf_file
                        for pdf_file in uploaded_pdfs
                    }
                    excel_basename = os.path.splitext(uploaded_excel.name)[0]

                    if not file_columns:
                        file_columns = [
                            c
                            for c in all_columns
                            if c not in selected_metadata_cols
                        ]

                    store_data_list = []
                    max_single_store_pages = 0
                    grand_total_pages = 0

                    for index, row in df_control.iterrows():
                        metadata_dict = {
                            col: row[col]
                            for col in selected_metadata_cols
                            if col in row
                        }

                        content_page_count = 0
                        valid_files_to_add = []
                        detected_width = 612
                        detected_height = 792

                        for file_name in file_columns:
                            qty_value = row[file_name]

                            if pd.notna(qty_value):
                                try:
                                    qty = int(qty_value)
                                except ValueError:
                                    continue

                                if qty > 0:
                                    pdf_key = str(file_name).strip().lower()
                                    if not pdf_key.endswith(".pdf"):
                                        pdf_key += ".pdf"

                                    if pdf_key in pdf_dict:
                                        pdf_file_obj = pdf_dict[pdf_key]
                                        pdf_file_obj.seek(0)
                                        reader = PdfReader(pdf_file_obj)

                                        if reader.pages:
                                            first_page = reader.pages[0]
                                            detected_width = float(
                                                first_page.mediabox.width
                                            )
                                            detected_height = float(
                                                first_page.mediabox.height
                                            )

                                        pages_in_file = len(reader.pages)
                                        content_page_count += (
                                            pages_in_file * qty
                                        )
                                        valid_files_to_add.append(
                                            (pdf_file_obj, qty)
                                        )
                                    else:
                                        st.warning(
                                            f"File '{pdf_key}' referenced in sheet was not uploaded."
                                        )

                        total_store_pages = 1 + content_page_count
                        grand_total_pages += total_store_pages

                        if total_store_pages > max_single_store_pages:
                            max_single_store_pages = total_store_pages

                        store_data_list.append(
                            {
                                "metadata": metadata_dict,
                                "total_pages": total_store_pages,
                                "files": valid_files_to_add,
                                "width": detected_width,
                                "height": detected_height,
                            }
                        )

                    st.info(
                        f"📊 **Total pages across all stores:** {grand_total_pages} pages "
                        f"(Largest single store requires {max_single_store_pages} pages)."
                    )

                    if max_pages_per_file < max_single_store_pages:
                        st.warning(
                            f"⚠️ **Limit adjusted:** The largest store needs **{max_single_store_pages} pages**. "
                            f"The limit was raised to {max_single_store_pages} to keep each store complete."
                        )
                        effective_max = max(
                            max_pages_per_file, max_single_store_pages
                        )
                    else:
                        effective_max = max_pages_per_file

                    batches = []
                    current_batch = []
                    current_batch_page_count = 0

                    for store in store_data_list:
                        if (
                            current_batch_page_count + store["total_pages"]
                            > effective_max
                            and current_batch
                        ):
                            batches.append(current_batch)
                            current_batch = []
                            current_batch_page_count = 0

                        current_batch.append(store)
                        current_batch_page_count += store["total_pages"]

                    if current_batch:
                        batches.append(current_batch)

                    total_batches = len(batches)
                    generated_files = []

                    for batch_idx, batch_stores in enumerate(
                        batches, start=1
                    ):
                        pdf_writer = PdfWriter()

                        for store in batch_stores:
                            header_pdf = create_header_pdf(
                                store["metadata"],
                                store["total_pages"],
                                page_width=store["width"],
                                page_height=store["height"],
                            )
                            pdf_writer.add_page(header_pdf.pages[0])

                            for pdf_file_obj, qty in store["files"]:
                                pdf_file_obj.seek(0)
                                reader = PdfReader(pdf_file_obj)
                                for _ in range(qty):
                                    for page in reader.pages:
                                        pdf_writer.add_page(page)

                        buf = io.BytesIO()
                        pdf_writer.write(buf)
                        buf.seek(0)

                        batch_filename = f"{excel_basename}_Consolidated_Batch_{batch_idx}_of_{total_batches}.pdf"
                        generated_files.append(
                            (batch_filename, buf.getvalue())
                        )

                    st.success(
                        f"Processing complete! Generated {total_batches} batch file(s)."
                    )

                    if total_batches == 1:
                        filename, file_bytes = generated_files[0]
                        st.download_button(
                            label=f"⬇️ Download {filename}",
                            data=file_bytes,
                            file_name=filename,
                            mime="application/pdf",
                        )
                    else:
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(
                            zip_buffer, "w", zipfile.ZIP_DEFLATED
                        ) as zip_file:
                            for fname, fbytes in generated_files:
                                zip_file.writestr(fname, fbytes)

                        zip_buffer.seek(0)
                        zip_filename = f"{excel_basename}_All_Batches.zip"

                        st.download_button(
                            label=f"⬇️ Download All {total_batches} Batches (ZIP Archive)",
                            data=zip_buffer,
                            file_name=zip_filename,
                            mime="application/zip",
                        )

# ---------------------------------------------------------
# PAGE 4: BATCHES & LABELS
# ---------------------------------------------------------
elif st.session_state.current_page == "batches_and_labels":
    st.subheader("🏷️ Batches & Labels Dashboard")

    # ONE unified navigation panel layout with explicit tracking keys
    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        if st.button("🏷️ Batch Headers", use_container_width=True, key="nav_btn_headers"): 
            st.session_state.batches_subtab = "batch_headers"
    with sub_col2:
        if st.button("🖨️ Print Labels", use_container_width=True, key="nav_btn_labels"): 
            st.session_state.batches_subtab = "print_labels"
    with sub_col3:
        if st.button("📁 Print from File", use_container_width=True, key="nav_btn_file"): 
            st.session_state.batches_subtab = "print_from_file"

    st.divider()

    # --- SUBTAB 1: BATCH HEADERS ---
    if st.session_state.batches_subtab == "batch_headers":

        st.markdown("### 🏷️ Batch Headers Generator")
        st.write(
            "Generate print header sheets or outside work pallet labels with custom parameters."
        )

        is_outside_work = st.checkbox(
            "Create Outside Work Label?",
            value=False,
            help="Check this box to format as an Outside Work Pallet Label sheet.",
        )

        if is_outside_work:
            st.markdown("#### 📦 Outside Work Label Details")
            col1, col2 = st.columns(2)
            with col1:
                supplier = st.text_input("Supplier:", value="")
                job_no = st.text_input("Job No:", value="1615699")
                client = st.text_input("Client:", value="Precision Mail Pty Ltd")
            with col2:
                job_title = st.text_input(
                    "Job Title:", value="Rase Spares Scratchys"
                )
                qty_this_pallet = st.text_input(
                    "Qty this Pallet:", value="1025"
                )
                total_pallets = st.number_input(
                    "Total Pallets (Number of Pages):",
                    min_value=1,
                    max_value=1000,
                    value=1,
                    step=1,
                )

            auto_number_pallets = st.checkbox(
                "Include Total Pallet Count (e.g. '1 of 5')?",
                value=True,
                help="If checked, displays '1 of 5'. If unchecked, leaves it blank as '1 of ______'.",
            )

            st.divider()

            if st.button("Generate Outside Work Label PDF", type="primary"):
                with st.spinner("Generating Outside Work Label PDF..."):
                    pdf_bytes = create_outside_work_label_file(
                        supplier=supplier,
                        job_no=job_no,
                        client=client,
                        job_title=job_title,
                        qty_this_pallet=qty_this_pallet,
                        total_pallets=int(total_pallets),
                        auto_number_pallets=auto_number_pallets,
                    )

                    out_filename = f"{job_no}_Outside_Work_Label.pdf"

                    st.success("Outside Work Label generated successfully!")
                    st.download_button(
                        label=f"⬇️ Download {out_filename}",
                        data=pdf_bytes,
                        file_name=out_filename,
                        mime="application/pdf",
                    )
        else:
            col1, col2 = st.columns(2)
            with col1:
                job_no = st.text_input("Job No.:", value="054520")
            with col2:
                description = st.text_input(
                    "Description:", value="Fragrance Wk5-6"
                )

            col3, col4 = st.columns(2)
            with col3:
                side_margin = st.number_input(
                    "Side Margin (pt):",
                    min_value=0,
                    max_value=200,
                    value=50,
                    step=5,
                    help="Left and right margin padding for the description text.",
                )
            with col4:
                total_batches = st.number_input(
                    "Total Batches (Number of Pages):",
                    min_value=1,
                    max_value=1000,
                    value=20,
                    step=1,
                )

            auto_number = st.checkbox(
                "Include Total Count (e.g. '1 OF 20')?",
                value=True,
                help="If checked, numbers each page as '1 OF 20', '2 OF 20'. If unchecked, prints '1 OF ______' for manual entry.",
            )

            st.divider()

            if st.button("Generate Batch Headers PDF", type="primary"):
                with st.spinner("Generating batch header sheets..."):
                    pdf_bytes = create_batch_header_file(
                        job_no=job_no,
                        description=description,
                        total_batches=int(total_batches),
                        auto_number=auto_number,
                        side_margin=int(side_margin),
                    )

                    out_filename = f"{job_no}_Batch_Headers.pdf"

                    st.success("Batch headers generated successfully!")
                    st.download_button(
                        label=f"⬇️ Download {out_filename}",
                        data=pdf_bytes,
                        file_name=out_filename,
                        mime="application/pdf",
                    )

       # --- SUBTAB 2: PRINT LABELS ---
    elif st.session_state.batches_subtab == "print_labels":
        st.markdown("### 🖨️ Print Labels Generator")
        st.write(
            "Design customized label content and impose them automatically on A4 pages."
        )

        st.markdown("#### 1. Page Layout & Label Dimensions (mm)")
        col_grid1, col_grid2 = st.columns(2)
        with col_grid1:
            rows = st.number_input(
                "Rows per A4 Page:", min_value=1, max_value=20, value=7, step=1
            )
            cols = st.number_input(
                "Columns per A4 Page:",
                min_value=1,
                max_value=10,
                value=2,
                step=1,
            )
            label_w_mm = st.number_input(
                "Label Width (mm):",
                min_value=10.0,
                max_value=210.0,
                value=99.1,
                step=0.5,
            )
            label_h_mm = st.number_input(
                "Label Height (mm):",
                min_value=10.0,
                max_value=297.0,
                value=38.1,
                step=0.5,
            )

        with col_grid2:
            gutter_x_mm = st.number_input(
                "Horizontal Gutter (mm):",
                min_value=0.0,
                max_value=50.0,
                value=2.5,
                step=0.5,
            )
            gutter_y_mm = st.number_input(
                "Vertical Gutter (mm):",
                min_value=0.0,
                max_value=50.0,
                value=0.0,
                step=0.5,
            )
            margin_x_mm = st.number_input(
                "Page Side Margin (mm):",
                min_value=0.0,
                max_value=50.0,
                value=4.5,
                step=0.5,
            )
            margin_y_mm = st.number_input(
                "Page Top Margin (mm):",
                min_value=0.0,
                max_value=50.0,
                value=15.0,
                step=0.5,
            )

        st.divider()

        st.markdown("#### 2. Label Master Content & Quantity")
        num_lines = st.number_input(
            "Number of Text Lines per Label:",
            min_value=1,
            max_value=10,
            value=2,
            step=1,
        )

        # 1. Setup Master Baseline Configuration
        master_lines = []
        st.markdown("##### 🖋️ Configure Master Baseline Values")
        for i in range(int(num_lines)):
            l_col1, l_col2, l_col3 = st.columns([3, 1, 1])
            with l_col1:
                m_text = st.text_input(
                    f"Line {i+1} Master Text:",
                    value=f"Sample Text {i+1}",
                    key=f"master_text_{i}",
                )
            with l_col2:
                m_sz = st.number_input(
                    f"Line {i+1} Master Size:",
                    min_value=6,
                    max_value=72,
                    value=12,
                    step=1,
                    key=f"master_size_{i}",
                )
            with l_col3:
                m_bld = st.checkbox(
                    "Bold", value=(i == 0), key=f"master_bold_{i}"
                )
            master_lines.append({"text": m_text, "font_size": m_sz, "bold": m_bld})

        st.divider()
        st.markdown("#### 3. Batch Break Segment Control Matrix")
        
        num_breaks = st.number_input(
            "Number of Breaks / Batch Segments:",
            min_value=1,
            max_value=100,
            value=1,
            step=1,
        )

        breaks_configs = []
        running_label_counter = 1

        # 2. Iterate and render flexible card modules per batch break group
        for b in range(int(num_breaks)):
            st.markdown(f"---")
            st.markdown(f"##### 📦 Batch Segment Group Block #{b+1}")
            
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                b_labels_count = st.number_input(
                    f"Total Labels for Batch #{b+1}:",
                    min_value=1, value=14, step=1, key=f"b_count_{b}"
                )
            with col_b2:
                include_num = st.checkbox(
                    "Include Sequence Counter?", value=True, key=f"b_inc_num_{b}"
                )
            with col_b3:
                r_num_mode = st.radio(
                    f"Sequence Slicing Logic:",
                    ["Continue from previous batch", "Restart from new number"],
                    key=f"b_mode_{b}"
                )

            # Explicit sequence constraints allocation
            start_num = running_label_counter
            end_num = running_label_counter + b_labels_count - 1
            
            if r_num_mode == "Restart from new number":
                nc1, nc2 = st.columns(2)
                with nc1:
                    start_num = st.number_input(
                        "Start Number Overwrite:", min_value=1, value=1, key=f"b_start_{b}"
                    )
                with nc2:
                    end_num = st.number_input(
                        "End Number (Denominator limit):", min_value=1, value=14, key=f"b_end_{b}"
                    )

            b_final_lines = []
            st.markdown(f"⚙️ **Line Content Overrides for Batch #{b+1}:**")
            
            for i in range(int(num_lines)):
                cc1, cc2 = st.columns([2, 3])
                with cc1:
                    stay_same = st.checkbox(
                        "Stay Same / Inherit", value=True, key=f"b_same_{b}_{i}"
                    )
                with cc2:
                    if stay_same:
                        st.caption(f"Inherited: *\"{master_lines[i]['text']}\"*")
                        line_txt = master_lines[i]["text"]
                    else:
                        line_txt = st.text_input(
                            f"Modify Line {i+1} Text:",
                            value=master_lines[i]["text"],
                            key=f"b_text_override_{b}_{i}"
                        )
                
                b_final_lines.append({
                    "text": line_txt,
                    "font_size": master_lines[i]["font_size"],
                    "bold": master_lines[i]["bold"]
                })

                        # Save sequential tracker step updates
            running_label_counter += int(b_labels_count)

            # --- This block must break out of the batch loop but remain in the loop's parent tier ---
            breaks_configs.append({
                "count": int(b_labels_count),
                "include_numbering": include_num,
                "num_mode": r_num_mode,
                "start_num": int(start_num),
                "end_num": int(end_num),
                "lines": b_final_lines,
                "total_labels_global": int(b_labels_count)
            })

        st.divider()

        col_qty1, col_qty2 = st.columns(2)
        with col_qty1:
            total_labels = st.number_input(
                "Total Labels to Print:",
                min_value=1,
                max_value=10000,
                value=14,
                step=1,
            )
        with col_qty2:
            include_num = st.checkbox(
                "Include Sequential Label Count (e.g. '1 of 14')?",
                value=True,
            )

        if st.button("Generate Imposed Labels PDF", type="primary"):
            with st.spinner("Generating labels layout..."):
                mm_to_pt = 2.83465
                
                # Build default block properties if a dynamic page reload clears structural values
                if ('breaks_configs' not in locals()) or (not breaks_configs):
                    breaks_configs = [{
                        "count": int(total_labels) if 'total_labels' in locals() else 14,
                        "include_numbering": include_num if 'include_num' in locals() else True,
                        "num_mode": "Restart from new number",
                        "start_num": 1,
                        "end_num": int(total_labels) if 'total_labels' in locals() else 14,
                        "lines": lines_config if 'lines_config' in locals() else [],
                        "total_labels_global": int(total_labels) if 'total_labels' in locals() else 14
                    }]

                total_global_sum = sum(item.get("count", 0) for item in breaks_configs)
                for item in breaks_configs:
                    if item.get("num_mode") == "Continue from previous batch":
                        item["total_labels_global"] = total_global_sum

                active_lines = lines_config if 'lines_config' in locals() else []
                active_num = include_num if 'include_num' in locals() else True

                pdf_buffer = create_labels_pdf(
                    rows=int(rows),
                    cols=int(cols),
                    label_w_pt=label_w_mm * mm_to_pt,
                    label_h_pt=label_h_mm * mm_to_pt,
                    gutter_x_pt=gutter_x_mm * mm_to_pt,
                    gutter_y_pt=gutter_y_mm * mm_to_pt,
                    margin_x_pt=margin_x_mm * mm_to_pt,
                    margin_y_pt=margin_y_mm * mm_to_pt,
                    lines_config=active_lines,
                    total_labels=int(total_global_sum),
                    include_numbering=active_num,
                    breaks_configs=breaks_configs,
                )

                if hasattr(pdf_buffer, "getvalue"):
                    pdf_bytes = pdf_buffer.getvalue()
                else:
                    pdf_bytes = pdf_buffer

                out_filename = "Imposed_Labels_Output.pdf"
                
                if len(pdf_bytes) > 100:
                    st.success("Label sheet generated successfully!")
                    st.download_button(
                        label=f"⬇ Download {out_filename}",
                        data=pdf_bytes,
                        file_name=out_filename,
                        mime="application/pdf",
                    )
                else:
                    st.error("Error: Generated PDF is empty. Check batch counts.")
    # --- EXPAND NAVIGATION HUB TO 3 DISTINCT PANEL COLUMNS ---
    sub_col1, sub_col2, sub_col3 = st.columns(3)
    with sub_col1:
        if st.button("🏷️ Batch Headers", use_container_width=True): 
            st.session_state.batches_subtab = "batch_headers"
    with sub_col2:
        if st.button("🖨️ Print Labels", use_container_width=True): 
            st.session_state.batches_subtab = "print_labels"
    with sub_col3:
        if st.button("📁 Print from File", use_container_width=True): 
            st.session_state.batches_subtab = "print_from_file"

    st.divider()

    # --- SUBTAB 3: PRINT FROM FILE & REPEAT OVERWRITES ---
    if st.session_state.batches_subtab == "print_from_file":
        st.markdown("### 📁 Print Labels From Data File")
        st.write("Extract spreadsheet cell metrics dynamically onto standard A4 labels with custom constraints.")

        # Core logic switch between parsing file records vs generating manual repeat labels
        data_mode = st.radio(
            "Select Processing Engine Mode:",
            ["Use Excel Data Source File", "Repeat Manual Entry Override Mode"],
            horizontal=True,
            help="Excel mode reads your spreadsheet rows. Repeat Manual mode clones a single custom label completely N times."
        )

        df_labels = None
        columns_list = []

        if data_mode == "Use Excel Data Source File":
            uploaded_data = st.file_uploader("Upload Excel Data Sheet", type=["xlsx", "xls"], key="label_data_uploader")
            if uploaded_data:
                df_labels = pd.read_excel(uploaded_data)
                columns_list = [str(c) for c in df_labels.columns]
                st.success(f"Successfully tracked data source file with **{len(df_labels)} rows** available.")
        else:
            st.info("Manual Clone Mode Active. Map your constant data items manually below.")

        st.divider()
        st.markdown("#### 1. Page Layout & Label Dimensions (mm)")
        col_grid1, col_grid2 = st.columns(2)
        with col_grid1:
            rows = st.number_input("Rows per A4 Page:", min_value=1, max_value=20, value=7, key="file_rows")
            cols = st.number_input("Columns per A4 Page:", min_value=1, max_value=10, value=2, key="file_cols")
            label_w_mm = st.number_input("Label Width (mm):", min_value=10.0, value=99.1, key="file_w")
            label_h_mm = st.number_input("Label Height (mm):", min_value=10.0, value=38.1, key="file_h")
        with col_grid2:
            gutter_x_mm = st.number_input("Horizontal Gutter (mm):", min_value=0.0, value=2.5, key="file_gx")
            gutter_y_mm = st.number_input("Vertical Gutter (mm):", min_value=0.0, value=0.0, key="file_gy")
            margin_x_mm = st.number_input("Page Side Margin (mm):", min_value=0.0, value=4.5, key="file_mx")
            margin_y_mm = st.number_input("Page Top Margin (mm):", min_value=0.0, value=15.0, key="file_my")
        st.divider()
        st.markdown("#### 2. Label Content Structure & Column Mapping Matrix")
        num_lines = st.number_input("Number of Text Lines per Label:", min_value=1, max_value=10, value=2, key="file_num_lines")

        line_mappings = []
        for i in range(int(num_lines)):
            st.markdown(f"**🖋️ Text Line Block Configuration #{i+1}**")
            l_col1, l_col2, l_col3, l_col4 = st.columns([2, 3, 1, 1])
            
            with l_col1:
                source_type = st.radio(
                    f"Line {i+1} Data Source:",
                    ["Manual Entry Only", "Excel Column Header Bind"],
                    index=0 if data_mode == "Repeat Manual Entry Override Mode" else 1,
                    disabled=(data_mode == "Repeat Manual Entry Override Mode"),
                    key=f"src_type_{i}"
                )
            
            with l_col2:
                bound_col = None
                manual_text = ""
                if source_type == "Excel Column Header Bind" and columns_list:
                    bound_col = st.selectbox(f"Bind Column Header:", columns_list, key=f"bind_col_{i}")
                    manual_text = st.text_input(f"Append Prefix/Suffix Text:", value="", key=f"append_txt_{i}", help="Optional wording attached alongside data cell strings.")
                else:
                    manual_text = st.text_input(f"Enter Static Text String:", value=f"Sample Text {i+1}", key=f"manual_txt_{i}")
            
            with l_col3:
                line_sz = st.number_input(f"Font Size:", min_value=6, max_value=72, value=12, key=f"file_sz_{i}")
            with l_col4:
                line_bld = st.checkbox("Bold Text", value=(i == 0), key=f"file_bld_{i}")
                
            line_mappings.append({
                "type": source_type,
                "column": bound_col,
                "text": manual_text,
                "font_size": line_sz,
                "bold": line_bld
            })

        st.divider()
        st.markdown("#### 3. Row Limit Strategy & Sequencing Safeguards")
        
        if data_mode == "Use Excel Data Source File":
            row_strategy = st.radio("Rows Execution Scope Limits:", ["Process All Rows Found", "Limit to Specific Row Count Limit"], horizontal=True)
            max_rows_to_process = len(df_labels) if df_labels is not None else 0
            if row_strategy == "Limit to Specific Row Count Limit":
                max_rows_to_process = st.number_input("Process up to how many spreadsheet data rows?", min_value=1, max_value=max(1, max_rows_to_process), value=min(10, max(1, max_rows_to_process)))
        else:
            total_clones_needed = st.number_input("Total Repeated Labels to Generate:", min_value=1, max_value=10000, value=30)

        col_seq1, col_seq2, col_seq3 = st.columns(3)
        with col_seq1:
            append_sequence_counter = st.checkbox("Include Index Counter Footer? (e.g. '1 of 30')", value=False)
        with col_seq2:
            start_seq_num = st.number_input("Counter Start Index Overwrite:", min_value=1, value=1, disabled=not append_sequence_counter)
        with col_seq3:
            custom_denominator = st.checkbox("Use Custom Total Max Denominator Value?", value=False, disabled=not append_sequence_counter)
            end_seq_num = st.number_input("Custom Denominator Limit Bounds Value:", min_value=1, value=30, disabled=(not append_sequence_counter or not custom_denominator))

               # 4. Engine Processing Execution Block
        if st.button("Generate Imposed Data Labels PDF", type="primary"):
            if data_mode == "Use Excel Data Source File" and df_labels is None:
                st.error("Error: Please upload a valid Excel control data file first.")
            else:
                with st.spinner("Compiling structural label fields layout page grids..."):
                    processed_breaks_configs = []
                    
                    # --- SAFE FALLBACK ENGINE CHECK ---
                    # Ensures variables exist even if layout blocks didn't render completely
                    safe_rows = int(rows) if 'rows' in locals() and rows else 7
                    safe_cols = int(cols) if 'cols' in locals() and cols else 2
                    safe_w = float(label_w_mm) if 'label_w_mm' in locals() and label_w_mm else 99.1
                    safe_h = float(label_h_mm) if 'label_h_mm' in locals() and label_h_mm else 38.1
                    safe_gx = float(gutter_x_mm) if 'gutter_x_mm' in locals() and gutter_x_mm else 2.5
                    safe_gy = float(gutter_y_mm) if 'gutter_y_mm' in locals() and gutter_y_mm else 0.0
                    safe_mx = float(margin_x_mm) if 'margin_x_mm' in locals() and margin_x_mm else 4.5
                    safe_my = float(margin_y_mm) if 'margin_y_mm' in locals() and margin_y_mm else 15.0

                    if data_mode == "Use Excel Data Source File":
                        loop_range = int(max_rows_to_process)
                        for r_idx in range(loop_range):
                            row_data = df_labels.iloc[r_idx]
                            row_lines = []
                            for mapping in line_mappings:
                                if mapping["type"] == "Excel Column Header Bind" and mapping["column"] is not None:
                                    cell_val = row_data[mapping["column"]]
                                    cell_str = "" if pd.isna(cell_val) else str(cell_val)
                                    final_line_str = f"{mapping['text']} {cell_str}".strip() if mapping["text"] else cell_str
                                else:
                                    final_line_str = mapping["text"]
                                    
                                row_lines.append({
                                    "text": final_line_str,
                                    "font_size": mapping["font_size"],
                                    "bold": mapping["bold"]
                                })
                            
                            processed_breaks_configs.append({
                                "count": 1,
                                "include_numbering": append_sequence_counter,
                                "num_mode": "Restart from new number" if custom_denominator else "Continue from previous batch",
                                "start_num": int(start_seq_num + r_idx),
                                "end_num": int(end_seq_num) if custom_denominator else int(loop_range),
                                "lines": row_lines,
                                "total_labels_global": int(loop_range)
                            })
                    else:
                        clone_lines = []
                        for mapping in line_mappings:
                            clone_lines.append({
                                "text": mapping["text"],
                                "font_size": mapping["font_size"],
                                "bold": mapping["bold"]
                            })
                        
                        processed_breaks_configs.append({
                            "count": int(total_clones_needed),
                            "include_numbering": append_sequence_counter,
                            "num_mode": "Restart from new number" if custom_denominator else "Continue from previous batch",
                            "start_num": int(start_seq_num),
                            "end_num": int(end_seq_num) if custom_denominator else int(total_clones_needed),
                            "lines": clone_lines,
                            "total_labels_global": int(total_clones_needed)
                        })

                    mm_to_pt = 2.83465
                    total_calculated_sum = sum(item.get("count", 0) for item in processed_breaks_configs)
                    
                    # --- UPDATED GENERATOR FUNCTION TO USE SAFE VARIABLES ---
                    pdf_buffer = create_labels_pdf(
                        rows=safe_rows, 
                        cols=safe_cols,
                        label_w_pt=safe_w * mm_to_pt, 
                        label_h_pt=safe_h * mm_to_pt,
                        gutter_x_pt=safe_gx * mm_to_pt, 
                        gutter_y_pt=safe_gy * mm_to_pt,
                        margin_x_pt=safe_mx * mm_to_pt, 
                        margin_y_pt=safe_my * mm_to_pt,
                        total_labels=int(total_calculated_sum), 
                        breaks_configs=processed_breaks_configs
                    )

                    pdf_bytes = pdf_buffer.getvalue() if hasattr(pdf_buffer, "getvalue") else pdf_buffer
                    
                    if len(pdf_bytes) > 100:
                        st.success(f"Successfully generated **{total_calculated_sum} labels**!")
                        st.download_button(label="⬇ Download Imposed_Data_Labels_Output.pdf", data=pdf_bytes, file_name="Imposed_Data_Labels_Output.pdf", mime="application/pdf")
                    else:
                        st.error("Error generating label document matrix. Review parameters.")

# ---------------------------------------------------------
# PAGE 5: GENERAL SETTINGS
# ---------------------------------------------------------
elif st.session_state.current_page == "general":
    st.subheader("⚙️ General Settings")
    st.write("Configure application parameters and system defaults.")
    st.info("System operational. All dependencies loaded.")
