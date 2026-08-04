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

    for i in range(1, total_pallets + 1):
        # 1. Fill Page Background (Bright Cyan/Blue)
        can.setFillColor(cyan_bg)
        can.rect(0, 0, page_width, page_height, fill=1, stroke=0)

        # 2. Outer Chamfered Border Frame
        margin_x = 35
        margin_y = 35
        frame_w = page_width - (margin_x * 2)
        frame_h = page_height - (margin_y * 2)
        corner_cut = 25  # Corner angle cutout at the top

        path = can.beginPath()
        path.moveTo(margin_x + corner_cut, page_height - margin_y)
        path.lineTo(
            page_width - margin_x - corner_cut, page_height - margin_y
        )
        path.lineTo(page_width - margin_x, page_height - margin_y - corner_cut)
        path.lineTo(page_width - margin_x, margin_y)
        path.lineTo(margin_x, margin_y)
        path.lineTo(margin_x, page_height - margin_y - corner_cut)
        path.close()

        can.setStrokeColor(dark_frame)
        can.setLineWidth(5)
        can.drawPath(path, fill=0, stroke=1)

        # 3. Top Section: From Address & Logo
        can.setFillColor(text_dark)
        can.setFont("Helvetica-Bold", 11)
        can.drawString(margin_x + 20, page_height - 75, "From:")
        can.setFont("Helvetica-Bold", 14)
        can.drawString(margin_x + 20, page_height - 93, "IVE Print")
        can.setFont("Helvetica", 11)
        can.drawString(
            margin_x + 20, page_height - 109, "24-36 Beyer Rd, Braeside"
        )
        can.drawString(margin_x + 20, page_height - 123, "Victoria 3195")

        # Top Right "ive" logo
        can.setFont("Helvetica-Bold", 46)
        can.drawRightString(
            page_width - margin_x - 25, page_height - 105, "ive"
        )

        # 4. Dark Block Banner: "OUTSIDE WORK"
        banner_y = page_height - 350
        banner_h = 190
        can.setFillColor(dark_frame)
        can.rect(
            margin_x, banner_y, frame_w, banner_h, fill=1, stroke=0
        )

        can.setFillColor(HexColor("#FFFFFF"))
        can.setFont("Helvetica-Bold", 54)
        can.drawCentredString(page_width / 2.0, banner_y + 110, "OUTSIDE")
        can.drawCentredString(page_width / 2.0, banner_y + 40, "WORK")

        # 5. Form Fields with Dotted Baseline Guides
        fields = [
            ("Supplier:", supplier),
            ("Job No:", job_no),
            ("Client:", client),
            ("Job Title:", job_title),
            ("Qty this pallet:", qty_this_pallet),
        ]

        y_start = banner_y - 45
        line_gap = 42

        can.setFillColor(text_dark)

        for idx, (label, val) in enumerate(fields):
            curr_y = y_start - (idx * line_gap)

            # Field Label
            can.setFont("Helvetica", 16)
            can.drawString(margin_x + 20, curr_y, label)

            label_width = can.stringWidth(label, "Helvetica", 16)
            dots_x_start = margin_x + 25 + label_width

            # Render Form Entry Text
            if val:
                can.setFont("Helvetica-Bold", 20)
                can.drawString(dots_x_start + 10, curr_y, str(val))

            # Render Dotted Line Baseline
            can.setStrokeColor(dark_frame)
            can.setLineWidth(1)
            can.setDash([1, 3], 0)  # Creates dotted line effect
            can.line(
                dots_x_start,
                curr_y - 2,
                page_width - margin_x - 20,
                curr_y - 2,
            )

        # 6. Bottom Row: Pallet X of Y
        y_pallet = y_start - (len(fields) * line_gap)

        can.setFont("Helvetica", 16)
        can.drawString(margin_x + 20, y_pallet, "Pallet:")

        # Draw Pallet Number
        can.setFont("Helvetica-Bold", 20)
        can.drawString(margin_x + 95, y_pallet, str(i))

        # "of:" text
        can.setFont("Helvetica", 16)
        can.drawString(margin_x + 155, y_pallet, "of:")

        # Draw Total Pallets value
        total_str = str(total_pallets) if auto_number_pallets else ""
        if total_str:
            can.setFont("Helvetica-Bold", 20)
            can.drawString(margin_x + 195, y_pallet, total_str)

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
