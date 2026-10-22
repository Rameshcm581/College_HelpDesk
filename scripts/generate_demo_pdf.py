#!/usr/bin/env bash
# ==============================================================================
# Generate Fictional Demonstration PDF for College AI Help Desk
# ==============================================================================
import os
import pathlib
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

OUTPUT_DIR = pathlib.Path(__file__).parent.parent / "backend" / "storage"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = OUTPUT_DIR / "demo_college_regulations_2025_2026.pdf"

def generate_pdf():
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        alignment=1, # Center
        spaceAfter=6
    )

    banner_style = ParagraphStyle(
        'DemoBanner',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#b91c1c'),
        backColor=colors.HexColor('#fee2e2'),
        borderColor=colors.HexColor('#f87171'),
        borderWidth=1,
        borderPadding=6,
        alignment=1,
        spaceAfter=15
    )

    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#166534'),
        spaceBefore=10,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=6
    )

    story = []

    # ── PAGE 1: ADMISSIONS & TUITION FEES ─────────────────────────────────────
    story.append(Paragraph("ST. JUDE COLLEGE OF ENGINEERING & TECHNOLOGY", title_style))
    story.append(Paragraph("ACADEMIC & CAMPUS REGULATIONS (2025–2026)", ParagraphStyle('Sub', parent=title_style, fontSize=12, leading=15, textColor=colors.HexColor('#475569'))))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>[DEMONSTRATION SAMPLE]</b> - FICTIONAL COLLEGE REGULATIONS CREATED EXCLUSIVELY FOR AI RETRIEVAL BENCHMARKS. ALL POLICIES AND FEES ARE FICTIONAL.", banner_style))
    
    story.append(Paragraph("1. Undergraduate Admissions & Tuition Fee Structure (2025–2026)", section_style))
    story.append(Paragraph("This circular governs undergraduate admissions and fee collections for the academic year 2025–2026, approved by the College Academic Governing Council.", body_style))
    story.append(Spacer(1, 4))

    fee_data = [
        ["Department / Programme", "Quota", "Annual Tuition Fee", "Payment Due Date"],
        ["B.E. Computer Science & Engineering", "Merit Quota", "₹85,000 per annum", "July 15, 2025"],
        ["B.E. Electronics & Communication", "Merit Quota", "₹80,000 per annum", "July 15, 2025"],
        ["B.E. Mechanical Engineering", "Merit Quota", "₹75,000 per annum", "July 15, 2025"],
        ["B.Tech Artificial Intelligence", "Merit Quota", "₹90,000 per annum", "July 15, 2025"]
    ]
    t1 = Table(fee_data, colWidths=[180, 80, 130, 110])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>1.2 Merit Scholarship Cut-off Criteria:</b>", body_style))
    story.append(Paragraph("Students securing a Higher Secondary cut-off score of <b>185.50 marks or higher</b> are entitled to a 50% tuition fee waiver for the first academic year. Renewal requires maintaining a CGPA of 8.50 without standing arrears.", body_style))
    story.append(Paragraph("<b>1.3 Late Admission Penalties:</b>", body_style))
    story.append(Paragraph("Admissions fee remittance after the due date of <b>July 15, 2025</b> incurs an administrative surcharge of ₹250 per calendar day up to July 31, 2025. Seats unconfirmed after July 31st will be forfeited.", body_style))

    # Page break for Page 2
    from reportlab.platypus import PageBreak
    story.append(PageBreak())

    # ── PAGE 2: HOSTEL ACCOMMODATION & MESS EXPENSES ───────────────────────────
    story.append(Paragraph("ST. JUDE COLLEGE OF ENGINEERING & TECHNOLOGY", title_style))
    story.append(Paragraph("<b>[DEMONSTRATION SAMPLE]</b> - FICTIONAL COLLEGE REGULATIONS CREATED EXCLUSIVELY FOR AI RETRIEVAL BENCHMARKS.", banner_style))
    
    story.append(Paragraph("2. Campus Hostel Accommodation, Caution Deposit & Mess Rules", section_style))
    story.append(Paragraph("All residential students must strictly adhere to the hostel residency guidelines outlined by the Hostel Warden Office (Room #102, Ground Floor, Block-B).", body_style))
    story.append(Spacer(1, 6))

    hostel_data = [
        ["Fee Component", "Applicability", "Amount", "Refundable / Policy"],
        ["Hostel Caution Deposit", "One-time at admission", "₹5,000", "100% Refundable at graduation"],
        ["Annual Mess Advance", "Per Academic Year", "₹42,000", "Adjustable against monthly billing"],
        ["Room Rent (Twin Sharing)", "Per Academic Year", "₹28,000", "Non-refundable"],
        ["Room Rent (Single Occupancy)", "Per Academic Year", "₹38,000", "Subject to availability"]
    ]
    t2 = Table(hostel_data, colWidths=[140, 110, 80, 170])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>2.2 Hostel Fee Due Date and Late Penalties:</b>", body_style))
    story.append(Paragraph("Hostel and mess fees must be cleared on or before <b>July 31, 2025</b>. A late fee penalty of <b>₹100 per day</b> applies thereafter up to 15 calendar days (August 15, 2025). Failure to clear fees by August 15th results in automatic cancellation of room allotment.", body_style))
    story.append(Paragraph("<b>2.3 Mess Timings & Dining Regulations:</b>", body_style))
    story.append(Paragraph("Breakfast: 07:30 AM – 09:00 AM | Lunch: 12:30 PM – 02:00 PM | Dinner: 07:30 PM – 09:00 PM. Food cannot be taken outside the dining hall.", body_style))

    # Page break for Page 3
    story.append(PageBreak())

    # ── PAGE 3: EXAMINATIONS & ATTENDANCE POLICY ──────────────────────────────
    story.append(Paragraph("ST. JUDE COLLEGE OF ENGINEERING & TECHNOLOGY", title_style))
    story.append(Paragraph("<b>[DEMONSTRATION SAMPLE]</b> - FICTIONAL COLLEGE REGULATIONS CREATED EXCLUSIVELY FOR AI RETRIEVAL BENCHMARKS.", banner_style))
    
    story.append(Paragraph("3. Academic Regulations, Attendance Condonation & Revaluation", section_style))
    story.append(Paragraph("Promulgated by the Office of the Controller of Examinations (COE) for all B.E. / B.Tech degree candidates.", body_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>3.1 Mandatory Attendance Criteria for End-Semester Examinations:</b>", body_style))
    story.append(Paragraph("Every student must secure a <b>minimum of 75% attendance</b> in each course across the semester to qualify for issuance of the examination hall ticket.", body_style))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>3.2 Attendance Condonation on Medical Grounds (65% to 74%):</b>", body_style))
    story.append(Paragraph("Students having attendance between <b>65% and 74%</b> due to hospitalisation, medical leave, or official college sports participation may apply for condonation. The condonation application must be submitted along with an approved Government Hospital Medical Certificate and payment of a <b>condonation fee of ₹1,500</b>. Students with attendance below 65% are NOT eligible for condonation under any circumstances and must repeat the semester.", body_style))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>3.3 End-Semester Revaluation & Script Photocopy Policy:</b>", body_style))
    story.append(Paragraph("Students desiring revaluation of examination answer scripts must apply within <b>10 days of results declaration</b>. The revaluation fee is <b>₹750 per subject</b>. In addition, students may request a photocopy of the evaluated answer script by remitting an administrative fee of <b>₹300 per script</b>.", body_style))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>3.4 Controller of Examinations Office Hours:</b>", body_style))
    story.append(Paragraph("For hall ticket grievances or mark sheet corrections, the COE enquiry window operates Monday to Friday from 09:30 AM to 04:30 PM in the Administrative Block, Second Floor.", body_style))

    doc.build(story)
    print(f"Generated demonstration PDF at: {PDF_PATH}")

if __name__ == "__main__":
    generate_pdf()
