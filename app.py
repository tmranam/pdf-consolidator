import io
import os
import zipfile
import pandas as pd
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
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


# Helper function for Standard Batch Headers generator
def create_batch_header_file(
    job_no, description, total_batches, auto_number=True
):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    page_width, page_height = letter

    center_x = page_width / 2.0

    # Draw pages
    for i in range(1, total_batches + 1):
        # 1. Job No. (Large font at the top)
        can.setFont("Helvetica-Bold", 70)
        can.drawCentredString(center_x, page_height - 110, str(job_no))

        # 2. Description (Under Job No.)
        can.setFont("Helvetica-Bold", 32)
        can.drawCentredString(center_x, page_height - 170, str(description))

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


# Helper function for Outside Work Label generator
def create_outside_work_label_file(
    supplier, job_no, client, job_title, qty_this_pallet, total_pallets
):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    page_width, page_height = A4

    margin = 36
    content_width = page_width - (margin * 2)

    for i in range(1, total_pallets + 1):
        # Top Header Section: From Address & Logo Header
        can.setFont("Helvetica-Bold", 10)
        can.drawString(margin, page_height - 45, "From:")
        can.setFont("Helvetica-Bold", 12)
        can.drawString(margin, page_height - 60, "IVE Print")
        can.setFont("Helvetica", 10)
        can.drawString(margin, page_height - 73, "24-36 Beyer Rd, Braeside")
        can.drawString(margin, page_height - 86, "Victoria 3195")

        # IVE Logo Placeholder Text
        can.setFont("Helvetica-Bold", 28)
        can.setFillColor(HexColor("#FF3300"))
        can.drawRightString(page_width - margin, page_height - 65, "ive")
        can.setFillColor(HexColor("#000000"))

        # Large Header: OUTSIDE WORK
        can.setFont("Helvetica-Bold", 42)
        can.drawCentredString(page_width / 2.0, page_height - 145, "OUTSIDE")
        can.drawCentredString(page_width / 2.0, page_height - 190, "WORK")

        # Horizontal Divider
        can.setLineWidth(2)
        can.line(margin, page_height - 210, page_width - margin, page_height - 210)

        # Key-Value Form Fields Layout
        y = page_height - 245
        line_gap = 58

        fields = [
            ("Supplier:", supplier),
            ("Job No:", job_no),
            ("Client:", client),
            ("Job Title:", job_title),
            ("Qty this pallet:", qty_this_pallet),
        ]

        for label, val in fields:
            can.setFont("Helvetica-Bold", 16)
            can.drawString(margin, y, label)

            can.setFont("Helvetica-Bold", 28)
            can.drawString(margin, y - 28, str(val) if val else "")

            can.setLineWidth(1)
            can.line(margin, y - 35, page_width - margin, y - 35)

            y -= line_gap

        # Bottom Section: Pallet X of Y
        y_pallet = y - 10
        can.setFont("Helvetica-Bold", 20)
        can.drawString(margin, y_pallet, "Pallet:")

        can.setFont("Helvetica-Bold", 48)
        can.drawString(margin + 80, y_pallet - 5, str(i))

        can.setFont("Helvetica-Bold", 20)
        can.drawString(margin + 170, y_pallet, "of:")

        can.setFont("Helvetica-Bold", 48)
        can.drawString(margin + 210, y_pallet - 5, str(total_pallets))

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
    st.write("Layout and arrange pages for print imposition (e.g., 2-up, 4-up).")
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
                job_title = st.text_input("Job Title:", value="Rase Spares Scratchys")
                qty_this_pallet = st.text_input("Qty this Pallet:", value="1025")
                total_pallets = st.number_input(
                    "Total Pallets (Number of Pages):",
                    min_value=1,
                    max_value=1000,
                    value=1,
                    step=1,
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

        st.markdown("#### 2. Label Text Configuration")
        num_lines = st.number_input(
            "Number of Text Lines per Label:",
            min_value=1,
            max_value=10,
            value=3,
            step=1,
        )

        lines_config = []
        for line_idx in range(int(num_lines)):
            st.markdown(f"**Line {line_idx + 1}:**")
            col_txt, col_fs, col_bld = st.columns([3, 1, 1])

            with col_txt:
                line_text = st.text_input(
                    "Text", value=f"Line {line_idx + 1} Content", key=f"lbl_txt_{line_idx}"
                )
            with col_fs:
                font_size = st.number_input(
                    "Font Size",
                    min_value=6,
                    max_value=72,
                    value=12,
                    step=1,
                    key=f"lbl_fs_{line_idx}",
                )
            with col_bld:
                is_bold = st.checkbox(
                    "Bold", value=False, key=f"lbl_bld_{line_idx}"
                )

            lines_config.append(
                {"text": line_text, "font_size": int(font_size), "bold": is_bold}
            )

        st.divider()

        st.markdown("#### 3. Batch Quantity & Numbering")
        col_qty1, col_qty2 = st.columns(2)
        with col_qty1:
            total_labels = st.number_input(
                "Total Quantity of Labels to Print:",
                min_value=1,
                max_value=10000,
                value=14,
                step=1,
            )
        with col_qty2:
            include_numbering = st.checkbox(
                "Append '1 of N' Numbering Line?",
                value=True,
                help="Adds a bottom line displaying '1 of 14', '2 of 14', etc., on each label.",
            )

        st.divider()

        if st.button("Generate Imposed Labels PDF", type="primary"):
            with st.spinner("Generating and imposing labels on A4..."):
                mm_to_pt = 2.83464567
                label_w_pt = label_w_mm * mm_to_pt
                label_h_pt = label_h_mm * mm_to_pt
                gutter_x_pt = gutter_x_mm * mm_to_pt
                gutter_y_pt = gutter_y_mm * mm_to_pt
                margin_x_pt = margin_x_mm * mm_to_pt
                margin_y_pt = margin_y_mm * mm_to_pt

                labels_pdf_io = create_labels_pdf(
                    rows=int(rows),
                    cols=int(cols),
                    label_w_pt=label_w_pt,
                    label_h_pt=label_h_pt,
                    gutter_x_pt=gutter_x_pt,
                    gutter_y_pt=gutter_y_pt,
                    margin_x_pt=margin_x_pt,
                    margin_y_pt=margin_y_pt,
                    lines_config=lines_config,
                    total_labels=int(total_labels),
                    include_numbering=include_numbering,
                )

                out_filename = f"Imposed_Labels_{total_labels}_Items.pdf"

                st.success("Labels PDF generated successfully!")
                st.download_button(
                    label=f"⬇️ Download {out_filename}",
                    data=labels_pdf_io,
                    file_name=out_filename,
                    mime="application/pdf",
                )

# ---------------------------------------------------------
# PAGE 5: GENERAL / UTILITIES
# ---------------------------------------------------------
elif st.session_state.current_page == "general":
    st.subheader("⚙️ General Settings & Diagnostics")
    st.write(
        "Manage application state, view active session data, and inspect quick PDF properties."
    )

    st.markdown("### 📄 Quick PDF Inspector")
    inspect_file = st.file_uploader(
        "Upload a PDF to inspect metadata and dimensions:", type=["pdf"]
    )

    if inspect_file:
        try:
            reader = PdfReader(inspect_file)
            total_pages = len(reader.pages)
            st.write(f"**Total Pages:** {total_pages}")

            if total_pages > 0:
                first_page = reader.pages[0]
                width = float(first_page.mediabox.width)
                height = float(first_page.mediabox.height)

                col_w, col_h = st.columns(2)
                col_w.metric("Width (pt)", f"{width:.2f}")
                col_h.metric("Height (pt)", f"{height:.2f}")

                if reader.metadata:
                    st.markdown("**Document Metadata:**")
                    metadata_clean = {
                        k: str(v)
                        for k, v in reader.metadata.items()
                        if v is not None
                    }
                    st.json(metadata_clean)
        except Exception as e:
            st.error(f"Error reading PDF file: {e}")

    st.divider()

    st.markdown("### 🔄 Session Management")
    if st.button("Reset Session State"):
        st.session_state.clear()
        st.session_state.current_page = "batch_consolidator"
        st.rerun()
