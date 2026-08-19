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
    page_title="PDF Toolsuite & Dynamic Label Matrix Dashboard", 
    page_icon="🛠️", 
    layout="wide"
)

# -------------------------------------------------------------------------
# NAVIGATION & PERSISTENCE STATE MANAGER
# -------------------------------------------------------------------------
if "current_page" not in st.session_state:
    st.session_state.current_page = "matrix_label_generator"
if "batches_subtab" not in st.session_state:
    st.session_state.batches_subtab = "batch_headers"

# Global Top Header Tabs Navigation Menu
tabs = st.tabs(["🏷️ Variable Label Grid Matrix", "📂 Batch Consolidator Pages", "🗂️ Production Sub-Apps"])

with tabs[0]:
    if st.button("Activate Label Matrix Engine", key="nav_matrix"):
        st.session_state.current_page = "matrix_label_generator"
with tabs[1]:
    if st.button("Activate Batch Consolidator Tool", key="nav_consolidator"):
        st.session_state.current_page = "batch_consolidator"
with tabs[2]:
    st.markdown("### Extra Legacy Applications")
    sub_c1, sub_c2 = st.columns(2)
    with sub_c1:
        if st.button("Standard Batch Headers Tab"):
            st.session_state.current_page = "batch_subapps"
            st.session_state.batches_subtab = "batch_headers"
    with sub_c2:
        if st.button("Legacy Outside Work Labels Tab"):
            st.session_state.current_page = "batch_subapps"
            st.session_state.batches_subtab = "outside_labels"

# -------------------------------------------------------------------------
# CORE UTILITY RENDERING ENGINE FUNCTIONS
# -------------------------------------------------------------------------

def create_header_pdf(metadata_dict, total_pages, page_width=612, page_height=792):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(float(page_width), float(page_height)))
    center_x, center_y = float(page_width) / 2.0, float(page_height) / 2.0
    total_lines = len(metadata_dict) + 1
    line_height = 30
    current_y = center_y + ((total_lines * line_height) / 2.0)

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

    desc_style = ParagraphStyle(
        "DescStyle", fontName="Helvetica-Bold", fontSize=32, leading=38, alignment=1
    )

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


def create_outside_work_label_file(supplier, job_no, client, job_title, qty_this_pallet, total_pallets):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    page_width, page_height = A4
    cyan_bg, dark_frame = HexColor("#00AEEF"), HexColor("#1A1A1A")
    top_clearance_pt = 80 * 2.83465

    for i in range(1, total_pallets + 1):
        can.setFillColor(cyan_bg)
        can.rect(0, 0, page_width, page_height, fill=1, stroke=0)

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

        can.setFillColor(dark_frame)
        can.setFont("Helvetica-Bold", 11)
        can.drawString(margin_x + 20, frame_top_y - 40, "From:")
        can.setFont("Helvetica-Bold", 14)
        can.drawString(margin_x + 20, frame_top_y - 58, "IVE Print")

        banner_y, banner_h = frame_top_y - 260, 160
        can.setFillColor(dark_frame)
        can.rect(margin_x, banner_y, page_width - (margin_x * 2), banner_h, fill=1, stroke=0)
        can.setFillColor(HexColor("#FFFFFF"))
        can.setFont("Helvetica-Bold", 80)
        can.drawCentredString(page_width / 2.0, banner_y + 92, "OUTSIDE")
        can.drawCentredString(page_width / 2.0, banner_y + 32, "WORK")

        # Basic label metadata positioning fields loop
        fields = [("Supplier:", supplier), ("Job No:", job_no), ("Client:", client), ("Job Title:", job_title), ("Qty this pallet:", qty_this_pallet)]
        y_start, line_gap = banner_y - 38, 36
        can.setFillColor(dark_frame)
        for idx, (label, val) in enumerate(fields):
            curr_y = y_start - (idx * line_gap)
            can.setFont("Helvetica", 15)
            can.drawString(margin_x + 20, curr_y, label)
            if val:
                can.setFont("Helvetica-Bold", 18)
                can.drawString(margin_x + 180, curr_y, str(val))
        can.showPage()
    can.save()
    packet.seek(0)
    return packet

# -------------------------------------------------------------------------
# PRECISION LABELS DRAW MATRIX GRID ENGINE
# -------------------------------------------------------------------------

def draw_custom_label_cell(can, x, y, width, height, line_data, current_idx, total_idx):
    can.setStrokeColor(HexColor("#DDDDDD"))
    can.setLineWidth(0.5)
    can.rect(x, y, width, height, fill=0, stroke=1)

    total_lines = len(line_data)
    if total_lines == 0: return

    usable_h = height * 0.85
    start_y = y + height - ((height - usable_h) / 2.0)
    line_step = usable_h / total_lines

    for idx, line in enumerate(line_data):
        raw_text = line["text"]
        processed_text = raw_text.replace("{box_num}", str(current_idx)).replace("{total_boxes}", str(total_idx))
        f_size = line["font_size"]
        f_name = "Helvetica-Bold" if line["bold"] else "Helvetica"
        
        can.setFont(f_name, f_size)
        can.setFillColor(HexColor("#000000"))
        target_y = start_y - (idx * line_step) - (f_size / 2.0)
        can.drawCentredString(x + (width / 2.0), target_y, processed_text)


def compile_matrix_pdf_pipeline(global_cfg, range_configs):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=global_cfg["page_size"])
    p_width, p_height = global_cfg["page_size"]

    rows, cols = global_cfg["rows"], global_cfg["cols"]
    m_top, m_bottom, m_left, m_right = global_cfg["margin_top"], global_cfg["margin_bottom"], global_cfg["margin_left"], global_cfg["margin_right"]

    grid_w = p_width - m_left - m_right
    grid_h = p_height - m_top - m_bottom
    cell_w = grid_w / cols
    cell_h = grid_h / rows

    current_col, current_row, global_running_num = 0, 0, 1

    for cfg in range_configs:
        range_size = (cfg["end"] - cfg["start"]) + 1
        for local_step in range(range_size):
            display_current = (local_step + 1) if cfg["num_mode"] == "Restart from 1" else global_running_num
            display_total = range_size if cfg["denom_mode"] == "Range Size" else global_cfg["total_boxes"]

            cell_x = m_left + (current_col * cell_w)
            cell_y = p_height - m_top - ((current_row + 1) * cell_h)

            draw_custom_label_cell(can, cell_x, cell_y, cell_w, cell_h, cfg["lines"], display_current, display_total)

            current_col += 1
            if current_col >= cols:
                current_col = 0
                current_row += 1
                if current_row >= rows:
                    current_row = 0
                    can.showPage()
            global_running_num += 1

    if current_col != 0 or current_row != 0:
        can.showPage()
    can.save()
    packet.seek(0)
    return packet


# -------------------------------------------------------------------------
# INTERACTIVE APPLICATION PAGES CONTEXT SWITCHING ROUTING ROUTINES
# -------------------------------------------------------------------------

# PAGE 1: DYNAMIC VARIABLE LABEL ENGINE (TAB 1)
if st.session_state.current_page == "matrix_label_generator":
    st.subheader("⚙️ Matrix Sizing & Variable Range Workspace")

    with st.sidebar.form("sheet_matrix_form"):
        st.subheader("📐 Canvas Config")
