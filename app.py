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

    current_label = 1

    while current_label <= total_labels:
        for r in range(rows):
            for c in range(cols):
                if current_label > total_labels:
                    break

                x_left = margin_x_pt + c * (label_w_pt + gutter_x_pt)
                y_top = a4_h - margin_y_pt - r * (label_h_pt + gutter_y_pt)
                center_x = x_left + (label_w_pt / 2.0)

                active_lines = list(lines_config)
                if include_numbering:
                    active_lines.append(
                        {
                            "text": f"{current_label} of {total_labels}",
                            "font_size": 10,
                            "bold": True,
                        }
                    )

                total_content_lines = len(active_lines)
                if total_content_lines > 0:
                    line_height = label_h_pt / (total_content_lines + 1)
                    current_y = y_top - line_height

                    for line in active_lines:
                        font_name = (
                            "Helvetica-Bold" if line["bold"] else "Helvetica"
                        )
                        can.setFont(font_name, line["font_size"])
                        can.drawCentredString(
                            center_x, current_y, str(line["text"])
                        )
                        current_y -= line_height

                current_label += 1

        can.showPage()

    can.save()
    packet.seek(0)
    return packet


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

# ---------------------------------------------------------
# PAGE 1: IMPOSE
# ---------------------------------------------------------
if st.session_state.current_page == "impose":
    st.subheader("📐 PDF Impose Tool")
    st.write(
        "Layout and arrange pages for print imposition (e.g., 2-up, 4-up)."
    )
    st.info("Feature placeholder: Upload PDFs to begin imposition layout.")

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

    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        if st.button("🏷️ Batch Headers", use_container_width=True):
            st.session_state.batches_subtab = "batch_headers"
    with sub_col2:
        if st.button("🖨️ Print Labels", use_container_width=True):
            st.session_state.batches_subtab = "print_labels"

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

            breaks_configs.append({
                "count": int(b_labels_count),
                "include_numbering": include_num,
                "num_mode": r_num_mode,
                "start_num": int(start_num),
                "end_num": int(end_num),
                "lines": b_final_lines,
                "total_labels_global": int(b_labels_count)
            })
            
            # Save sequential tracker step updates
            running_label_counter += int(b_labels_count)

        st.divider()

                       # Ensure there are exactly 8 spaces before 'if'
               if st.button("Generate Imposed Labels PDF", type="primary"):
            with st.spinner("Generating labels layout..."):
                mm_to_pt = 2.83465
                
                # Align denominators for the sequential continuous blocks
                total_global_sum = sum(item["count"] for item in breaks_configs)
                for item in breaks_configs:
                    if item["num_mode"] == "Continue from previous batch":
                        item["total_labels_global"] = total_global_sum

                # Fetch lines_config if it exists, otherwise fall back to empty list safely
                active_lines = lines_config if 'lines_config' in locals() else []
                
                # Fetch checkbox state safely, fallback to True if missing
                active_num = include_num if 'include_num' in locals() else True

                # Trigger backend renderer with exact variable alignments
                pdf_bytes = create_labels_pdf(
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

                out_filename = "Imposed_Labels_Output.pdf"

                st.success("Label sheet generated successfully!")
                st.download_button(
                    label=f"⬇️ Download {out_filename}",
                    data=pdf_bytes,
                    file_name=out_filename,
                    mime="application/pdf",
                )





# ---------------------------------------------------------
# PAGE 5: GENERAL SETTINGS
# ---------------------------------------------------------
elif st.session_state.current_page == "general":
    st.subheader("⚙️ General Settings")
    st.write("Configure application parameters and system defaults.")
    st.info("System operational. All dependencies loaded.")
