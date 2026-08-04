import io
import os
import zipfile
import pandas as pd
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import streamlit as st


def create_header_pdf(
    metadata_dict, total_pages, page_width=612, page_height=792
):
    """Generates a 1-page PDF cover sheet using user-selected metadata fields."""
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


st.set_page_config(
    page_title="PDF Consolidator", page_icon="📄", layout="centered"
)
st.title("📄 PDF Store Batch Consolidator")
st.write(
    "Upload your Excel control sheet, select cover page fields, set batch limits, and process target PDFs."
)

st.divider()

# Step 1: Upload Excel Control Sheet
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

    st.subheader("📋 Select Metadata for Cover Header Page")
    st.write(
        "Check the column headers below that you want displayed on each store's cover page:"
    )

    cols_per_row = st.columns(min(len(non_pdf_candidates), 3) or 1)
    for idx, col_name in enumerate(non_pdf_candidates):
        with cols_per_row[idx % 3]:
            if st.checkbox(col_name, value=True, key=f"meta_{col_name}"):
                selected_metadata_cols.append(col_name)

    st.divider()

    # Step 2: Upload Target PDFs
    uploaded_pdfs = st.file_uploader(
        "2. Upload PDF Files", type=["pdf"], accept_multiple_files=True
    )

    st.divider()

    # Step 3: Batching Settings
    st.subheader("⚙️ Batch Splitting Options")
    max_pages_per_file = st.number_input(
        "Maximum Target Pages Per PDF File:",
        min_value=10,
        max_value=5000,
        value=50,
        step=10,
        help="The app will package as many full stores as possible without exceeding this page count per output file.",
    )

    st.divider()

    # Step 4: Generate
    if st.button("Generate Master PDF(s)", type="primary"):
        if not uploaded_pdfs:
            st.error("Please upload the target PDF files.")
        else:
            with st.spinner("Analyzing document sizes and organizing batches..."):
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

                # --- PHASE 1: Calculate exact structure & page count for each store ---
                store_data_list = []
                max_single_store_pages = 0

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
                                    content_page_count += pages_in_file * qty
                                    valid_files_to_add.append(
                                        (pdf_file_obj, qty)
                                    )
                                else:
                                    st.warning(
                                        f"File '{pdf_key}' referenced in sheet was not uploaded."
                                    )

                    total_store_pages = 1 + content_page_count

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

                # --- Check if user threshold is smaller than a single store ---
                if max_pages_per_file < max_single_store_pages:
                    st.warning(
                        f"⚠️ Notice: The largest single store requires **{max_single_store_pages} pages**. "
                        f"Your target setting was {max_pages_per_file}. To prevent breaking any single store line across files, "
                        f"the limit will automatically adjust to at least **{max_single_store_pages} pages** per batch."
                    )
                    effective_max = max(max_pages_per_file, max_single_store_pages)
                else:
                    effective_max = max_pages_per_file

                # --- PHASE 2: Group stores into batches cleanly ---
                batches = []
                current_batch = []
                current_batch_page_count = 0

                for store in store_data_list:
                    # If adding this store exceeds the max target AND current batch isn't empty, create new batch
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

                # --- PHASE 3: Generate PDF binary data for each batch ---
                generated_files = []

                for batch_idx, batch_stores in enumerate(batches, start=1):
                    pdf_writer = PdfWriter()

                    for store in batch_stores:
                        # Add Header
                        header_pdf = create_header_pdf(
                            store["metadata"],
                            store["total_pages"],
                            page_width=store["width"],
                            page_height=store["height"],
                        )
                        pdf_writer.add_page(header_pdf.pages[0])

                        # Add Content PDFs
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
                    generated_files.append((batch_filename, buf.getvalue()))

                st.success(
                    f"Processing complete! Created {total_batches} batch file(s)."
                )

                # --- PHASE 4: Provide download options ---
                if total_batches == 1:
                    filename, file_bytes = generated_files[0]
                    st.download_button(
                        label=f"⬇️ Download {filename}",
                        data=file_bytes,
                        file_name=filename,
                        mime="application/pdf",
                    )
                else:
                    # Package multiple batches into a single ZIP file for convenient download
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(
                        zip_buffer, "w", zipfile.ZIP_DEFLATED
                    ) as zip_file:
                        for fname, fbytes in generated_files:
                            zip_file.writestr(fname, fbytes)

                    zip_buffer.seek(0)
                    zip_filename = f"{excel_basename}_All_Batches.zip"

                    st.info(
                        f"Generated **{total_batches} batch files** following the naming scheme `Batch 1 of {total_batches}`, etc."
                    )
                    st.download_button(
                        label=f"⬇️ Download All {total_batches} Batches (ZIP Archive)",
                        data=zip_buffer,
                        file_name=zip_filename,
                        mime="application/zip",
                    )
