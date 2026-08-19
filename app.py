from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
import streamlit as st

# Set page layout once at the top
@@ -59,23 +61,38 @@ def create_header_pdf(

# Helper function for Standard Batch Header generation
def create_batch_header_file(
    job_no, description, total_batches, auto_number=True
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

        # 2. Description (Under Job No.)
        can.setFont("Helvetica-Bold", 32)
        can.drawCentredString(center_x, page_height - 170, str(description))
        # 2. Wrapped Description with side margins
        max_desc_width = page_width - (2 * side_margin)
        desc_para = Paragraph(str(description), desc_style)
        para_w, para_h = desc_para.wrap(max_desc_width, page_height)

        # Base Y positioning adjusted so multi-line wraps go downwards neatly
        desc_y = page_height - 140 - para_h
        desc_para.drawOn(can, side_margin, desc_y)

# 3. Batch Numbering on 3 separate lines
can.setFont("Helvetica-Bold", 90)
@@ -163,13 +180,22 @@ def create_outside_work_label_file(

# Top Right "ive" logo
can.setFont("Helvetica-Bold", 46)
        can.drawRightString(page_width - margin_x - 25, frame_top_y - 70, "ive")
        can.drawRightString(
            page_width - margin_x - 25, frame_top_y - 70, "ive"
        )

# 4. Dark Block Banner: "OUTSIDE WORK"
banner_y = frame_top_y - 260
banner_h = 160
can.setFillColor(dark_frame)
        can.rect(margin_x, banner_y, page_width - (margin_x * 2), banner_h, fill=1, stroke=0)
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
@@ -356,7 +382,9 @@ def create_labels_pdf(
# ---------------------------------------------------------
if st.session_state.current_page == "impose":
st.subheader("📐 PDF Impose Tool")
    st.write("Layout and arrange pages for print imposition (e.g., 2-up, 4-up).")
    st.write(
        "Layout and arrange pages for print imposition (e.g., 2-up, 4-up)."
    )
st.info("Feature placeholder: Upload PDFs to begin imposition layout.")

# ---------------------------------------------------------
@@ -732,8 +760,12 @@ def create_labels_pdf(
job_no = st.text_input("Job No:", value="1615699")
client = st.text_input("Client:", value="Precision Mail Pty Ltd")
with col2:
                job_title = st.text_input("Job Title:", value="Rase Spares Scratchys")
                qty_this_pallet = st.text_input("Qty this Pallet:", value="1025")
                job_title = st.text_input(
                    "Job Title:", value="Rase Spares Scratchys"
                )
                qty_this_pallet = st.text_input(
                    "Qty this Pallet:", value="1025"
                )
total_pallets = st.number_input(
"Total Pallets (Number of Pages):",
min_value=1,
@@ -780,13 +812,24 @@ def create_labels_pdf(
"Description:", value="Fragrance Wk5-6"
)

            total_batches = st.number_input(
                "Total Batches (Number of Pages):",
                min_value=1,
                max_value=1000,
                value=20,
                step=1,
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
@@ -803,6 +846,7 @@ def create_labels_pdf(
description=description,
total_batches=int(total_batches),
auto_number=auto_number,
                        side_margin=int(side_margin),
)

out_filename = f"{job_no}_Batch_Headers.pdf"
@@ -884,35 +928,61 @@ def create_labels_pdf(

st.markdown("#### 2. Label Content & Quantity")
num_lines = st.number_input(
            "Number of Text Lines per Label:", min_value=1, max_value=5, value=2, step=1
            "Number of Text Lines per Label:",
            min_value=1,
            max_value=10,
            value=2,
            step=1,
)

lines_config = []
for i in range(int(num_lines)):
l_col1, l_col2, l_col3 = st.columns([3, 1, 1])
with l_col1:
                text = st.text_input(f"Line {i+1} Text:", value=f"Sample Text {i+1}", key=f"label_txt_{i}")
                text_val = st.text_input(
                    f"Line {i+1} Text:",
                    value=f"Sample Text {i+1}",
                    key=f"label_text_{i}",
                )
with l_col2:
                font_size = st.number_input(f"Font Size:", min_value=6, max_value=48, value=12, key=f"label_size_{i}")
                font_sz = st.number_input(
                    f"Line {i+1} Size:",
                    min_value=6,
                    max_value=72,
                    value=12,
                    step=1,
                    key=f"label_size_{i}",
                )
with l_col3:
                bold = st.checkbox("Bold", value=True, key=f"label_bold_{i}")
            
            lines_config.append({"text": text, "font_size": font_size, "bold": bold})
                is_bold = st.checkbox(
                    "Bold", value=(i == 0), key=f"label_bold_{i}"
                )

        total_labels = st.number_input(
            "Total Labels to Print:", min_value=1, max_value=10000, value=14, step=1
        )
        include_numbering = st.checkbox(
            "Include Auto-Numbering (e.g., '1 of 14') on Label?", value=True
        )
            lines_config.append(
                {"text": text_val, "font_size": font_sz, "bold": is_bold}
            )

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
                # Convert mm to ReportLab points (1 mm = ~2.83465 pt)
mm_to_pt = 2.83465
                

pdf_bytes = create_labels_pdf(
rows=int(rows),
cols=int(cols),
@@ -924,20 +994,23 @@ def create_labels_pdf(
margin_y_pt=margin_y_mm * mm_to_pt,
lines_config=lines_config,
total_labels=int(total_labels),
                    include_numbering=include_numbering,
                    include_numbering=include_num,
)

                st.success("Labels generated successfully!")
                out_filename = "Imposed_Labels_Output.pdf"

                st.success("Label sheet generated successfully!")
st.download_button(
                    label="⬇️ Download Imposed Labels PDF",
                    label=f"⬇️ Download {out_filename}",
data=pdf_bytes,
                    file_name="Imposed_Labels.pdf",
                    file_name=out_filename,
mime="application/pdf",
)

# ---------------------------------------------------------
# PAGE 5: GENERAL / OTHER TOOLS
# PAGE 5: GENERAL SETTINGS
# ---------------------------------------------------------
elif st.session_state.current_page == "general":
    st.subheader("⚙️ General Settings & Tools")
    st.write("Additional utility tools and general dashboard configuration.")
    st.subheader("⚙️ General Settings")
    st.write("Configure application parameters and system defaults.")
    st.info("System operational. All dependencies loaded.")
