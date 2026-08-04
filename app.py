import io
import os
import pandas as pd
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import streamlit as st


def create_header_pdf(store_name, address, postcode, total_pages):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    address_str = "" if pd.isna(address) else str(address)
    postcode_str = "" if pd.isna(postcode) else str(postcode)

    can.setFont("Helvetica-Bold", 24)
    can.drawCentredString(300, 520, str(store_name))

    can.setFont("Helvetica", 14)
    location_line = f"Address: {address_str}"
    if postcode_str:
        location_line += f" | Postcode: {postcode_str}"
    can.drawCentredString(300, 485, location_line)

    can.setFont("Helvetica-Bold", 14)
    can.drawCentredString(300, 450, f"Total Pages: {total_pages}")

    can.save()
    packet.seek(0)
    return PdfReader(packet)


st.set_page_config(
    page_title="PDF Consolidator", page_icon="📄", layout="centered"
)
st.title("📄 PDF Store Batch Consolidator")
st.write(
    "Upload your target PDF files and your Excel control sheet to generate the master PDF."
)

st.divider()

uploaded_pdfs = st.file_uploader(
    "1. Upload PDF Files", type=["pdf"], accept_multiple_files=True
)
uploaded_excel = st.file_uploader(
    "2. Upload Excel Control Sheet", type=["xlsx", "xls"]
)

st.divider()

if st.button("Generate Master PDF", type="primary"):
    if not uploaded_pdfs:
        st.error("Please upload at least one PDF file.")
    elif not uploaded_excel:
        st.error("Please upload an Excel control sheet.")
    else:
        with st.spinner("Processing documents and compiling PDF..."):
            pdf_dict = {
                pdf_file.name.lower(): pdf_file for pdf_file in uploaded_pdfs
            }
            excel_basename = os.path.splitext(uploaded_excel.name)[0]
            output_filename = f"{excel_basename}_Consolidated.pdf"

            df_control = pd.read_excel(uploaded_excel)

            non_pdf_columns = [
                "Store Name",
                "Address",
                "Postcode",
                "Post Code",
                "Zip",
            ]
            store_col_name = df_control.columns[0]

            file_columns = [
                col
                for col in df_control.columns[1:]
                if not str(col).startswith("Unnamed:")
                and str(col).strip() not in non_pdf_columns
            ]

            pdf_writer = PdfWriter()

            for index, row in df_control.iterrows():
                store_name = row[store_col_name]
                if pd.isna(store_name):
                    continue

                address_val = row.get("Address", "")
                postcode_val = row.get("Postcode", row.get("Post Code", ""))

                content_page_count = 0
                valid_files_to_add = []

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

                header_pdf = create_header_pdf(
                    store_name, address_val, postcode_val, total_pages_for_store
                )
                pdf_writer.add_page(header_pdf.pages[0])

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
