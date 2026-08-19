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
    page_title="Dynamic Dynamic Range Label Matrix Engine", 
    page_icon="🏷️", 
    layout="wide"
)

# -------------------------------------------------------------------------
# COMPREHENSIVE MATH ENGINE: CORE DYNAMIC GRID LAYOUT DRAWING PIPELINE
# -------------------------------------------------------------------------

def draw_custom_label_cell(
    can, x, y, width, height, line_data, current_idx, total_idx
):
    """
    Draws a single multi-line grid cell using dynamic spatial layout math.
    Automatically interprets sequence denominators inline.
    """
    # Optional visual boundary reference box
    can.setStrokeColor(HexColor("#CCCCCC"))
    can.setLineWidth(0.5)
    can.setDash([2, 2], 0)
    can.rect(x, y, width, height, fill=0, stroke=1)
    can.setDash([], 0) # Clear dashes

    total_lines = len(line_data)
    if total_lines == 0:
        return

    # Dynamic baseline layout positioning metrics
    usable_h = height * 0.85
    start_y = y + height - ((height - usable_h) / 2.0)
    line_step = usable_h / total_lines

    for idx, line in enumerate(line_data):
        raw_text = line["text"]
        
        # In-line sequence indicator token parsing evaluation
        processed_text = raw_text.replace("{box_num}", str(current_idx))
        processed_text = processed_text.replace("{total_boxes}", str(total_idx))

        f_size = line["font_size"]
        is_bold = line["bold"]
        f_name = "Helvetica-Bold" if is_bold else "Helvetica"
        
        can.setFont(f_name, f_size)
        can.setFillColor(HexColor("#000000"))
        
        target_y = start_y - (idx * line_step) - (f_size / 2.0)
        center_x = x + (width / 2.0)
        
        can.drawCentredString(center_x, target_y, processed_text)


def compile_matrix_pdf_pipeline(global_cfg, range_configs):
    """
    Renders flexible labels per sheet grids, dynamically stepping over multiple pages
    based on custom rows, columns, and sheet padding matrices.
    """
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=global_cfg["page_size"])
    p_width, p_height = global_cfg["page_size"]

    # Destructure global physical measurements
    rows = global_cfg["rows"]
    cols = global_cfg["cols"]
    m_top = global_cfg["margin_top"]
    m_bottom = global_cfg["margin_bottom"]
    m_left = global_cfg["margin_left"]
    m_right = global_cfg["margin_right"]

    # Calculate exact cell dimensions based on sheet layouts
    grid_w = p_width - m_left - m_right
    grid_h = p_height - m_top - m_bottom
    cell_w = grid_w / cols
    cell_h = grid_h / rows

    current_col = 0
    current_row = 0  # 0 is the top row of cells on the layout canvas
    global_running_num = 1

    for cfg in range_configs:
        start_box = cfg["start"]
        end_box = cfg["end"]
        range_size = (end_box - start_box) + 1

        for local_step in range(range_size):
            # Resolve individual tracking index numbers
            if cfg["num_mode"] == "Restart from 1":
                display_current = local_step + 1
            else:
                display_current = global_running_num

            # Resolve individual tracking base ceilings
            if cfg["denom_mode"] == "Range Size":
                display_total = range_size
            else:
                display_total = global_cfg["total_boxes"]

            # Calculate precise draw coordinate origins
            cell_x = m_left + (current_col * cell_w)
            cell_y = p_height - m_top - ((current_row + 1) * cell_h)

            # Draw the label cell configuration
            draw_custom_label_cell(
                can, cell_x, cell_y, cell_w, cell_h, 
                cfg["lines"], display_current, display_total
            )

            # Progress structural layout matrix coordinates
            current_col += 1
            if current_col >= cols:
                current_col = 0
                current_row += 1
                if current_row >= rows:
                    current_row = 0
                    can.showPage()  # Commit structural canvas layer to sheet stream

            global_running_num += 1

    # Finalize remaining layouts
    if current_col != 0 or current_row != 0:
        can.showPage()

    can.save()
    packet.seek(0)
    return packet


# -------------------------------------------------------------------------
# INTERACTIVE USER INTERFACE CONTROLS
# -------------------------------------------------------------------------

st.title("🎛️ Complete Precision Label Matrix Suite")
st.markdown("Configure physical sheet layouts, text line formatting properties, and apply dynamic range sequence overrides.")

# Global Sheet and Canvas Parameter Control Center
with st.sidebar.form("sheet_matrix_form"):
    st.subheader("📏 1. Sheet & Canvas Geometry")
    p_format = st.selectbox("Sheet Geometry Size", ["A4", "Letter"])
    p_size = A4 if p_format == "A4" else letter
    
    st.markdown("---")
    st.subheader("🔲 2. Matrix Dimensions")
    cols = st.number_input("Columns Per Sheet", min_value=1, value=2, step=1)
    rows = st.number_input("Rows Per Sheet", min_value=1, value=4, step=1)
    
    st.markdown("---")
    st.subheader("📐 3. Grid Padding (Points)")
    m_top = st.number_input("Top Margin", min_value=0, value=30)
    m_bottom = st.number_input("Bottom Margin", min_value=0, value=30)
    m_left = st.number_input("Left Margin", min_value=0, value=30)
    m_right = st.number_input("Right Margin", min_value=0, value=30)
    
    st.markdown("---")
    st.subheader("🔢 4. Global Production Count")
    total_boxes = st.number_input("Total Output Run Target", min_value=1, value=50, step=1)
    
    lock_globals = st.form_submit_button("Lock Physical Layout Configurations")

global_cfg = {
    "page_size": p_size, "cols": cols, "rows": rows,
    "margin_top": m_top, "margin_bottom": m_bottom,
    "margin_left": m_left, "margin_right": m_right,
    "total_boxes": total_boxes
}

# Sub-Range Variable Control Configuration Block
st.subheader("🔧 Variable Range Groupings & Data Mapping Matrix")
st.info(f"Dynamically partition and format text profiles across your global target run of **{total_boxes}** units.")

if "range_count" not in st.session_state:
    st.session_state.range_count = 1
if "line_counts" not in st.session_state:
    st.session_state.line_counts = {}

c_btn1, c_btn2 = st.columns(2)
with c_btn1:
    if st.button("➕ Append Sub-Range Block"):
        st.session_state.range_count += 1
with c_btn2:
    if st.button("❌ Remove Last Sub-Range Block") and st.session_state.range_count > 1:
        st.session_state.range_count -= 1

range_configs = []
current_auto_start = 1

# Render flexible property cards for each separate range segment block
for r_idx in range(st.session_state.range_count):
    st.markdown(f"---")
    st.markdown(f"### 🏷️ Sub-Range Interval Block #{r_idx + 1}")
    
    # Range Boundaries
    c1, c2, c3, c4 = st.columns([1, 1, 2, 2])
    with c1:
        r_start = st.number_input("Start Unit Index", min_value=1, max_value=total_boxes, value=min(current_auto_start, total_boxes), key=f"start_{r_idx}")
    with c2:
        def_end = min(r_start + 9, total_boxes)
        r_end = st.number_input("End Unit Index", min_value=int(r_start), max_value=total_boxes, value=int(def_end), key=f"end_{r_idx}")
    with c3:
        r_num_mode = st.radio("Counter Sequence Strategy", ["Continue Sequence", "Restart from 1"], key=f"num_{r_idx}")
    with c4:
        r_denom_mode = st.radio("Denominator Tracking Sizing", ["Global Total", "Range Size"], key=f"denom_{r_idx}")

    # Dynamic line allocation parameters for each separate range
    st.markdown(f"**Text & Layout Specifications for Block #{r_idx + 1}**")
    st.caption("Use token placeholders `{box_num}` and `{total_boxes}` anywhere inside text rows to inject running sequence numbers dynamically.")
    
    if r_idx not in st.session_state.line_counts:
        st.session_state.line_counts[r_idx] = 4
        
    l_col1, l_col2 = st.columns(2)
    with l_col1:
        if st.button("➕ Insert New Formatting Row Line", key=f"add_line_{r_idx}"):
            st.session_state.line_counts[r_idx] += 1
            st.rerun()
    with l_col2:
        if st.button("❌ Drop Bottom Formatting Row Line", key=f"drop_line_{r_idx}") and st.session_state.line_counts[r_idx] > 1:
            st.session_state.line_counts[r_idx] -= 1
            st.rerun()

    # Generate variable formatting control cards matching current line selection parameters
    block_lines = []
    for l_idx in range(st.session_state.line_counts[r_idx]):
        lc1, lc2, lc3 = st.columns([5, 2, 1])
        
        # Establish structural default strings
        default_val = "Sample Fixed Label Data"
        if l_idx == 0: default_val = "JOB NUMBER: 240822"
        elif l_idx == 1: default_val = "ITEM CONTENT DESCRIPTIONS"
        elif l_idx == 2: default_val = "PACK QUANTITY: 100 UNITS"
        elif l_idx == 3: default_val = "UNIT: {box_num} OF {total_boxes}"
            
        with lc1:
            l_text = st.text_input(f"Line {l_idx + 1} Print Text", value=default_val, key=f"txt_{r_idx}_{l_idx}")
        with lc2:
            l_size = st.number_input(f"Font Point Size", min_value=4, max_value=120, value=14, key=f"sz_{r_idx}_{l_idx}")
        with lc3:
            st.markdown("<div style='padding-top:25px;'></div>", unsafe_allow_html=True)
            l_bold = st.checkbox("Bold", value=False, key=f"bld_{r_idx}_{l_idx}")
            
        block_lines.append({"text": l_text, "font_size": l_size, "bold": l_bold})
        
