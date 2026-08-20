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

# =========================================================================
# SYSTEM HEADERS & GLOBAL ENVIRONMENT INITIALIZATION
# =========================================================================
st.set_page_config(
    page_title="PDF Toolsuite Dashboard", page_icon="🛠️", layout="centered"
)

if "current_page" not in st.session_state:
    st.session_state.current_page = "batch_consolidator"
if "batches_subtab" not in st.session_state:
    st.session_state.batches_subtab = "batch_headers"


# =========================================================================
# CORE HELPER ENGINE FUNCTIONS (PART 1: COVERS & BATCHES)
# =========================================================================
def create_header_pdf(metadata_dict, total_pages, page_width=612, page_height=792):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(float(page_width), float(page_height)))

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


def create_batch_header_file(job_no, description, total_batches, auto_number=True, side_margin=50):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    page_width, page_height = letter
    center_x = page_width / 2.0

    desc_style = ParagraphStyle(
        "DescStyle",
        fontName="Helvetica-Bold",
        fontSize=32,
        leading=38,
        alignment=1,  # Center text
        textColor=HexColor("#000000"),
    )

    for i in range(1, total_batches + 1):
        can.setFont("Helvetica-Bold", 70)
        can.drawCentredString(center_x, page_height - 110, str(job_no))

        max_desc_width = page_width - (2 * side_margin)
        desc_para = Paragraph(str(description), desc_style)
        para_w, para_h = desc_para.wrap(max_desc_width, page_height)

        desc_y = page_height - 140 - para_h
        desc_para.drawOn(can, side_margin, desc_y)

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
    def create_outside_work_label_file(supplier, job_no, client, job_title, qty_this_pallet, total_pallets, auto_number_pallets=True):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    page_width, page_height = A4

    cyan_bg = HexColor("#00AEEF")
    dark_frame = HexColor("#1A1A1A")
    text_dark = HexColor("#1A1A1A")
    top_clearance_pt = 80 * 2.83465

    for i in range(1, total_pallets + 1):
        can.setFillColor(cyan_bg)
        can.rect(0, 0, page_width, page_height, fill=1, stroke=0)

        margin_x = 35
        margin_bottom = 35
        margin_top = top_clearance_pt
        corner_cut = 25
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

        banner_y = frame_top_y - 260
        banner_h = 160
        can.setFillColor(dark_frame)
        can.rect(margin_x, banner_y, page_width - (margin_x * 2), banner_h, fill=1, stroke=0)

        can.setFillColor(HexColor("#FFFFFF"))
        can.setFont("Helvetica-Bold", 80)
        can.drawCentredString(page_width / 2.0, banner_y + 92, "OUTSIDE")
        can.drawCentredString(page_width / 2.0, banner_y + 32, "WORK")

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

        y_pallet = y_start - (len(fields) * line_gap)
        can.setFont("Helvetica", 15)
        can.drawString(margin_x + 20, y_pallet, "Pallet:")
        can.setFont("Helvetica-Bold", 18)
        can.drawString(margin_x + 90, y_pallet, str(i))

        can.setFont("Helvetica", 15)
        can.drawString(margin_x + 145, y_pallet, "of:")

        total_str = str(total_pallets) if auto_number_pallets else "______"
        can.setFont("Helvetica-Bold", 18)
        can.drawString(margin_x + 180, y_pallet, total_str)

        can.setStrokeColor(dark_frame)
        can.setLineWidth(1)
        can.setDash([1, 3], 0)
        can.line(margin_x + 20, y_pallet - 2, page_width - margin_x - 20, y_pallet - 2)
        can.setDash([], 0)

        can.showPage()

    can.save()
    packet.seek(0)
    return packet


def create_labels_pdf(rows, cols, label_w_pt, label_h_pt, gutter_x_pt, gutter_y_pt, margin_x_pt, margin_y_pt, total_labels, breaks_configs):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    a4_w, a4_h = A4
    
    all_computed_labels = []
    for batch in breaks_configs:
        b_count = batch.get("count", 0)
        b_lines = batch.get("lines", [])
        b_inc_num = batch.get("include_numbering", True)
        b_start = batch.get("start_num", 1)
        b_global_total = batch.get("end_num", b_count) if batch.get("num_mode") == "Restart from new number" else batch.get("total_labels_global", b_count)
        
        for i in range(b_count):
            label_data = {
                "lines": list(b_lines),
                "show_num": b_inc_num,
                "current_idx": b_start + i,
                "total_idx": b_global_total
            }
            all_computed_labels.append(label_data)
            
    total_to_render = len(all_computed_labels)
    label_ptr = 0
    
    while label_ptr < total_to_render:
        for r in range(rows):
            for c in range(cols):
                if label_ptr >= total_to_render:
                    break
                
                x_left = margin_x_pt + c * (label_w_pt + gutter_x_pt)
                y_top = a4_h - margin_y_pt - r * (label_h_pt + gutter_y_pt)
                center_x = x_left + (label_w_pt / 2.0)
                
                current_label_data = all_computed_labels[label_ptr]
                active_lines = list(current_label_data["lines"])
                
                if current_label_data["show_num"]:
                    active_lines.append({
                        "text": f"{current_label_data['current_idx']} of {current_label_data['total_idx']}",
                        "font_size": 10,
                        "bold": True
                    })
                
                total_content_lines = len(active_lines)
                if total_content_lines > 0:
                    line_height = label_h_pt / (total_content_lines + 1)
                    current_y = y_top - line_height
                    
                    for line in active_lines:
                        font_name = "Helvetica-Bold" if line.get("bold", False) else "Helvetica"
                        can.setFont(font_name, line.get("font_size", 12))
                        can.drawCentredString(center_x, current_y, str(line.get("text", "")))
                        current_y -= line_height
                
                label_ptr += 1
                
        can.showPage()
        
    can.save()
    packet.seek(0)
    return packet


# =========================================================================
# GLOBAL NAVIGATION HUBS
# =========================================================================
st.title("🛠️ PDF Toolsuite Dashboard")
st.write("Select a tool below to begin processing your files:")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    if st.button("📐 Impose", use_container_width=True): st.session_state.current_page = "impose"
with col2:
    if st.button("📄 Duplicate", use_container_width=True): st.session_state.current_page = "duplicate"
with col3:
    if st.button("📦 Consolidator", use_container_width=True): st.session_state.current_page = "batch_consolidator"
with col4:
    if st.button("🏷️ Batches & Labels", use_container_width=True): st.session_state.current_page = "batches_and_labels"
with col5:
    if st.button("⚙️ General", use_container_width=True): st.session_state.current_page = "general"

st.divider()

# =========================================================================
# APPLICATION ROUTING INTERFACES
# =========================================================================
if st.session_state.current_page == "impose":
    st.subheader("📐 PDF Impose Tool")
    st.write("Layout and arrange pages for print imposition (e.g., 2-up, 4-up).")
    st.info("Feature placeholder: Upload PDFs to begin imposition layout.")

elif st.session_state.current_page == "duplicate":
    st.subheader("📄 Duplicate Pages Tool")
    col_a, col_b = st.columns(2)
    with col_a: uploaded_pdf = st.file_uploader("1. Upload PDF File", type=["pdf"])
    with col_b: uploaded_excel = st.file_uploader("2. Upload Excel Control Sheet", type=["xlsx", "xls"], key="dup_excel")
    mode = st.radio("3. Select Printing Mode:", ["Simplex", "Duplex"], horizontal=True)

    if uploaded_pdf and uploaded_excel:
        df_dup = pd.read_excel(uploaded_excel)
        qty_col = st.selectbox("Select Quantity/Copies Column:", df_dup.columns, index=len(df_dup.columns) - 1)

        if st.button("Generate Duplicated PDF", type="primary"):
            reader = PdfReader(uploaded_pdf)
            pdf_writer = PdfWriter()
            multiplier = 2 if mode == "Duplex" else 1

            for idx in range(len(reader.pages)):
                qty = 0
                if idx < len(df_dup):
                    raw_qty = df_dup.iloc[idx][qty_col]
                    qty = int(raw_qty) if pd.notna(raw_qty) and str(raw_qty).isdigit() else 0
                for _ in range(qty * multiplier): pdf_writer.add_page(reader.pages[idx])

            output_buffer = io.BytesIO()
            pdf_writer.write(output_buffer)
            output_buffer.seek(0)
            out_filename = f"Duplicated_{mode}_Output.pdf"
            st.success("PDF duplicated successfully!")
            st.download_button(f"⬇️ Download {out_filename}", data=output_buffer, file_name=out_filename, mime="application/pdf")

elif st.session_state.current_page == "batch_consolidator":
    st.subheader("📦 PDF Store Batch Consolidator")
    uploaded_excel = st.file_uploader("1. Upload Excel Control Sheet First", type=["xlsx", "xls"])

    if uploaded_excel:
        df_control = pd.read_excel(uploaded_excel)
        all_columns = [str(col) for col in df_control.columns if not str(col).startswith("Unnamed:")]non_pdf_candidates = [col for col in all_columns if not col.strip().lower().endswith(".pdf")]st.markdown("#### 📋 Select Metadata for Cover Header Page")selected_metadata_cols = []cols_per_row = st.columns(min(len(non_pdf_candidates), 3) or 1)for idx, col_name in enumerate(non_pdf_candidates):with cols_per_row[idx % 3]:if st.checkbox(col_name, value=True, key=f"meta_{col_name}"): selected_metadata_cols.append(col_name)st.divider()uploaded_pdfs = st.file_uploader("2. Upload PDF Files", type=["pdf"], accept_multiple_files=True)
        st.divider()
        st.markdown("#### ⚙️ Batch Splitting Options")
        max_pages_per_file = st.number_input("Maximum Target Pages Per PDF File:", min_value=1, max_value=10000, value=50, step=5)

        if st.button("Generate Master PDF(s)", type="primary"):
            if not uploaded_pdfs:
                st.error("Please upload the target PDF files.")
            else:
                with st.spinner("Analyzing document sizes and organizing batches..."):
                    pdf_dict = {pdf_file.name.lower(): pdf_file for pdf_file in uploaded_pdfs}
                    store_data_list = []
                    max_single_store_pages = 0
                    grand_total_pages = 0

                    for index, row in df_control.iterrows():
                        metadata_dict = {col: row[col] for col in selected_metadata_cols if col in row}
                        content_page_count = 0
                        valid_files_to_add = []
                        detected_width, detected_height = 612, 792

                        for file_name in [c for c in all_columns if c not in selected_metadata_cols]:
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
                                            detected_width = float(reader.pages[0].mediabox.width)
                                            detected_height = float(reader.pages[0].mediabox.height)
                                        content_page_count += len(reader.pages) * qty
                                        valid_files_to_add.append((pdf_file_obj, qty))

                        total_store_pages = 1 + content_page_count
                        grand_total_pages += total_store_pages
                        max_single_store_pages = max(max_single_store_pages, total_store_pages)

                        store_data_list.append({
                            "metadata": metadata_dict, "total_pages": total_store_pages,
                            "files": valid_files_to_add, "width": detected_width, "height": detected_height
                        })

                    effective_max = max(max_pages_per_file, max_single_store_pages)
                    st.info(f"📊 **Total pages across all items:** {grand_total_pages}. Packed into batch limit splits safely.")

elif st.session_state.current_page == "batches_and_labels":
    st.subheader("🏷️ Batches & Labels Dashboard")

    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        if st.button("🏷️ Batch Headers", use_container_width=True): st.session_state.batches_subtab = "batch_headers"
    with sub_col2:
        if st.button("🖨️ Print Labels", use_container_width=True): st.session_state.batches_subtab = "print_labels"

    st.divider()

    if st.session_state.batches_subtab == "batch_headers":
        st.markdown("### 🏷️ Batch Headers Generator")
        is_outside_work = st.checkbox("Create Outside Work Label?", value=False)

        if is_outside_work:
            col1, col2 = st.columns(2)
            with col1:
                supplier = st.text_input("Supplier:", value="")
                job_no = st.text_input("Job No:", value="1615699")
                client = st.text_input("Client:", value="Precision Mail Pty Ltd")
            with col2:
                job_title = st.text_input("Job Title:", value="Rase Spares Scratchys")
                qty_this_pallet = st.text_input("Qty this Pallet:", value="1025")
                total_pallets = st.number_input("Total Pallets:", min_value=1, value=1)

            auto_number_pallets = st.checkbox("Include Total Pallet Count?", value=True)

            if st.button("Generate Outside Work Label PDF", type="primary"):
                pdf_bytes = create_outside_work_label_file(supplier, job_no, client, job_title, qty_this_pallet, int(total_pallets), auto_number_pallets)
                st.download_button(f"⬇️ Download {job_no}_Outside_Work_Label.pdf", data=pdf_bytes, file_name=f"{job_no}_Outside_Work_Label.pdf", mime="application/pdf")
        else:
            col1, col2 = st.columns(2)
            with col1: job_no = st.text_input("Job No.:", value="054520")
            with col2: description = st.text_input("Description:", value="Fragrance Wk5-6")
            col3, col4 = st.columns(2)
            with col3: side_margin = st.number_input("Side Margin (pt):", min_value=0, value=50)
            with col4: total_batches = st.number_input("Total Batches:", min_value=1, value=20)
            auto_number = st.checkbox("Include Total Count?", value=True)

            if st.button("Generate Batch Headers PDF", type="primary"):
                pdf_bytes = create_batch_header_file(job_no, description, int(total_batches), auto_number, int(side_margin))
                st.download_button(f"⬇️ Download {job_no}_Batch_Headers.pdf", data=pdf_bytes, file_name=f"{job_no}_Batch_Headers.pdf", mime="application/pdf")

    elif st.session_state.batches_subtab == "print_labels":
        st.markdown("### 🖨️ Print Labels Generator")
        
        st.markdown("#### 1. Page Layout & Label Dimensions (mm)")
        col_grid1, col_grid2 = st.columns(2)
        with col_grid1:
            rows = st.number_input("Rows per A4 Page:", min_value=1, max_value=20, value=7)
            cols = st.number_input("Columns per A4 Page:", min_value=1, max_value=10, value=2)
            label_w_mm = st.number_input("Label Width (mm):", min_value=10.0, value=99.1)
            label_h_mm = st.number_input("Label Height (mm):", min_value=10.0, value=38.1)
        with col_grid2:
            gutter_x_mm = st.number_input("Horizontal Gutter (mm):", min_value=0.0, value=2.5)
            gutter_y_mm = st.number_input("Vertical Gutter (mm):", min_value=0.0, value=0.0)
            margin_x_mm = st.number_input("Page Side Margin (mm):", min_value=0.0, value=4.5)
            margin_y_mm = st.number_input("Page Top Margin (mm):", min_value=0.0, value=15.0)

        st.divider()
        st.markdown("#### 2. Label Master Content & Quantity")
        num_lines = st.number_input("Number of Text Lines per Label:", min_value=1, max_value=10, value=2)

        master_lines = []
        st.markdown("##### 🖋️ Configure Master Baseline Values")
        for i in range(int(num_lines)):
            l_col1, l_col2, l_col3 = st.columns([3, 1, 1])
            with l_col1: m_text = st.text_input(f"Line {i+1} Master Text:", value=f"Sample Text {i+1}", key=f"master_text_{i}")
            with l_col2: m_sz = st.number_input(f"Line {i+1} Master Size:", min_value=6, value=12, key=f"master_size_{i}")
            with l_col3: m_bld = st.checkbox("Bold", value=(i == 0), key=f"master_bold_{i}")
            master_lines.append({"text": m_text, "font_size": m_sz, "bold": m_bld})

        st.divider()
        st.markdown("#### 3. Batch Break Segment Control Matrix")
        num_breaks = st.number_input("Number of Breaks / Batch Segments:", min_value=1, value=1)

        breaks_configs = []
        running_label_counter = 1

        for b in range(int(num_breaks)):
            st.markdown(f"##### 📦 Batch Segment Group Block #{b+1}")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1: b_labels_count = st.number_input(f"Total Labels for Batch #{b+1}:", min_value=1, value=14, key=f"b_count_{b}")
            with col_b2: include_num = st.checkbox("Include Sequence Counter?", value=True, key=f"b_inc_num_{b}")
            with col_b3: r_num_mode = st.radio(f"Sequence Slicing Logic:", ["Continue from previous batch", "Restart from new number"], key=f"b_mode_{b}")

            # FIX: Force execution paths to lock into localized numbering chains
            if r_num_mode == "Restart from new number":
                nc1, nc2 = st.columns(2)
                with nc1: start_num = st.number_input("Start Overwrite:", min_value=1, value=1, key=f"b_start_{b}")
                with nc2: end_num = st.number_input("End Denominator:", min_value=1, value=14, key=f"b_end_{b}")
                running_label_counter = start_num
            else:
                start_num = running_label_counter
                end_num = running_label_counter + b_labels_count - 1

            b_final_lines = []
            for i in range(int(num_lines)):
                cc1, cc2 = st.columns([1, 2])
                with cc1: stay_same = st.checkbox("Inherit Master", value=True, key=f"b_same_{b}_{i}")
                with cc2:
                    if stay_same:
                        line_txt = master_lines[i]["text"]
                    else:
                        line_txt = st.text_input(f"Modify Text Line {i+1}:", value=master_lines[i]["text"], key=f"b_text_override_{b}_{i}")
                b_final_lines.append({"text": line_txt, "font_size": master_lines[i]["font_size"], "bold": master_lines[i]["bold"]})

            # FIX: Ensure global index handles standalone batches accurately without resetting out-of-bounds metrics
            if r_num_mode == "Restart from new number":
                running_label_counter = start_num + int(b_labels_count)
            else:
                running_label_counter += int(b_labels_count)
breaks_configs.append({"count": int(b_labels_count), "include_numbering": include_num, "num_mode": r_num_mode,"start_num": int(start_num), "end_num": int(end_num), "lines": b_final_lines, "total_labels_global": int(b_labels_count)})st.divider()if st.button("Generate Imposed Labels PDF", type="primary"):with st.spinner("Generating labels layout..."):mm_to_pt = 2.83465total_global_sum = sum(item.get("count", 0) for item in breaks_configs)for item in breaks_configs:if item.get("num_mode") == "Continue from previous batch":item["total_labels_global"] = total_global_sumpdf_buffer = create_labels_pdf(rows=int(rows), cols=int(cols),label_w_pt=label_w_mm * mm_to_pt, label_h_pt=label_h_mm * mm_to_pt,gutter_x_pt=gutter_x_mm * mm_to_pt, gutter_y_pt=gutter_y_mm * mm_to_pt,margin_x_pt=margin_x_mm * mm_to_pt, margin_y_pt=margin_y_mm * mm_to_pt,total_labels=int(total_global_sum), breaks_configs=breaks_configs)pdf_bytes = pdf_buffer.getvalue() if hasattr(pdf_buffer, "getvalue") else pdf_bufferif len(pdf_bytes) > 100:st.success("Label sheet matrix generated successfully!")st.download_button(label="⬇ Download Imposed_Labels_Output.pdf", data=pdf_bytes, file_name="Imposed_Labels_Output.pdf", mime="application/pdf")else:st.error("Error: Generated PDF is empty. Check configurations.")elif st.session_state.current_page == "general":st.subheader("⚙️ General Settings")st.write("Configure general application attributes here.")

