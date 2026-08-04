import io
import os
import pandas as pd
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import streamlit as st


def create_header_pdf(
    metadata_dict, total_pages, page_width=612, page_height=792
):
    """Generates a 1-page PDF cover sheet using only user-selected metadata fields."""
    packet = io.BytesIO()
    can = canvas.Canvas(
        packet, pagesize=(float(page_width), float(page_height))
    )

    center_x = float(page_width) / 2.0
    center_y = float(page_height) / 2.0

    # Total items to render (Metadata lines + Total Pages line)
    total_lines = len(metadata_dict) + 1
    line_height = 30
    start_y = center_y + ((total_lines * line_height) / 2.0)

    current_y = start_y

    # Render selected metadata lines
    for idx, (label, val) in enumerate(metadata_dict.items()):
        val_str = "" if pd.isna(val) else str(val)

        # Make the first selected metadata field (usually Store Name) larger and bold
        if idx == 0:
            can.setFont("Helvetica-Bold", 22)
            can.drawCentredString(center_x, current_y, f"{val_str}")
        else:
            can.setFont("Helvetica", 13)
            can.drawCentredString(center_x, current_y, f"{label}: {val_str}")

        current_y -= line_height

    # Render Total Pages line
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
    "Upload your Excel sheet first, configure cover page fields, then upload target PDFs to generate your master file."
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

    # Separate non-PDF metadata columns from PDF file columns
    all_columns = [
        str(col)
        for col in df_control.columns
        if not str(col).startswith("Unnamed:")
    ]

    non_pdf_candidates = []
    file_columns = []

    for col in all_columns:
        # Check if header ends with .pdf (case insensitive)
        if col.strip().lower().endswith(".pdf"):
            file_columns.append(col)
        else:
            non_pdf_candidates.append(col)

    st.subheader("📋 Select Metadata for Cover Header Page")
    st.write(
        "Check the column headers below that you want displayed on each store's cover page:"
    )

    # Display checkboxes for non-PDF column headers
    cols_per_row = st.columns(min(len(non_pdf_candidates), 3) or 1)
    for idx, col_name in enumerate(non_pdf_candidates):
        with cols_per_row[idx % 3]:
            # Default to checked
            if st.checkbox(col_name, value=True, key=f"meta_{col_name}"):
                selected_metadata_cols.append(col_name)

    st.divider()

    # Step 2: Upload Target PDFs
    uploaded_pdfs = st.file_uploader(
        "2. Upload PDF Files", type=["pdf"], accept_multiple_files=True
    )

    st.divider()

    # Step 3: Generate
    if st.button("Generate Master PDF", type="primary"):
        if not uploaded_pdfs:
            st.error("Please upload the target PDF files.")
        else:
            with st.spinner("Processing documents and compiling PDF..."):
                pdf_dict = {
                    pdf_file.name.lower(): pdf_file
                    for pdf_file in uploaded_pdfs
                }
                excel_basename = os.path.splitext(uploaded_excel.name)[0]
                output_filename = f"{excel_basename}_Consolidated.pdf"

                # If no explicit .pdf headers were found, treat remaining unselected columns as file names
                if not file_columns:
                    file_columns = [
                        c
                        for c in all_columns
                        if c not in selected_metadata_cols
                    ]

                pdf_writer = PdfWriter()

                for index, row in df_control.iterrows():
                    # Extract selected metadata for this store
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

                    total_pages_for_store = 1 + content_page_count

                    # Build Cover Header Page with checked metadata fields
                    header_pdf = create_header_pdf(
                        metadata_dict,
                        total_pages_for_store,
                        page_width=detected_width,
                        page_height=detected_height,
                    )
                    pdf_writer.add_page(header_pdf.pages[0])

                    # Append content PDFs
                    for pdf_file_obj, qty in valid_files_to_add:
                        pdf_file_obj.seek(0)
                        reader = PdfReader(pdf_file_obj)
                        for _ in range(qty):
                            for page in reader.pages:
                                pdf_writer.add_page(page)

                output_buffer = io.BytesIO()
                pdf_writer.write(output_buffer)
                output_buffer.seek(0)

                st.success("Master PDF generated successfully!")

                st.download_button(
                    label=f"⬇️ Download {output_filename}",
                    data=output_buffer,
                    file_name=output_filename,
                    mime="application/pdf",
                )
