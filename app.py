import io
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
    page_title="Custom Label & Batch Management Suite", page_icon="🛠️", layout="wide"
)

# -------------------------------------------------------------------------
# CORE ENGINE: PDF DRAWING RENDERING LOGIC WITH OVERRIDES
# -------------------------------------------------------------------------

def create_outside_work_label_page(
    can,
    page_width,
    page_height,
    supplier,
    job_no,
    client,
    job_title,
    qty_this_pallet,
    current_idx,
    total_idx,
):
    """Draws a single Outside Work Label page on the passed canvas."""
    cyan_bg = HexColor("#00AEEF")
    dark_frame = HexColor("#1A1A1A")
    text_dark = HexColor("#1A1A1A")

    # 80mm top clearance conversion (1 mm = ~2.83465 points)
    top_clearance_pt = 80 * 2.83465

    # 1. Fill Page Background
    can.setFillColor(cyan_bg)
    can.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    # 2. Outer Chamfered Border Frame
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

    # 3. Top Header Content
    can.setFillColor(text_dark)
    can.setFont("Helvetica-Bold", 11)
    can.drawString(margin_x + 20, frame_top_y - 40, "From:")
    can.setFont("Helvetica-Bold", 14)
    can.drawString(margin_x + 20, frame_top_y - 58, "IVE Print")
    can.setFont("Helvetica", 11)
    can.drawString(margin_x + 20, frame_top_y - 74, "24-36 Beyer Rd, Braeside")
    can.drawString(margin_x + 20, frame_top_y - 88, "Victoria 3195")

    # Top Right Brand Label
    can.setFont("Helvetica-Bold", 46)
    can.drawRightString(page_width - margin_x - 25, frame_top_y - 70, "ive")

    # 4. Banner: "OUTSIDE WORK"
    banner_y, banner_h = frame_top_y - 260, 160
    can.setFillColor(dark_frame)
    can.rect(margin_x, banner_y, page_width - (margin_x * 2), banner_h, fill=1, stroke=0)

    can.setFillColor(HexColor("#FFFFFF"))
    can.setFont("Helvetica-Bold", 80)
    can.drawCentredString(page_width / 2.0, banner_y + 92, "OUTSIDE")
    can.drawCentredString(page_width / 2.0, banner_y + 32, "WORK")

    # 5. Form Fields with Layout Baselines
    fields = [
        ("Supplier:", supplier),
        ("Job No:", job_no),
        ("Client:", client),
        ("Job Title:", job_title),
        ("Qty this pallet:", qty_this_pallet),
        ("Pallet Number:", f"{current_idx} OF {total_idx}"),
    ]

    y_start, line_gap = banner_y - 38, 36
    can.setFillColor(text_dark)

    for idx, (label, val) in enumerate(fields):
        curr_y = y_start - (idx * line_gap)
        can.setFont("Helvetica", 15)
        can.drawString(margin_x + 20, curr_y, label)

        label_width = can.stringWidth(label, "Helvetica", 15)
        dots_x_start = margin_x + 25 + label_width

        if val:
            can.setFont("Helvetica-Bold", 18)
            can.drawString(dots_x_start + 10, curr_y, str(val))

        can.setStrokeColor(dark_frame)
        can.setLineWidth(1)
        can.setDash([1, 3], 0)
        can.line(dots_x_start, curr_y - 2, page_width - margin_x - 20, curr_y - 2)

    can.showPage()


# -------------------------------------------------------------------------
# INTERACTIVE DATA PROCESSING ENGINE
# -------------------------------------------------------------------------

def generate_ranged_labels(base_data, range_configs):
    """Parses range matrix configurations to build custom, segmented sequence labels."""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    page_width, page_height = A4
    
    global_running_num = 1
    
    for r_idx, cfg in enumerate(range_configs):
        start_box = cfg["start"]
        end_box = cfg["end"]
        qty_override = cfg["qty"]
        num_mode = cfg["num_mode"]
        denom_mode = cfg["denom_mode"]
        custom_title = cfg["title"] if cfg["title"] else base_data["job_title"]
        
        range_size = (end_box - start_box) + 1
        
        for local_step in range(range_size):
            # Calculate Current Box Number Display
            if num_mode == "Restart from 1":
                display_current = local_step + 1
            else:  # "Continue Sequence"
                display_current = global_running_num
                
            # Calculate Total Box Denominator Display
            if denom_mode == "Range Size":
                display_total = range_size
            else:  # "Global Total"
                display_total = base_data["total_boxes"]
                
            # Run Canvas Paint Sequence
            create_outside_work_label_page(
                can,
                page_width,
                page_height,
                supplier=base_data["supplier"],
                job_no=base_data["job_no"],
                client=base_data["client"],
                job_title=custom_title,
                qty_this_pallet=qty_override,
                current_idx=display_current,
                total_idx=display_total,
            )
            
            global_running_num += 1
            
    can.save()
    packet.seek(0)
    return packet


# -------------------------------------------------------------------------
# STREAMLIT USER INTERFACE APPLICATION
# -------------------------------------------------------------------------

st.title("📦 Variable Range Label Generator")
st.markdown("Specify global job values, partition quantities into sub-ranges, and toggle custom item tracking numbers below.")

# Global Setup Controls
with st.sidebar.form("global_form"):
    st.subheader("1. Global Properties")
    supplier = st.text_input("Supplier Name", value="IVE Group")
    job_no = st.text_input("Job Number", value="240822")
    client = st.text_input("Client Name", value="Corporate Direct")
    job_title = st.text_input("Default Item/Job Title", value="Product Marketing Catalogues")
    total_boxes = st.number_input("Total Output Run Volume (Boxes/Pallets)", min_value=1, value=50, step=1)
    
    submit_globals = st.form_submit_button("Lock Base Configuration")

base_data = {
    "supplier": supplier,
    "job_no": job_no,
    "client": client,
    "job_title": job_title,
    "total_boxes": total_boxes
}

st.subheader("2. Sub-Range Interval Multi-Matrix Manager")
st.info(f"Distribute properties dynamically across your targeted total of **{total_boxes}** units.")

# Initialize dynamic range tracking array state
if "range_count" not in st.session_state:
    st.session_state.range_count = 1

col_btns_1, col_btns_2 = st.columns(2)
with col_btns_1:
    if st.button("➕ Append Sub-Range Segment"):
        st.session_state.range_count += 1
with col_btns_2:
    if st.button("❌ Remove Last Segment") and st.session_state.range_count > 1:
        st.session_state.range_count -= 1

range_configs = []
current_auto_start = 1

# Render flexible card options grid per user sub-range specification
for i in range(st.session_state.range_count):
    st.markdown(f"---")
    st.markdown(f"#### 🏷️ Interval Matrix Segment #{i+1}")
    
    c1, c2, c3, c4 = st.columns([1, 1, 1.5, 2.5])
    
    with c1:
        rng_start = st.number_input(f"Start Index", min_value=1, max_value=total_boxes, value=min(current_auto_start, total_boxes), key=f"start_{i}")
    with c2:
        default_end = min(rng_start + 9, total_boxes)
        rng_end = st.number_input(f"End Index", min_value=int(rng_start), max_value=total_boxes, value=int(default_end), key=f"end_{i}")
    with c3:
        rng_qty = st.text_input(f"Pack Quantity Override", value="100", key=f"qty_{i}")
    with c4:
        rng_title = st.text_input(f"Item/Job Title Override (Optional)", placeholder="Leave blank to use default", key=f"title_{i}")
        
    c5, c6 = st.columns(2)
    with c5:
        rng_num_mode = st.radio(
            "Numerical Counter Indexing Sequence Strategy",
            ["Continue Sequence", "Restart from 1"],
            key=f"num_mode_{i}",
            help="Choose whether the counter continues running sequentially from previous tiers or restarts from 1."
        )
    with c6:
        rng_denom_mode = st.radio(
            "Denominator/Total Count Format Type",
            ["Global Total", "Range Size"],
            key=f"denom_mode_{i}",
            help="Determines if the total counter matches your global total box layout configuration or just the batch group count sizing."
        )
        
    # Append structured config details to map engine parsing pipeline arrays
    range_configs.append({
        "start": int(rng_start),
        "end": int(rng_end),
        "qty": rng_qty,
        "title": rng_title,
        "num_mode": rng_num_mode,
        "denom_mode": rng_denom_mode
    })
    
    current_auto_start = int(rng_end) + 1

# Verification layer mapping
st.markdown("---")
st.subheader("3. Execution Output Pipeline")

# Validating index gaps to catch layout overlaps
coverage_errors = []
covered_markers = set()
for index, item in enumerate(range_configs):
    for val in range(item["start"], item["end"] + 1):
        if val in covered_markers:
            coverage_errors.append(f"Overlap detected: Unit block indicator '{val}' is double-mapped inside multiple configuration modules.")
