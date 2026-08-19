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
    page_title="PDF Toolsuite Dashboard", page_icon="🛠️", layout="centered"
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


# Upgraded Outside Work Label generator handling multi-range segmentation matrices cleanly
def create_outside_work_label_ranged_file(
    supplier, job_no, client, default_title, total_pallets, range_configs
):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    page_width, page_height = A4

    cyan_bg = HexColor("#00AEEF")
    dark_frame = HexColor("#1A1A1A")
    text_dark = HexColor("#1A1A1A")
    top_clearance_pt = 80 * 2.83465

    global_counter = 1

    # Loop through each custom partitioned user sub-range block matrix
    for r_idx, cfg in enumerate(range_configs):
        st_val = cfg["start"]
        en_val = cfg["end"]
        qty_val = cfg["qty"]
        title_val = cfg["title"] if cfg["title"] else default_title
        num_mode = cfg["num_mode"]
        denom_mode = cfg["denom_mode"]

        range_total_size = (en_val - st_val) + 1

        for step in range(range_total_size):
            # Calculate current running pallet number text string
            if num_mode == "Start from beginning (1)":
                display_current = step + 1
            else:
                display_current = global_counter

            # Calculate base denominator limit text string
            if denom_mode == "Range size limit":
                display_total = range_total_size
            else:
                display_total = total_pallets

            # 1. Fill Page Background (Bright Cyan/Blue)
            can.setFillColor(cyan_bg)
            can.rect(0, 0, page_width, page_height, fill=1, stroke=0)

            # 2. Outer Chamfered Border Frame
            margin_x, margin_bottom, corner_cut = 35, 35, 25
            frame_top_y = page_height - top_clearance_pt

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

            # 3. Top Section: From Address & Logo
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

            # 4. Dark Block Banner: "OUTSIDE WORK"
            banner_y, banner_h = frame_top_y - 260, 160
            can.setFillColor(dark_frame)
            can.rect(margin_x, banner_y, page_width - (margin_x * 2), banner_h, fill=1, stroke=0)

            can.setFillColor(HexColor("#FFFFFF"))
            can.setFont("Helvetica-Bold", 80)
            can.drawCentredString(page_width / 2.0, banner_y + 92, "OUTSIDE")
            can.drawCentredString(page_width / 2.0, banner_y + 32, "WORK")

            # 5. Form Fields with Dotted Baseline Guides
            fields = [
                ("Supplier:", supplier),
                ("Job No:", job_no),
                ("Client:", client),
                ("Job Title:", title_val),
                ("Qty this pallet:", qty_val),
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

            # Pallet Numbering Footer Execution Block
            can.setFont("Helvetica-Bold", 24)
            can.drawString(margin_x + 20, margin_bottom + 40, "PALLET NUMBER:")
            
            can.setFont("Helvetica-Bold", 40)
            pallet_str = f"{display_current} OF {display_total}"
            can.drawString(margin_x + 260, margin_bottom + 38, pallet_str)

            can.showPage()
            global_counter += 1

    can.save()
    packet.seek(0)
    return packet


# -------------------------------------------------------------------------
# STREAMLIT INTERACTIVE USER INTERFACE CONTEXT DASHBOARD
# -------------------------------------------------------------------------
st.title("🛠️ PDF Toolsuite Dashboard")

# Top Navigation Management Links
st.sidebar.markdown("### Navigation Apps")
if st.sidebar.button("Batch Consolidator Page"):
    st.session_state.current_page = "batch_consolidator"
if st.sidebar.button("Production Headers & Labels Workspace"):
    st.session_state.current_page = "batches_subtab"

# Execution Routing Layers
if st.session_state.current_page == "batch_consolidator":
    st.subheader("📂 Batch Consolidator Hub")
    st.info("Upload source print document tracking manifests to parse cover metrics.")

elif st.session_state.current_page == "batches_subtab":
    sub_tab1, sub_tab2 = st.tabs(["🗂️ Standard Batch Headers", "📦 Outside Work Labels"])

    with sub_tab1:
        st.subheader("Standard Batch Header Generator")
        with st.form("batch_header_form"):
            job_no = st.text_input("Job Number", value="100234")
            description = st.text_area("Description Field Specifications")
