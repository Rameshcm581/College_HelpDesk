#!/usr/bin/env python3
"""
========================================================================================
Comprehensive College Documents PDF Generator
St. Jude College of Engineering & Technology (Autonomous)
Academic Year: 2025–2026
========================================================================================
Generates all 12 basic institutional documents and 1 Master Compendium PDF
with exhaustive mock data, schedules, tables, contacts, rules, and procedures.
Every document has clean page boundaries, structured tables, and formal signatory blocks.
"""

import os
import pathlib
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
import pypdf

BASE_DIR = pathlib.Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "college_documents_pdf"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── CANVAS IMPLEMENTATIONS ────────────────────────────────────────────────────────────

class StandaloneNumberedCanvas(canvas.Canvas):
    """Draws running header and 'Page X of Y' for individual document PDFs."""
    def __init__(self, *args, **kwargs):
        super(StandaloneNumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont('Helvetica-Bold', 7)
        self.setFillColor(colors.HexColor('#475569'))

        # Running header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(36, 762, "ST. JUDE COLLEGE OF ENGINEERING & TECHNOLOGY (AUTONOMOUS)")
            self.drawRightString(576, 762, "OFFICIAL INSTITUTIONAL REGULATIONS (2025–2026)")
            self.setStrokeColor(colors.HexColor('#cbd5e1'))
            self.setLineWidth(0.6)
            self.line(36, 756, 576, 756)

        # Running footer (all pages)
        self.setStrokeColor(colors.HexColor('#cbd5e1'))
        self.setLineWidth(0.6)
        self.line(36, 36, 576, 36)
        self.setFont('Helvetica', 7)
        self.setFillColor(colors.HexColor('#64748b'))
        self.drawString(36, 25, "St. Jude College of Engineering & Technology | Approved by AICTE & UGC | ISO 9001:2015 Certified")
        self.drawRightString(576, 25, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


class MasterNumberedCanvas(canvas.Canvas):
    """Draws running header and unified continuous pagination for the Master Compendium."""
    def __init__(self, *args, **kwargs):
        super(MasterNumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        self.saveState()
        # Suppress headers and footers on cover page (Page 1)
        if self._pageNumber > 1:
            self.setFont('Helvetica-Bold', 7)
            self.setFillColor(colors.HexColor('#1e3a8a'))
            self.drawString(36, 762, "ST. JUDE COLLEGE OF ENGINEERING & TECHNOLOGY — MASTER COMPENDIUM 2025–2026")
            self.drawRightString(576, 762, "AUTONOMOUS INSTITUTIONAL POLICIES")
            self.setStrokeColor(colors.HexColor('#cbd5e1'))
            self.setLineWidth(0.6)
            self.line(36, 756, 576, 756)

            self.line(36, 36, 576, 36)
            self.setFont('Helvetica', 7)
            self.setFillColor(colors.HexColor('#64748b'))
            self.drawString(36, 25, "Master Administrative Handbook | Governing Council Ratification Ref: #42-B")
            self.drawRightString(576, 25, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


# ── STYLE FACTORY ─────────────────────────────────────────────────────────────────────

def create_styles():
    base_styles = getSampleStyleSheet()
    
    styles = {
        'CollegeHeader': ParagraphStyle(
            'CollegeHeader',
            parent=base_styles['Heading1'],
            fontSize=14,
            leading=17,
            textColor=colors.HexColor('#1e3a8a'),
            alignment=1, # Center
            fontName='Helvetica-Bold',
            spaceAfter=2
        ),
        'CollegeSubHeader': ParagraphStyle(
            'CollegeSubHeader',
            parent=base_styles['Normal'],
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor('#475569'),
            alignment=1,
            fontName='Helvetica-Bold',
            spaceAfter=2
        ),
        'DocBadge': ParagraphStyle(
            'DocBadge',
            parent=base_styles['Normal'],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#64748b'),
            alignment=1,
            fontName='Helvetica',
            spaceAfter=6
        ),
        'DocTitle': ParagraphStyle(
            'DocTitle',
            parent=base_styles['Heading1'],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor('#0f172a'),
            alignment=1,
            fontName='Helvetica-Bold',
            spaceAfter=5
        ),
        'BannerNotice': ParagraphStyle(
            'BannerNotice',
            parent=base_styles['Normal'],
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor('#991b1b'),
            backColor=colors.HexColor('#fef2f2'),
            borderColor=colors.HexColor('#fca5a5'),
            borderWidth=0.8,
            borderPadding=4,
            alignment=1,
            spaceAfter=6
        ),
        'H1': ParagraphStyle(
            'H1',
            parent=base_styles['Heading2'],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#1e3a8a'),
            fontName='Helvetica-Bold',
            spaceBefore=6,
            spaceAfter=3
        ),
        'H2': ParagraphStyle(
            'H2',
            parent=base_styles['Heading3'],
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor('#0f172a'),
            fontName='Helvetica-Bold',
            spaceBefore=4,
            spaceAfter=2
        ),
        'Body': ParagraphStyle(
            'Body',
            parent=base_styles['Normal'],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=3
        ),
        'Bullet': ParagraphStyle(
            'Bullet',
            parent=base_styles['Normal'],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#1e293b'),
            leftIndent=10,
            firstLineIndent=-6,
            spaceAfter=2.5
        ),
        'AlertBox': ParagraphStyle(
            'AlertBox',
            parent=base_styles['Normal'],
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor('#92400e'),
            backColor=colors.HexColor('#fffbeb'),
            borderColor=colors.HexColor('#fcd34d'),
            borderWidth=0.8,
            borderPadding=5,
            spaceBefore=3,
            spaceAfter=5
        ),
        'InfoBox': ParagraphStyle(
            'InfoBox',
            parent=base_styles['Normal'],
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor('#1e40af'),
            backColor=colors.HexColor('#eff6ff'),
            borderColor=colors.HexColor('#93c5fd'),
            borderWidth=0.8,
            borderPadding=5,
            spaceBefore=3,
            spaceAfter=5
        ),
        'SuccessBox': ParagraphStyle(
            'SuccessBox',
            parent=base_styles['Normal'],
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor('#065f46'),
            backColor=colors.HexColor('#ecfdf5'),
            borderColor=colors.HexColor('#6ee7b7'),
            borderWidth=0.8,
            borderPadding=5,
            spaceBefore=3,
            spaceAfter=5
        ),
        'TableHeader': ParagraphStyle(
            'TableHeader',
            parent=base_styles['Normal'],
            fontSize=7,
            leading=9.5,
            textColor=colors.white,
            fontName='Helvetica-Bold',
            alignment=1
        ),
        'TableCell': ParagraphStyle(
            'TableCell',
            parent=base_styles['Normal'],
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor('#1e293b')
        ),
        'TableCellCenter': ParagraphStyle(
            'TableCellCenter',
            parent=base_styles['Normal'],
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor('#1e293b'),
            alignment=1
        ),
        'TableCellBold': ParagraphStyle(
            'TableCellBold',
            parent=base_styles['Normal'],
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor('#0f172a'),
            fontName='Helvetica-Bold'
        ),
        'MetaKey': ParagraphStyle(
            'MetaKey',
            parent=base_styles['Normal'],
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor('#475569'),
            fontName='Helvetica-Bold'
        ),
        'MetaVal': ParagraphStyle(
            'MetaVal',
            parent=base_styles['Normal'],
            fontSize=7,
            leading=9.5,
            textColor=colors.HexColor('#0f172a')
        ),
        'SignatoryRole': ParagraphStyle(
            'SignatoryRole',
            parent=base_styles['Normal'],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor('#475569'),
            alignment=1
        ),
        'SignatoryName': ParagraphStyle(
            'SignatoryName',
            parent=base_styles['Normal'],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#0f172a'),
            fontName='Helvetica-Bold',
            alignment=1
        )
    }
    return styles

def build_pdf_document(filename, story):
    filepath = OUTPUT_DIR / filename
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=44,
        bottomMargin=44
    )
    doc.build(story, canvasmaker=StandaloneNumberedCanvas)
    return filepath

def get_header_story(styles, doc_id, doc_title, category, effective_date="July 01, 2025"):
    story = [
        Paragraph("ST. JUDE COLLEGE OF ENGINEERING & TECHNOLOGY", styles['CollegeHeader']),
        Paragraph("An Autonomous Institution | Affiliated to Anna University, Chennai | Approved by AICTE, New Delhi", styles['CollegeSubHeader']),
        Paragraph("Accredited by NAAC with 'A++' Grade (CGPA 3.68/4.00) | NBA Accredited Programmes | ISO 9001:2015 Certified", styles['DocBadge']),
        Paragraph("Campus: St. Jude Nagar, Rajiv Gandhi IT Expressway, OMR, Chennai – 600119, Tamil Nadu | Web: www.stjude.edu.in", styles['DocBadge']),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1e3a8a'), spaceAfter=5),
        Paragraph(doc_title.upper(), styles['DocTitle']),
    ]
    
    meta_data = [
        [
            Paragraph("<b>Document Ref:</b>", styles['MetaKey']),
            Paragraph(doc_id, styles['MetaVal']),
            Paragraph("<b>Category:</b>", styles['MetaKey']),
            Paragraph(category, styles['MetaVal'])
        ],
        [
            Paragraph("<b>Academic Year:</b>", styles['MetaKey']),
            Paragraph("2025–2026", styles['MetaVal']),
            Paragraph("<b>Effective Date:</b>", styles['MetaKey']),
            Paragraph(effective_date, styles['MetaVal'])
        ],
        [
            Paragraph("<b>Governing Approval:</b>", styles['MetaKey']),
            Paragraph("Governing Council Resolution #42-B", styles['MetaVal']),
            Paragraph("<b>Custodian Office:</b>", styles['MetaKey']),
            Paragraph("Office of the Principal & Academic Council", styles['MetaVal'])
        ]
    ]
    t = Table(meta_data, colWidths=[85, 185, 95, 175])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>OFFICIAL REGULATION NOTICE:</b> This institutional document forms an enforceable part of the student and administrative handbook for the 2025–2026 academic cycle. All students, faculty, and administrative staff are required to adhere to these statutory provisions.", styles['BannerNotice']))
    return story

def get_signatory_block(styles, prepared_role, prepared_name, verified_role, verified_name):
    sign_data = [
        [
            Paragraph("<b>Prepared &amp; Recommended By:</b><br/><br/><br/>", styles['SignatoryRole']),
            Paragraph("<b>Verified &amp; Certified By:</b><br/><br/><br/>", styles['SignatoryRole']),
            Paragraph("<b>Approved &amp; Issued By Authority:</b><br/><br/><br/>", styles['SignatoryRole'])
        ],
        [
            Paragraph(f"<b>{prepared_name}</b><br/>{prepared_role}", styles['SignatoryName']),
            Paragraph(f"<b>{verified_name}</b><br/>{verified_role}", styles['SignatoryName']),
            Paragraph("<b>Dr. S. Rajasekar, M.E., Ph.D.</b><br/>Principal &amp; Member Secretary, Governing Council", styles['SignatoryName'])
        ],
        [
            Paragraph("St. Jude College of Engineering &amp; Technology", styles['SignatoryRole']),
            Paragraph("St. Jude College of Engineering &amp; Technology", styles['SignatoryRole']),
            Paragraph("Official Institutional Seal / Autonomous", styles['SignatoryRole'])
        ]
    ]
    t_sign = Table(sign_data, colWidths=[180, 180, 180])
    t_sign.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('LINEBEFORE', (1,0), (1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('LINEBEFORE', (2,0), (2,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    return t_sign


# ======================================================================================
# 1. ACADEMIC REGULATIONS & CURRICULUM FRAMEWORK (2025–2026) - 2 PAGES
# ======================================================================================
def get_doc_01_story():
    styles = create_styles()
    story = get_header_story(
        styles,
        doc_id="SJCET/ACAD/REG/2025/01",
        doc_title="Undergraduate & Postgraduate Academic Regulations (CBCS) 2025–2026",
        category="Academic Affairs"
    )

    story.append(Paragraph("1. Preliminary Framework & Choice Based Credit System (CBCS)", styles['H1']))
    story.append(Paragraph("These Academic Regulations apply to all candidates admitted to Full-Time Undergraduate (B.E. / B.Tech.) and Postgraduate (M.E., M.Tech., M.B.A., M.C.A.) degree programmes at St. Jude College of Engineering & Technology commencing from the Academic Year 2025–2026.", styles['Body']))
    story.append(Paragraph("<b>1.1 Choice Based Credit System (CBCS):</b> Every programme follows a semester-based curriculum. A typical academic year consists of two semesters: Odd Semester (July to November) and Even Semester (January to May). One credit is assigned to 1 hour of lecture per week, 1 hour of tutorial per week, or 2 hours of laboratory/practical work per week.", styles['Bullet']))
    story.append(Paragraph("<b>1.2 Total Credit Requirements for Degree Award:</b>", styles['Bullet']))

    cred_data = [
        [Paragraph("Programme Level", styles['TableHeader']), Paragraph("Normal Entry Duration", styles['TableHeader']), Paragraph("Mandatory Minimum Credits", styles['TableHeader']), Paragraph("Maximum Completion Tenure", styles['TableHeader'])],
        [Paragraph("B.E. / B.Tech. (Regular)", styles['TableCellBold']), Paragraph("4 Years (8 Semesters)", styles['TableCellCenter']), Paragraph("162 Credits", styles['TableCellCenter']), Paragraph("6 Years (12 Semesters)", styles['TableCellCenter'])],
        [Paragraph("B.E. / B.Tech. (Lateral Entry)", styles['TableCellBold']), Paragraph("3 Years (6 Semesters)", styles['TableCellCenter']), Paragraph("124 Credits", styles['TableCellCenter']), Paragraph("5 Years (10 Semesters)", styles['TableCellCenter'])],
        [Paragraph("M.E. / M.Tech.", styles['TableCellBold']), Paragraph("2 Years (4 Semesters)", styles['TableCellCenter']), Paragraph("72 Credits", styles['TableCellCenter']), Paragraph("4 Years (8 Semesters)", styles['TableCellCenter'])],
        [Paragraph("Master of Business Admin (MBA)", styles['TableCellBold']), Paragraph("2 Years (4 Semesters)", styles['TableCellCenter']), Paragraph("102 Credits", styles['TableCellCenter']), Paragraph("4 Years (8 Semesters)", styles['TableCellCenter'])],
        [Paragraph("Master of Computer Applications (MCA)", styles['TableCellBold']), Paragraph("2 Years (4 Semesters)", styles['TableCellCenter']), Paragraph("86 Credits", styles['TableCellCenter']), Paragraph("4 Years (8 Semesters)", styles['TableCellCenter'])],
    ]
    t_cred = Table(cred_data, colWidths=[150, 110, 130, 150])
    t_cred.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_cred)
    story.append(Spacer(1, 4))

    story.append(Paragraph("2. Mandatory Attendance & Condonation Regulations", styles['H1']))
    story.append(Paragraph("A candidate shall be eligible to appear for the End Semester Examinations only if the student has secured a minimum of <b>75% overall attendance</b> in all registered courses taken together across the semester.", styles['Body']))
    story.append(Paragraph("<b>2.1 Condonation of Attendance Shortage (65% to 74.9%):</b> The Principal, on recommendation of the Head of the Department, may condone shortage of attendance up to 10% on genuine medical grounds (hospitalisation/prolonged illness) or official participation in national sports/cultural events with prior On-Duty approval. The student must pay a non-refundable Condonation Fee of <b>₹1,500</b> per semester to the Accounts Office along with authentic medical certificates within 3 working days of resumption.", styles['AlertBox']))
    story.append(Paragraph("<b>2.2 Barring from Examinations (<65% Attendance):</b> Students securing less than 65% overall attendance shall NOT be permitted to write the End Semester Examinations under any circumstances. They shall be deemed 'Detained for Lack of Attendance' and must repeat the semester in the subsequent academic year.", styles['Bullet']))

    # Clean Page Break to Page 2
    story.append(PageBreak())

    story.append(Paragraph("3. Evaluation Framework, Grading System & CGPA Computation", styles['H1']))
    story.append(Paragraph("Course evaluation consists of Continuous Internal Assessment (CIA: 40 Marks) and End Semester Examination (ESE: 60 Marks), totalling 100 Marks per course. The 10-point absolute grading scale is shown below:", styles['Body']))
    
    grade_data = [
        [Paragraph("Letter Grade", styles['TableHeader']), Paragraph("Grade Point", styles['TableHeader']), Paragraph("Mark Range (%)", styles['TableHeader']), Paragraph("Qualitative Performance Description", styles['TableHeader'])],
        [Paragraph("O", styles['TableCellCenter']), Paragraph("10.0", styles['TableCellCenter']), Paragraph("91 – 100", styles['TableCellCenter']), Paragraph("Outstanding (Exceptional mastery)", styles['TableCell'])],
        [Paragraph("A+", styles['TableCellCenter']), Paragraph("9.0", styles['TableCellCenter']), Paragraph("81 – 90", styles['TableCellCenter']), Paragraph("Excellent (Very high level of accomplishment)", styles['TableCell'])],
        [Paragraph("A", styles['TableCellCenter']), Paragraph("8.0", styles['TableCellCenter']), Paragraph("71 – 80", styles['TableCellCenter']), Paragraph("Very Good (Above average competence)", styles['TableCell'])],
        [Paragraph("B+", styles['TableCellCenter']), Paragraph("7.0", styles['TableCellCenter']), Paragraph("61 – 70", styles['TableCellCenter']), Paragraph("Good (Standard professional competence)", styles['TableCell'])],
        [Paragraph("B", styles['TableCellCenter']), Paragraph("6.0", styles['TableCellCenter']), Paragraph("55 – 60", styles['TableCellCenter']), Paragraph("Fair (Average performance)", styles['TableCell'])],
        [Paragraph("C", styles['TableCellCenter']), Paragraph("5.0", styles['TableCellCenter']), Paragraph("50 – 54", styles['TableCellCenter']), Paragraph("Pass (Satisfies minimum academic threshold)", styles['TableCell'])],
        [Paragraph("RA", styles['TableCellCenter']), Paragraph("0.0", styles['TableCellCenter']), Paragraph("< 50", styles['TableCellCenter']), Paragraph("Re-Appear (Failed to secure passing threshold)", styles['TableCell'])],
        [Paragraph("SA", styles['TableCellCenter']), Paragraph("0.0", styles['TableCellCenter']), Paragraph("Attendance Shortage", styles['TableCellCenter']), Paragraph("Shortage of Attendance (Mandatory repetition)", styles['TableCell'])],
        [Paragraph("W", styles['TableCellCenter']), Paragraph("0.0", styles['TableCellCenter']), Paragraph("Withdrawn", styles['TableCellCenter']), Paragraph("Permitted official withdrawal from examination", styles['TableCell'])],
    ]
    t_grade = Table(grade_data, colWidths=[65, 65, 95, 315])
    t_grade.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_grade)
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>3.1 CGPA Computation Formula:</b> CGPA = Σ(Credit_i × GradePoint_i) / Σ(Credit_i), computed across all successfully cleared courses.", styles['Body']))
    story.append(Paragraph("<b>3.2 Classification of Degree Awarded:</b><br/>"
                           "• <b>First Class with Distinction:</b> CGPA ≥ 8.50 with zero history of arrears, passed within normal duration.<br/>"
                           "• <b>First Class:</b> CGPA ≥ 6.50 passed within normal duration or plus 1 additional year.<br/>"
                           "• <b>Second Class:</b> All other students securing CGPA ≥ 5.00 within maximum tenure.", styles['Bullet']))

    story.append(Paragraph("4. Honors & Minor Degree Regulations", styles['H1']))
    story.append(Paragraph("Students maintaining a minimum CGPA of 7.50 without arrears up to Semester IV may opt for B.E. (Honors) in their parent discipline or B.E. with Minor Specialisation (e.g. AI, Cyber Security, FinTech) by successfully earning <b>18 additional credits</b> through approved NPTEL / SWAYAM / Departmental advanced electives.", styles['Body']))
    story.append(Spacer(1, 6))

    # Formal Signatory Block
    story.append(get_signatory_block(
        styles,
        prepared_role="Dean of Academic Affairs",
        prepared_name="Dr. V. Chandrasekaran, Ph.D.",
        verified_role="Vice Principal & Academic Council Member",
        verified_name="Prof. M. Kalyanasundaram, M.E."
    ))

    return story

def generate_doc_01():
    return build_pdf_document("01_academic_regulations_2025_2026.pdf", get_doc_01_story())


# ======================================================================================
# 2. ADMISSIONS, FEE STRUCTURE & REFUND POLICY (2025–2026) - 2 PAGES
# ======================================================================================
def get_doc_02_story():
    styles = create_styles()
    story = get_header_story(
        styles,
        doc_id="SJCET/ADM/FEES/2025/02",
        doc_title="Undergraduate & Postgraduate Admissions, Fee Schedule & Refund Policy (2025–2026)",
        category="Admissions & Finance"
    )

    story.append(Paragraph("1. Admission Quotas & Eligibility Criteria", styles['H1']))
    story.append(Paragraph("Admissions are conducted strictly under two categories pursuant to Government of Tamil Nadu Higher Education guidelines: <b>Government Single Window Quota (TNEA) - 65%</b> and <b>Management Quota (Consortium of Self-Financing Colleges) - 35%</b>.", styles['Body']))
    story.append(Paragraph("<b>1.1 Minimum Qualifying Cutoff Marks in HSC (10+2) Mathematics, Physics & Chemistry:</b><br/>"
                           "• General Category (OC): Minimum 50.0% aggregate<br/>"
                           "• Backward Classes (BC / BCM): Minimum 45.0% aggregate<br/>"
                           "• Most Backward Classes & DNC (MBC/DNC): Minimum 40.0% aggregate<br/>"
                           "• Scheduled Castes & Scheduled Tribes (SC/SCA/ST): Minimum 40.0% aggregate", styles['Bullet']))

    story.append(Paragraph("2. Approved Annual Tuition & Ancillary Fee Structure (2025–2026)", styles['H1']))
    story.append(Paragraph("The following annual fee structure was determined and approved by the Fee Fixation Committee of Tamil Nadu and the Institutional Governing Body:", styles['Body']))

    fee_data = [
        [Paragraph("Degree & Department", styles['TableHeader']), Paragraph("Tuition Fee (Annual)", styles['TableHeader']), Paragraph("Special Lab & Computing Fee", styles['TableHeader']), Paragraph("Library, Internet & Dev Fund", styles['TableHeader']), Paragraph("Total Annual Fee (Govt Quota)", styles['TableHeader']), Paragraph("Management Quota", styles['TableHeader'])],
        [Paragraph("B.E. Computer Science & Engineering", styles['TableCellBold']), Paragraph("₹85,000", styles['TableCellCenter']), Paragraph("₹15,000", styles['TableCellCenter']), Paragraph("₹10,000", styles['TableCellCenter']), Paragraph("₹1,10,000", styles['TableCellCenter']), Paragraph("₹1,65,000", styles['TableCellCenter'])],
        [Paragraph("B.Tech. Artificial Intelligence & Data Science", styles['TableCellBold']), Paragraph("₹90,000", styles['TableCellCenter']), Paragraph("₹18,000", styles['TableCellCenter']), Paragraph("₹10,000", styles['TableCellCenter']), Paragraph("₹1,18,000", styles['TableCellCenter']), Paragraph("₹1,75,000", styles['TableCellCenter'])],
        [Paragraph("B.Tech. Information Technology", styles['TableCellBold']), Paragraph("₹85,000", styles['TableCellCenter']), Paragraph("₹15,000", styles['TableCellCenter']), Paragraph("₹10,000", styles['TableCellCenter']), Paragraph("₹1,10,000", styles['TableCellCenter']), Paragraph("₹1,60,000", styles['TableCellCenter'])],
        [Paragraph("B.E. Electronics & Communication", styles['TableCellBold']), Paragraph("₹80,000", styles['TableCellCenter']), Paragraph("₹12,000", styles['TableCellCenter']), Paragraph("₹10,000", styles['TableCellCenter']), Paragraph("₹1,02,000", styles['TableCellCenter']), Paragraph("₹1,45,000", styles['TableCellCenter'])],
        [Paragraph("B.E. Electrical & Electronics Engineering", styles['TableCellBold']), Paragraph("₹75,000", styles['TableCellCenter']), Paragraph("₹12,000", styles['TableCellCenter']), Paragraph("₹8,000", styles['TableCellCenter']), Paragraph("₹95,000", styles['TableCellCenter']), Paragraph("₹1,30,000", styles['TableCellCenter'])],
        [Paragraph("B.E. Mechanical Engineering", styles['TableCellBold']), Paragraph("₹75,000", styles['TableCellCenter']), Paragraph("₹10,000", styles['TableCellCenter']), Paragraph("₹8,000", styles['TableCellCenter']), Paragraph("₹93,000", styles['TableCellCenter']), Paragraph("₹1,25,000", styles['TableCellCenter'])],
        [Paragraph("B.E. Civil Engineering", styles['TableCellBold']), Paragraph("₹70,000", styles['TableCellCenter']), Paragraph("₹8,000", styles['TableCellCenter']), Paragraph("₹7,000", styles['TableCellCenter']), Paragraph("₹85,000", styles['TableCellCenter']), Paragraph("₹1,15,000", styles['TableCellCenter'])],
        [Paragraph("Master of Business Administration (MBA)", styles['TableCellBold']), Paragraph("₹65,000", styles['TableCellCenter']), Paragraph("₹10,000", styles['TableCellCenter']), Paragraph("₹10,000", styles['TableCellCenter']), Paragraph("₹85,000", styles['TableCellCenter']), Paragraph("₹1,35,000", styles['TableCellCenter'])],
        [Paragraph("Master of Computer Applications (MCA)", styles['TableCellBold']), Paragraph("₹60,000", styles['TableCellCenter']), Paragraph("₹12,000", styles['TableCellCenter']), Paragraph("₹8,000", styles['TableCellCenter']), Paragraph("₹80,000", styles['TableCellCenter']), Paragraph("₹1,25,000", styles['TableCellCenter'])],
    ]
    t_fee = Table(fee_data, colWidths=[135, 75, 75, 75, 90, 90])
    t_fee.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_fee)
    story.append(Spacer(1, 4))
    story.append(Paragraph("<i>*Note: A one-time Institutional Caution Deposit of <b>₹5,000</b> (fully refundable upon completion of degree) is collected at the time of initial admission across all streams.</i>", styles['DocBadge']))

    # Clean Page Break to Page 2
    story.append(PageBreak())

    story.append(Paragraph("3. Payment Deadlines & Late Fine Slabs", styles['H1']))
    story.append(Paragraph("• <b>Odd Semester (Sem 1, 3, 5, 7):</b> Last date for fee remittance without fine is <b>July 15, 2025</b>.<br/>"
                           "• <b>Even Semester (Sem 2, 4, 6, 8):</b> Last date for fee remittance without fine is <b>December 15, 2025</b>.<br/>"
                           "• <b>Grace Period (Days 1 to 7 after due date):</b> Zero penalty.<br/>"
                           "• <b>Slab 1 (Days 8 to 15 after due date):</b> Late fine of <b>₹500</b>.<br/>"
                           "• <b>Slab 2 (Days 16 to 30 after due date):</b> Late fine of <b>₹1,500</b>.<br/>"
                           "• <b>Beyond 30 Days:</b> Student portal access and attendance logging are suspended until clearance.", styles['AlertBox']))

    story.append(Paragraph("4. Statutory Fee Refund & Cancellation Policy (UGC Mandated)", styles['H1']))
    story.append(Paragraph("In strict compliance with UGC Notification on Fee Refund, the refund schedule for formal cancellation is as follows:", styles['Body']))

    ref_data = [
        [Paragraph("S.No", styles['TableHeader']), Paragraph("Percentage of Refund", styles['TableHeader']), Paragraph("Timeline / Notice Period Before Formally Announced Last Date", styles['TableHeader']), Paragraph("Deduction / Processing Charges", styles['TableHeader'])],
        [Paragraph("1", styles['TableCellCenter']), Paragraph("100%", styles['TableCellBold']), Paragraph("15 days or more before the formally announced last date of admission", styles['TableCell']), Paragraph("₹1,000 maximum processing fee deducted", styles['TableCell'])],
        [Paragraph("2", styles['TableCellCenter']), Paragraph("90%", styles['TableCellBold']), Paragraph("Less than 15 days before the formally announced last date of admission", styles['TableCell']), Paragraph("10% of aggregate fees deducted", styles['TableCell'])],
        [Paragraph("3", styles['TableCellCenter']), Paragraph("80%", styles['TableCellBold']), Paragraph("15 days or less after the formally announced last date of admission", styles['TableCell']), Paragraph("20% of aggregate fees deducted", styles['TableCell'])],
        [Paragraph("4", styles['TableCellCenter']), Paragraph("50%", styles['TableCellBold']), Paragraph("30 days or less, but more than 15 days after last date of admission", styles['TableCell']), Paragraph("50% of aggregate fees deducted", styles['TableCell'])],
        [Paragraph("5", styles['TableCellCenter']), Paragraph("0% (Nil)", styles['TableCellBold']), Paragraph("More than 30 days after formally announced last date of admission", styles['TableCell']), Paragraph("Only Caution Deposit refunded", styles['TableCell'])],
    ]
    t_ref = Table(ref_data, colWidths=[30, 90, 230, 190])
    t_ref.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_ref)
    story.append(Spacer(1, 4))

    story.append(Paragraph("5. Payment Gateways & Educational Loan Facilitation", styles['H1']))
    story.append(Paragraph("Tuition fees can be paid seamlessly via the College ERP Portal (Razorpay / Net Banking / UPI) or via direct NEFT/RTGS to <b>Canara Bank, St. Jude College Branch (A/C: 110024568801, IFSC: CNRB0002845)</b>. The Admissions Office issues official Bonafide and Fee Estimate Certificates within 24 hours for bank loan sanctions.", styles['Body']))
    story.append(Spacer(1, 6))

    # Formal Signatory Block
    story.append(get_signatory_block(
        styles,
        prepared_role="Director of Admissions",
        prepared_name="Prof. R. Soundararajan, M.Tech.",
        verified_role="Finance Officer & Registrar",
        verified_name="Mr. K. Natarajan, M.Com., FCA"
    ))

    return story

def generate_doc_02():
    return build_pdf_document("02_admissions_and_fee_structure_2025_2026.pdf", get_doc_02_story())


# ======================================================================================
# 3. EXAMINATION & EVALUATION MANUAL (2025–2026) - 1 PAGE
# ======================================================================================
def get_doc_03_story():
    styles = create_styles()
    story = get_header_story(
        styles,
        doc_id="SJCET/COE/EXAM/2025/03",
        doc_title="Standard Operating Procedures & Evaluation Manual (2025–2026)",
        category="Office of the Controller of Examinations (CoE)"
    )

    story.append(Paragraph("1. Examination Registration & Hall Ticket Issuance", styles['H1']))
    story.append(Paragraph("• <b>Hall Ticket Eligibility:</b> Generated electronically 7 days prior to examination commencement for all students fulfilling: (a) minimum 75% attendance requirement or approved condonation, (b) clearance of tuition & hostel dues, and (c) completed course registration.<br/>"
                           "• <b>Mandatory Entry Requirements:</b> Students must produce physical Hall Ticket along with College RFID Identity Card at the examination entrance. Identity cards must be worn visibly around the neck at all times.", styles['Body']))

    story.append(Paragraph("2. Examination Hall Discipline & Malpractice Penalties", styles['H1']))
    
    mal_data = [
        [Paragraph("Category", styles['TableHeader']), Paragraph("Nature of Malpractice / Infraction", styles['TableHeader']), Paragraph("Statutory Disciplinary Penalty", styles['TableHeader'])],
        [Paragraph("Category I", styles['TableCellBold']), Paragraph("Possession of unauthorized handwritten/printed notes, formula sheets, or writing on body/clothes without copying attempt.", styles['TableCell']), Paragraph("Cancellation of the specific course examination; student marked 'RA' in that subject.", styles['TableCell'])],
        [Paragraph("Category II", styles['TableCellBold']), Paragraph("Possession of electronic gadgets: Smartwatches, mobile phones, programmable calculators, Bluetooth earpieces, or memory storage devices.", styles['TableCell']), Paragraph("Confiscation of device, cancellation of that examination, and penalty fine of ₹2,500.", styles['TableCell'])],
        [Paragraph("Category III", styles['TableCellBold']), Paragraph("Detected copying from notes, digital devices, or peer copying / passing answer material in the hall.", styles['TableCell']), Paragraph("Cancellation of ALL registered examinations in the current semester; debarment from 1 subsequent semester.", styles['TableCell'])],
        [Paragraph("Category IV", styles['TableCellBold']), Paragraph("Impersonation, tampering with answer booklets, bar-code destruction, or verbal assault/intimidation of invigilating staff.", styles['TableCell']), Paragraph("Immediate rustication for 2 academic years (4 semesters) and registration of Police FIR.", styles['TableCell'])],
    ]
    t_mal = Table(mal_data, colWidths=[65, 235, 240])
    t_mal.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_mal)
    story.append(Spacer(1, 3))

    story.append(Paragraph("3. Transparency, Photocopy & Revaluation Procedures", styles['H1']))
    story.append(Paragraph("• <b>Step 1 - Application for Answer Script Photocopy:</b> Online application within <b>7 calendar days</b> of results announcement, fee: <b>₹300 per subject</b>.<br/>"
                           "• <b>Step 2 - Application for Revaluation:</b> Upon reviewing script with Class Advisor, file for Revaluation within <b>10 calendar days</b> of receiving photocopy, non-refundable fee: <b>₹750 per subject</b>.<br/>"
                           "• <b>Step 3 - Challenge Valuation:</b> Challenge valuation by External University Expert within 5 days, remitting <b>₹2,000</b>. If marks gain is ≥15%, 50% fee is refunded.", styles['InfoBox']))

    story.append(Paragraph("4. Arrear & Special Supplementary Examinations", styles['H1']))
    story.append(Paragraph("• Regular odd/even arrear examination fee: <b>₹500 per theoretical paper</b> and <b>₹600 per practical examination</b>.<br/>"
                           "• <b>Special Supplementary Exams:</b> Conducted annually in July exclusively for final-year graduating students possessing up to a maximum of 2 active arrears, enabling seamless graduation.", styles['Body']))
    story.append(Spacer(1, 4))

    # Formal Signatory Block
    story.append(get_signatory_block(
        styles,
        prepared_role="Deputy Controller of Examinations",
        prepared_name="Dr. K. Ananthasivan, Ph.D.",
        verified_role="Controller of Examinations (CoE)",
        verified_name="Dr. T. Sivaraman, M.E., Ph.D."
    ))

    return story

def generate_doc_03():
    return build_pdf_document("03_examinations_and_evaluation_manual_2025_2026.pdf", get_doc_03_story())


# ======================================================================================
# 4. HOSTEL & RESIDENTIAL LIFE HANDBOOK (2025–2026) - 1 PAGE
# ======================================================================================
def get_doc_04_story():
    styles = create_styles()
    story = get_header_story(
        styles,
        doc_id="SJCET/HOSTEL/POL/2025/04",
        doc_title="Hostel & Residential Life Regulations, Mess Charges & Safety Manual (2025–2026)",
        category="Student Residential Services"
    )

    story.append(Paragraph("1. Accommodation Infrastructure & Annual Charges", styles['H1']))
    story.append(Paragraph("St. Jude College provides separate residential hostels for Men (Cauvery, Krishna & Godavari Blocks) and Women (Ganga, Yamuna & Narmada Blocks) under continuous warden supervision.", styles['Body']))

    h_data = [
        [Paragraph("Occupancy Type", styles['TableHeader']), Paragraph("Room Rent & Utilities", styles['TableHeader']), Paragraph("Annual Veg/Non-Veg Mess Fee", styles['TableHeader']), Paragraph("Amenities & Wi-Fi", styles['TableHeader']), Paragraph("Caution Deposit (Refundable)", styles['TableHeader']), Paragraph("Total Annual Fee", styles['TableHeader'])],
        [Paragraph("4-Sharing (Non-AC)", styles['TableCellBold']), Paragraph("₹30,000", styles['TableCellCenter']), Paragraph("₹45,000", styles['TableCellCenter']), Paragraph("₹6,000", styles['TableCellCenter']), Paragraph("₹5,000", styles['TableCellCenter']), Paragraph("₹86,000", styles['TableCellBold'])],
        [Paragraph("2-Sharing (Non-AC)", styles['TableCellBold']), Paragraph("₹42,000", styles['TableCellCenter']), Paragraph("₹45,000", styles['TableCellCenter']), Paragraph("₹6,000", styles['TableCellCenter']), Paragraph("₹5,000", styles['TableCellCenter']), Paragraph("₹98,000", styles['TableCellBold'])],
        [Paragraph("4-Sharing (AC Deluxe)", styles['TableCellBold']), Paragraph("₹48,000", styles['TableCellCenter']), Paragraph("₹45,000", styles['TableCellCenter']), Paragraph("₹10,000", styles['TableCellCenter']), Paragraph("₹5,000", styles['TableCellCenter']), Paragraph("₹1,08,000", styles['TableCellBold'])],
        [Paragraph("2-Sharing (AC Deluxe)", styles['TableCellBold']), Paragraph("₹65,000", styles['TableCellCenter']), Paragraph("₹45,000", styles['TableCellCenter']), Paragraph("₹10,000", styles['TableCellCenter']), Paragraph("₹5,000", styles['TableCellCenter']), Paragraph("₹1,25,000", styles['TableCellBold'])],
    ]
    t_h = Table(h_data, colWidths=[110, 85, 95, 80, 85, 85])
    t_h.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_h)
    story.append(Spacer(1, 3))

    story.append(Paragraph("2. Dining Hall Timings & Mess Rebate Policy", styles['H1']))
    story.append(Paragraph("• <b>Breakfast:</b> 07:15 AM – 08:30 AM | <b>Lunch:</b> 12:30 PM – 02:00 PM | <b>Evening Snacks:</b> 04:45 PM – 05:45 PM | <b>Dinner:</b> 07:30 PM – 09:00 PM.<br/>"
                           "• <b>Mess Rebate Rules:</b> Continuous absence of <b>5 or more days</b> on approved leave entitles a rebate of <b>₹120/day</b>, upon 48-hour prior notification.", styles['Body']))

    story.append(Paragraph("3. Curfew Hours, Biometric Roll Call & Outing Passes", styles['H1']))
    story.append(Paragraph("• <b>Curfew & Gate Closure:</b> Main hostel gates close strictly at <b>08:30 PM</b> on weekdays and <b>09:00 PM</b> on Sundays.<br/>"
                           "• <b>Mandatory Biometric Attendance:</b> Conducted every evening between <b>08:45 PM and 09:15 PM</b>. Failure to punch leads to automated parent SMS.<br/>"
                           "• <b>Digital Outing Pass:</b> Day outings require app approval; overnight leave requires parent authorization via automated SMS OTP.", styles['AlertBox']))

    story.append(Paragraph("4. Prohibited Items & Medical Emergency", styles['H1']))
    story.append(Paragraph("• <b>Electrical Ban:</b> Immersion heaters, hot plates, induction cookers are banned; violation attracts <b>₹1,000 fine</b>.<br/>"
                           "• <b>Substance Abuse:</b> Zero tolerance for alcohol/tobacco/narcotics: immediate expulsion and police notification.<br/>"
                           "• <b>Emergency Health Room:</b> 24/7 Dispensary in Cauvery Block. Emergency contact: <b>044-2456-8800 (Extn 108)</b>.", styles['Body']))
    story.append(Spacer(1, 4))

    # Formal Signatory Block
    story.append(get_signatory_block(
        styles,
        prepared_role="Chief Warden (Men's Hostel)",
        prepared_name="Dr. K. Arulmozhi, Prof/Mech",
        verified_role="Chief Warden (Women's Hostel)",
        verified_name="Dr. V. Revathy, Prof/ECE"
    ))

    return story

def generate_doc_04():
    return build_pdf_document("04_hostel_and_residential_life_handbook_2025_2026.pdf", get_doc_04_story())


# ======================================================================================
# 5. SCHOLARSHIPS & FINANCIAL AID POLICY (2025–2026) - 1 PAGE
# ======================================================================================
def get_doc_05_story():
    styles = create_styles()
    story = get_header_story(
        styles,
        doc_id="SJCET/SCHOL/CIRC/2025/05",
        doc_title="Institutional & Governmental Scholarship Schemes and Financial Aid (2025–2026)",
        category="Student Welfare & Financial Aid"
    )

    story.append(Paragraph("1. Institutional Merit-Cum-Means Scholarships", styles['H1']))
    story.append(Paragraph("St. Jude College allocates ₹1.2 Crores annually under the St. Jude Educational Trust to reward academic excellence and assist financially challenged students.", styles['Body']))

    sch_data = [
        [Paragraph("Scholarship Title", styles['TableHeader']), Paragraph("Eligibility Criteria", styles['TableHeader']), Paragraph("Concession / Benefit Granted", styles['TableHeader']), Paragraph("Quota Available", styles['TableHeader'])],
        [Paragraph("Founder's Premier Merit Award", styles['TableCellBold']), Paragraph("HSC / TNEA Aggregate score ≥ 95.0% or Top 10 college entrance ranks", styles['TableCell']), Paragraph("100% Tuition Fee Waiver across all 4 years", styles['TableCell']), Paragraph("15 Students / Year", styles['TableCellCenter'])],
        [Paragraph("Academic Excellence Tier-II", styles['TableCellBold']), Paragraph("HSC / TNEA Aggregate score between 90.0% and 94.9%", styles['TableCell']), Paragraph("50% Tuition Fee Waiver across all 4 years", styles['TableCell']), Paragraph("30 Students / Year", styles['TableCellCenter'])],
        [Paragraph("Sports Quota Excellence Award", styles['TableCellBold']), Paragraph("Gold/Silver medalist in National / Inter-University championship", styles['TableCell']), Paragraph("100% Tuition Fee + 100% Hostel & Mess Waiver", styles['TableCell']), Paragraph("10 Students / Year", styles['TableCellCenter'])],
        [Paragraph("State Sports Representation", styles['TableCellBold']), Paragraph("Represented Tamil Nadu in SGFI / National Games", styles['TableCell']), Paragraph("50% Tuition Fee Waiver", styles['TableCell']), Paragraph("15 Students / Year", styles['TableCellCenter'])],
        [Paragraph("Alumni Bereavement Endowment", styles['TableCellBold']), Paragraph("Sudden demise of earning parent during student's tenure", styles['TableCell']), Paragraph("Full fee sponsorship until degree completion", styles['TableCell']), Paragraph("Discretionary", styles['TableCellCenter'])],
    ]
    t_sch = Table(sch_data, colWidths=[115, 165, 170, 90])
    t_sch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_sch)
    story.append(Spacer(1, 3))

    story.append(Paragraph("2. Government Welfare Scholarships & Fee Concessions", styles['H1']))
    story.append(Paragraph("• <b>First Generation Graduate Concession (Govt of Tamil Nadu):</b> Annual statutory tuition fee waiver of <b>₹25,000</b>. Tahsildar-issued certificate required.<br/>"
                           "• <b>Post-Matric Scholarship (SC / SCA / ST Welfare):</b> Full tuition fee waiver and maintenance allowance (family income < <b>₹2,50,000</b>).<br/>"
                           "• <b>BC / MBC / DNC Welfare Scholarship:</b> Maintenance grant and partial fee support (family income < <b>₹2,00,000</b>).<br/>"
                           "• <b>Pudhumai Penn Scheme:</b> Monthly stipend of <b>₹1,000</b> for girl students who studied in Government schools from Classes VI to XII.", styles['SuccessBox']))

    story.append(Paragraph("3. Application Deadlines & Documentation Checklist", styles['H1']))
    story.append(Paragraph("• <b>Deadline:</b> Submit completed forms on or before <b>August 25, 2025</b> to Student Welfare Section, Room #105, Admin Block.<br/>"
                           "• <b>Mandatory Enclosures:</b> Income Certificate (<6 months old), Community Certificate, 10th & 12th Marksheets, First Graduate Certificate, Aadhaar-linked Bank Passbook.", styles['AlertBox']))
    story.append(Spacer(1, 4))

    # Formal Signatory Block
    story.append(get_signatory_block(
        styles,
        prepared_role="Nodal Scholarship Officer",
        prepared_name="Mr. P. Vijayaraghavan, M.A.",
        verified_role="Dean of Student Welfare",
        verified_name="Dr. N. Sundarapandian, M.E., Ph.D."
    ))

    return story

def generate_doc_05():
    return build_pdf_document("05_scholarships_and_financial_aid_circular_2025_2026.pdf", get_doc_05_story())


# ======================================================================================
# 6. TRAINING, INTERNSHIP & CAMPUS PLACEMENT POLICY (2025–2026) - 1 PAGE
# ======================================================================================
def get_doc_06_story():
    styles = create_styles()
    story = get_header_story(
        styles,
        doc_id="SJCET/CDC/PLACE/2025/06",
        doc_title="Centre for Career Development & Campus Placement Policy (2025–2026)",
        category="Career Development Centre (CDC)"
    )

    story.append(Paragraph("1. Eligibility Criteria for Placement Registration", styles['H1']))
    story.append(Paragraph("• <b>Academic Cutoff:</b> Minimum Cumulative Grade Point Average of <b>6.50 CGPA</b> with <b>zero standing arrears</b> at the time of drive registration.<br/>"
                           "• <b>Training Attendance Mandate:</b> Students must maintain a minimum of <b>85% attendance</b> in soft-skills, quantitative aptitude, and coding bootcamps. Students below 85% attendance will be disqualified from campus drives.", styles['AlertBox']))

    story.append(Paragraph("2. Corporate Recruitment Tiers & Offer Categories", styles['H1']))
    
    tier_data = [
        [Paragraph("Recruitment Tier", styles['TableHeader']), Paragraph("Cost to Company (CTC) Range", styles['TableHeader']), Paragraph("Offer Classification", styles['TableHeader']), Paragraph("Upgrade Policy", styles['TableHeader'])],
        [Paragraph("Tier-3 (Mass / Standard)", styles['TableCellBold']), Paragraph("₹3.50 LPA to ₹6.50 LPA", styles['TableCellCenter']), Paragraph("Core / IT Service", styles['TableCell']), Paragraph("Eligible to appear for Tier-2 and Tier-1", styles['TableCell'])],
        [Paragraph("Tier-2 (Dream Offer)", styles['TableCellBold']), Paragraph("₹6.51 LPA to ₹12.00 LPA", styles['TableCellCenter']), Paragraph("Dream Category", styles['TableCell']), Paragraph("Eligible to appear only for Tier-1 Super Dream", styles['TableCell'])],
        [Paragraph("Tier-1 (Super Dream)", styles['TableCellBold']), Paragraph("Above ₹12.00 LPA", styles['TableCellCenter']), Paragraph("Super Dream Category", styles['TableCell']), Paragraph("Final offer; placed out of recruitment process", styles['TableCell'])],
    ]
    t_tier = Table(tier_data, colWidths=[110, 115, 115, 200])
    t_tier.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_tier)
    story.append(Spacer(1, 3))

    story.append(Paragraph("3. Single Offer Rule & Dream Upgrade Regulations", styles['H1']))
    story.append(Paragraph("• <b>One Student - One Offer Principle:</b> Securing a Tier-3 offer automatically withdraws the student from all other Tier-3 drives to give chances to unplaced peers.<br/>"
                           "• <b>Dream Offer Upgrade:</b> Holding a Tier-3 offer allows registering for Tier-2. If Tier-2 is secured, the Tier-3 offer must be formally surrendered within 48 hours.<br/>"
                           "• <b>Absenteeism Penalty:</b> Registering for a drive and failing to attend without approval results in <b>debarment from the next 2 campus recruitment drives</b>.", styles['Body']))

    story.append(Paragraph("4. Summer Internship & Academic Credit Transfer", styles['H1']))
    story.append(Paragraph("Undergraduate students must complete a mandatory <b>6 to 8-week industrial internship</b> during the vacation between Semesters VI and VII (2 academic credits). High-stipend corporate interns (>₹25k/mo) may pursue an 8th semester full-time Industry Project carrying 10 credits.", styles['InfoBox']))
    story.append(Spacer(1, 4))

    # Formal Signatory Block
    story.append(get_signatory_block(
        styles,
        prepared_role="Head, Centre for Career Development",
        prepared_name="Prof. J. Senthil Kumar, M.E.",
        verified_role="Dean of Industry Relations & Placements",
        verified_name="Dr. E. Muralidharan, Ph.D."
    ))

    return story

def generate_doc_06():
    return build_pdf_document("06_training_internship_and_placement_policy_2025_2026.pdf", get_doc_06_story())


# ======================================================================================
# 7. CODE OF CONDUCT, ETHICS & ANTI-RAGGING POLICY (2025–2026) - 1 PAGE
# ======================================================================================
def get_doc_07_story():
    styles = create_styles()
    story = get_header_story(
        styles,
        doc_id="SJCET/DISC/RAG/2025/07",
        doc_title="Code of Conduct, Campus Ethics & Statutory Anti-Ragging Policy (2025–2026)",
        category="Discipline & Statutory Compliance"
    )

    story.append(Paragraph("1. Statutory Anti-Ragging Mandate (Supreme Court & UGC Regulations)", styles['H1']))
    story.append(Paragraph("In accordance with Supreme Court directives and UGC Regulations 2009, <b>RAGGING IS STRICTLY PROHIBITED AND CONSTITUTES A COGNIZABLE CRIMINAL OFFENCE</b>.", styles['BannerNotice']))
    story.append(Paragraph("<b>Penalties for Ragging:</b> Immediate suspension, cancellation of admission, withholding results/scholarships, permanent hostel expulsion, and <b>mandatory Police FIR within 24 hours</b> under TN Prohibition of Ragging Act, 1997 (rigorous imprisonment up to 2 years and ₹10,000 fine).", styles['AlertBox']))

    story.append(Paragraph("2. Institutional Anti-Ragging Squad Roster & 24/7 Helplines", styles['H1']))
    
    rag_data = [
        [Paragraph("Designation / Office", styles['TableHeader']), Paragraph("Name of Member", styles['TableHeader']), Paragraph("Official Phone Extension / Mobile", styles['TableHeader']), Paragraph("Email Address", styles['TableHeader'])],
        [Paragraph("Anti-Ragging Chairperson", styles['TableCellBold']), Paragraph("Dr. S. Rajasekar, Principal", styles['TableCell']), Paragraph("+91 94440 12345 / Extn 101", styles['TableCellCenter']), Paragraph("principal@stjude.edu.in", styles['TableCell'])],
        [Paragraph("Anti-Ragging Squad Head", styles['TableCellBold']), Paragraph("Prof. M. Kalyanasundaram, VP", styles['TableCell']), Paragraph("+91 98401 56789 / Extn 104", styles['TableCellCenter']), Paragraph("viceprincipal@stjude.edu.in", styles['TableCell'])],
        [Paragraph("Chief Warden (Men's Hostel)", styles['TableCellBold']), Paragraph("Dr. K. Arulmozhi, Prof/Mech", styles['TableCell']), Paragraph("+91 94451 22334 / Extn 201", styles['TableCellCenter']), Paragraph("warden.men@stjude.edu.in", styles['TableCell'])],
        [Paragraph("Chief Warden (Women's Hostel)", styles['TableCellBold']), Paragraph("Dr. V. Revathy, Prof/ECE", styles['TableCell']), Paragraph("+91 94451 22335 / Extn 202", styles['TableCellCenter']), Paragraph("warden.women@stjude.edu.in", styles['TableCell'])],
        [Paragraph("Local Police Station", styles['TableCellBold']), Paragraph("SHO, Semmancheri Police Station", styles['TableCell']), Paragraph("044-2450-0100 / 100", styles['TableCellCenter']), Paragraph("sho.semmancheri@tnpolice.gov.in", styles['TableCell'])],
        [Paragraph("UGC National Toll-Free Helpline", styles['TableCellBold']), Paragraph("National Anti-Ragging Cell", styles['TableCell']), Paragraph("<b>1800-180-5522 (24x7 Free)</b>", styles['TableCellCenter']), Paragraph("helpline@antiragging.in", styles['TableCell'])],
    ]
    t_rag = Table(rag_data, colWidths=[125, 125, 145, 145])
    t_rag.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_rag)
    story.append(Spacer(1, 3))

    story.append(Paragraph("3. Campus Decorum, RFID Mandate & Substance-Free Campus", styles['H1']))
    story.append(Paragraph("• <b>RFID Student ID Mandate:</b> Students must wear their official barcode-enabled RFID lanyard ID card at all times inside the college premises.<br/>"
                           "• <b>Vehicular Traffic & Speed:</b> Student two-wheelers must have valid licenses, helmets, and park in designated Bay 'D'. Speed limit inside campus is <b>20 km/h</b>.<br/>"
                           "• <b>Substance-Free Zone:</b> Smoking, vaping, alcohol, or narcotics are strictly prohibited on campus: immediate referral to Disciplinary Committee.", styles['Body']))
    story.append(Spacer(1, 4))

    # Formal Signatory Block
    story.append(get_signatory_block(
        styles,
        prepared_role="Disciplinary Officer & Head of Security",
        prepared_name="Capt. A. Joseph Antony, Retd.",
        verified_role="Vice Principal & Chairman, Discipline Cell",
        verified_name="Prof. M. Kalyanasundaram, M.E."
    ))

    return story

def generate_doc_07():
    return build_pdf_document("07_code_of_conduct_ethics_and_anti_ragging_policy_2025_2026.pdf", get_doc_07_story())


# ======================================================================================
# 8. INTERNAL COMPLAINTS COMMITTEE (ICC) & POSH CHARTER (2025–2026) - 1 PAGE
# ======================================================================================
def get_doc_08_story():
    styles = create_styles()
    story = get_header_story(
        styles,
        doc_id="SJCET/ICC/POSH/2025/08",
        doc_title="Internal Complaints Committee (ICC) & PoSH Policy Charter (2025–2026)",
        category="Statutory Compliance & Gender Safety"
    )

    story.append(Paragraph("1. Statutory Mandate & Objectives", styles['H1']))
    story.append(Paragraph("Pursuant to the Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013 and UGC Regulations 2015, the ICC is constituted to maintain a secure, dignified, and gender-equitable working and studying environment.", styles['Body']))

    story.append(Paragraph("2. Composition of the Internal Complaints Committee (2025–2026)", styles['H1']))
    
    icc_data = [
        [Paragraph("Role in Committee", styles['TableHeader']), Paragraph("Name & Academic Title", styles['TableHeader']), Paragraph("Designation & Department", styles['TableHeader']), Paragraph("Contact Email & Extension", styles['TableHeader'])],
        [Paragraph("Presiding Officer", styles['TableCellBold']), Paragraph("Dr. S. Meenakshi", styles['TableCell']), Paragraph("Senior Professor & Head, Dept of CSE", styles['TableCell']), Paragraph("posh.presiding@stjude.edu.in (Extn 112)", styles['TableCell'])],
        [Paragraph("Faculty Member 1", styles['TableCellBold']), Paragraph("Dr. P. Hemalatha", styles['TableCell']), Paragraph("Professor, Department of ECE", styles['TableCell']), Paragraph("p.hemalatha@stjude.edu.in (Extn 214)", styles['TableCell'])],
        [Paragraph("Faculty Member 2", styles['TableCellBold']), Paragraph("Dr. K. Sundararajan", styles['TableCell']), Paragraph("Associate Professor, Dept of Mechanical", styles['TableCell']), Paragraph("k.sundar@stjude.edu.in (Extn 315)", styles['TableCell'])],
        [Paragraph("Non-Teaching Staff", styles['TableCellBold']), Paragraph("Mrs. G. Shanthi", styles['TableCell']), Paragraph("Senior Administrative Assistant", styles['TableCell']), Paragraph("g.shanthi@stjude.edu.in (Extn 107)", styles['TableCell'])],
        [Paragraph("External NGO Member", styles['TableCellBold']), Paragraph("Advocate R. Vasundhara", styles['TableCell']), Paragraph("Legal Advisor, Women's Rights Forum", styles['TableCell']), Paragraph("vasundhara.legal@wrf-ngo.org", styles['TableCell'])],
        [Paragraph("Student Representative", styles['TableCellBold']), Paragraph("Ms. Ananya Sharma", styles['TableCell']), Paragraph("Final Year B.Tech AI & DS (Student Rep)", styles['TableCell']), Paragraph("icc.studentrep@stjude.edu.in", styles['TableCell'])],
    ]
    t_icc = Table(icc_data, colWidths=[105, 115, 175, 145])
    t_icc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_icc)
    story.append(Spacer(1, 3))

    story.append(Paragraph("3. Complaint Filing, Inquiry Timelines & Protection", styles['H1']))
    story.append(Paragraph("• <b>Filing Window:</b> Written or encrypted email submission (<b>icc@stjude.edu.in</b>) within <b>3 months</b> from incident date.<br/>"
                           "• <b>Notice to Respondent:</b> Dispatched within 7 working days; respondent must submit reply within 10 days.<br/>"
                           "• <b>Statutory Inquiry Ceiling:</b> Inquiries must be completed within <b>90 days</b>. The report is submitted to the Principal within 10 days.<br/>"
                           "• <b>Strict Confidentiality:</b> Breach of identity/inquiry confidentiality attracts a statutory fine of <b>₹5,000</b>. The institution guarantees complete protection against victimisation.", styles['InfoBox']))
    story.append(Spacer(1, 4))

    # Formal Signatory Block
    story.append(get_signatory_block(
        styles,
        prepared_role="Presiding Officer, ICC",
        prepared_name="Dr. S. Meenakshi, Ph.D.",
        verified_role="External Legal Member, ICC",
        verified_name="Advocate R. Vasundhara, B.A.L., LL.B."
    ))

    return story

def generate_doc_08():
    return build_pdf_document("08_internal_complaints_committee_posh_charter_2025_2026.pdf", get_doc_08_story())


# ======================================================================================
# 9. CENTRAL LIBRARY & DIGITAL RESOURCES POLICY (2025–2026) - 1 PAGE
# ======================================================================================
def get_doc_09_story():
    styles = create_styles()
    story = get_header_story(
        styles,
        doc_id="SJCET/LIB/POL/2025/09",
        doc_title="Central Library Regulations, Digital Resource Access & Plagiarism Policy (2025–2026)",
        category="Learning Resource Centre"
    )

    story.append(Paragraph("1. Library Infrastructure & Operating Hours", styles['H1']))
    story.append(Paragraph("Dr. A.P.J. Abdul Kalam Central Library spans a 3-storey facility housing 68,000+ volumes, 14,000+ titles, 220 printed journals, and 100 dedicated multimedia computer nodes. Operating hours: <b>08:00 AM to 08:00 PM (Mon-Fri)</b>, <b>09:00 AM to 05:00 PM (Sat-Sun)</b>, and open until <b>10:00 PM</b> during examination months.", styles['Body']))

    story.append(Paragraph("2. Borrowing Privileges & Overdue Fine Slabs", styles['H1']))
    
    lib_data = [
        [Paragraph("User Category", styles['TableHeader']), Paragraph("Book Quota", styles['TableHeader']), Paragraph("Loan Period", styles['TableHeader']), Paragraph("Renewals Permitted", styles['TableHeader']), Paragraph("Overdue Fine Slab", styles['TableHeader'])],
        [Paragraph("Undergraduate Students (B.E./B.Tech)", styles['TableCellBold']), Paragraph("4 Books", styles['TableCellCenter']), Paragraph("14 Days", styles['TableCellCenter']), Paragraph("1 Time (if not reserved)", styles['TableCellCenter']), Paragraph("₹2 / day (Days 1–7), ₹5 / day thereafter", styles['TableCell'])],
        [Paragraph("Postgraduate Students (M.E./MBA/MCA)", styles['TableCellBold']), Paragraph("6 Books", styles['TableCellCenter']), Paragraph("21 Days", styles['TableCellCenter']), Paragraph("2 Times", styles['TableCellCenter']), Paragraph("₹2 / day (Days 1–7), ₹5 / day thereafter", styles['TableCell'])],
        [Paragraph("Teaching Faculty Members", styles['TableCellBold']), Paragraph("10 Books", styles['TableCellCenter']), Paragraph("90 Days (1 Sem)", styles['TableCellCenter']), Paragraph("1 Time", styles['TableCellCenter']), Paragraph("Exempt from fine; reminder after 90 days", styles['TableCell'])],
        [Paragraph("Non-Teaching Staff", styles['TableCellBold']), Paragraph("2 Books", styles['TableCellCenter']), Paragraph("30 Days", styles['TableCellCenter']), Paragraph("1 Time", styles['TableCellCenter']), Paragraph("₹2 / day thereafter", styles['TableCell'])],
    ]
    t_lib = Table(lib_data, colWidths=[130, 65, 75, 115, 155])
    t_lib.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_lib)
    story.append(Spacer(1, 3))

    story.append(Paragraph("3. Digital Knowledge Centre & Plagiarism Screening", styles['H1']))
    story.append(Paragraph("• <b>Subscribed E-Databases:</b> IEEE Xplore Digital Library, Elsevier ScienceDirect, ACM Digital Library, Springer Nature, and DELNET.<br/>"
                           "• <b>Turnitin Plagiarism Screening:</b> All Capstone project reports and theses must undergo similarity verification. Total permissible similarity index must be <b>≤ 15%</b>. Submissions exceeding 15% will be returned for mandatory rewriting.<br/>"
                           "• <b>Lost Book Replacement:</b> Borrower must replace with same or latest edition plus ₹100 fee, or pay <b>double the latest market cost</b>.", styles['AlertBox']))
    story.append(Spacer(1, 4))

    # Formal Signatory Block
    story.append(get_signatory_block(
        styles,
        prepared_role="Chief Librarian",
        prepared_name="Dr. S. Gnanasekaran, M.L.I.S., Ph.D.",
        verified_role="Dean of Academic Research & Library Convener",
        verified_name="Dr. B. Vijayalakshmi, Ph.D."
    ))

    return story

def generate_doc_09():
    return build_pdf_document("09_central_library_and_digital_resources_policy_2025_2026.pdf", get_doc_09_story())


# ======================================================================================
# 10. STUDENT GRIEVANCE REDRESSAL & OMBUDSPERSON MANUAL (2025–2026) - 1 PAGE
# ======================================================================================
def get_doc_10_story():
    styles = create_styles()
    story = get_header_story(
        styles,
        doc_id="SJCET/GRIEV/MAN/2025/10",
        doc_title="Student Grievance Redressal Committee (SGRC) & Ombudsperson Manual (2025–2026)",
        category="Student Welfare & Governance"
    )

    story.append(Paragraph("1. Statutory Framework & Resolution Hierarchy", styles['H1']))
    story.append(Paragraph("Pursuant to UGC (Redressal of Grievances of Students) Regulations, 2023, St. Jude College maintains a multi-tiered grievance redressal hierarchy ensuring transparent, time-bound resolution.", styles['Body']))

    story.append(Paragraph("2. Four-Tier Escalation Matrix & Mandatory Timelines", styles['H1']))
    
    tier_g_data = [
        [Paragraph("Tier Level", styles['TableHeader']), Paragraph("Redressal Authority", styles['TableHeader']), Paragraph("Jurisdiction & Nature of Grievance", styles['TableHeader']), Paragraph("Resolution SLA", styles['TableHeader'])],
        [Paragraph("Tier 1", styles['TableCellBold']), Paragraph("Class Advisor & Faculty Proctor", styles['TableCell']), Paragraph("Routine academic issues, internal test doubts, laboratory schedules, room allocations", styles['TableCell']), Paragraph("Within 3 Working Days", styles['TableCellCenter'])],
        [Paragraph("Tier 2", styles['TableCellBold']), Paragraph("Head of the Department (HoD)", styles['TableCell']), Paragraph("Departmental course disputes, faculty feedback, elective choice allocations, attendance errors", styles['TableCell']), Paragraph("Within 5 Working Days", styles['TableCellCenter'])],
        [Paragraph("Tier 3", styles['TableCellBold']), Paragraph("Student Grievance Redressal Committee (SGRC)", styles['TableCell']), Paragraph("College-level disputes: fee discrepancies, transport grievances, hostel facilities, discrimination", styles['TableCell']), Paragraph("Within 15 Working Days", styles['TableCellCenter'])],
        [Paragraph("Tier 4", styles['TableCellBold']), Paragraph("University Ombudsperson", styles['TableCell']), Paragraph("Appeals against SGRC decisions; statutory oversight by former High Court Judge / Vice-Chancellor", styles['TableCell']), Paragraph("Within 30 Working Days", styles['TableCellCenter'])],
    ]
    t_tg = Table(tier_g_data, colWidths=[60, 130, 230, 120])
    t_tg.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_tg)
    story.append(Spacer(1, 3))

    story.append(Paragraph("3. SGRC Constitution & Submission Channels", styles['H1']))
    story.append(Paragraph("• <b>Chairperson:</b> Dr. S. Rajasekar, Principal | <b>University Ombudsperson:</b> Justice K. Govindarajan (Retd. High Court Judge).<br/>"
                           "• <b>Submission Channels:</b> Online via <b>https://helpdesk.stjude.edu.in</b> or email <b>grievance@stjude.edu.in</b>. Physical drop boxes cleared twice weekly.<br/>"
                           "• <b>Anti-Victimisation:</b> Section 7(3) of UGC Regulations guarantees that no student shall be subjected to discrimination or reduction of internal marks for filing a bonafide grievance.", styles['SuccessBox']))
    story.append(Spacer(1, 4))

    # Formal Signatory Block
    story.append(get_signatory_block(
        styles,
        prepared_role="Member Secretary, SGRC",
        prepared_name="Dr. T. Ramakrishnan, Prof/Mech",
        verified_role="Dean of Student Affairs",
        verified_name="Dr. N. Sundarapandian, M.E., Ph.D."
    ))

    return story

def generate_doc_10():
    return build_pdf_document("10_student_grievance_redressal_and_ombudsperson_manual_2025_2026.pdf", get_doc_10_story())


# ======================================================================================
# 11. CAMPUS HEALTH, TRANSPORT & STUDENT AMENITIES (2025–2026) - 1 PAGE
# ======================================================================================
def get_doc_11_story():
    styles = create_styles()
    story = get_header_story(
        styles,
        doc_id="SJCET/AMEN/FAC/2025/11",
        doc_title="Campus Health Services, Fleet Transportation & Student Amenities (2025–2026)",
        category="Campus Infrastructure & Health"
    )

    story.append(Paragraph("1. Campus Health Centre & Emergency Facilities", styles['H1']))
    story.append(Paragraph("The campus maintains a dedicated Health Centre staffed by a full-time Resident Medical Officer (RMO) and two qualified staff nurses. Out-patient consultation: 08:00 AM – 08:00 PM; 24/7 on-call emergency room service.<br/>"
                           "• <b>ICU Ambulance 24x7:</b> Emergency Hotlines: <b>044-2456-8800 (Extn 108) / +91 94451 99108</b>.<br/>"
                           "• <b>Tertiary Hospital Tie-Up:</b> Chettinad Health City and Apollo OMR for emergency hospitalisation.<br/>"
                           "• <b>Group Medical Insurance:</b> Every student covered under Cashless Hospitalisation Insurance up to <b>₹1,00,000</b> per annum.", styles['AlertBox']))

    story.append(Paragraph("2. Fleet Bus Transportation Network & Pass Slabs", styles['H1']))
    
    bus_data = [
        [Paragraph("Transport Zone", styles['TableHeader']), Paragraph("Representative Origin Points & Corridors", styles['TableHeader']), Paragraph("Approx. Distance", styles['TableHeader']), Paragraph("Annual Bus Fee (2025–2026)", styles['TableHeader'])],
        [Paragraph("Zone 1 (Nearby)", styles['TableCellBold']), Paragraph("Thiruvanmiyur, Velachery, Sholinganallur, Medavakkam, Navalur, Kelambakkam", styles['TableCell']), Paragraph("Within 15 km", styles['TableCellCenter']), Paragraph("₹22,000 per annum", styles['TableCellCenter'])],
        [Paragraph("Zone 2 (Mid-City)", styles['TableCellBold']), Paragraph("Tambaram, Chromepet, Guindy, Saidapet, Adyar, T. Nagar, Porur, Pallavaram", styles['TableCell']), Paragraph("16 km to 30 km", styles['TableCellCenter']), Paragraph("₹27,000 per annum", styles['TableCellCenter'])],
        [Paragraph("Zone 3 (Outer Suburbs)", styles['TableCellBold']), Paragraph("Anna Nagar, Ambattur, Koyambedu, Central, Avadi, Poonamallee, Chengalpattu", styles['TableCell']), Paragraph("31 km to 50 km", styles['TableCellCenter']), Paragraph("₹32,000 per annum", styles['TableCellCenter'])],
    ]
    t_bus = Table(bus_data, colWidths=[90, 240, 95, 115])
    t_bus.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_bus)
    story.append(Spacer(1, 3))

    story.append(Paragraph("3. Campus Food Court, Banking & Green Infrastructure", styles['H1']))
    story.append(Paragraph("• <b>Central Food Court:</b> Multi-cuisine FSSAI-certified cafeteria serving 1,200 students simultaneously (07:30 AM – 08:30 PM).<br/>"
                           "• <b>Banking & Postal:</b> Canara Bank on-campus branch, 2 24/7 ATMs, and India Post sub-office.<br/>"
                           "• <b>Green Campus:</b> 500 kW rooftop solar plant supplying 40% daytime energy; 100% sewage treatment recycling.", styles['Body']))
    story.append(Spacer(1, 4))

    # Formal Signatory Block
    story.append(get_signatory_block(
        styles,
        prepared_role="Resident Medical Officer (RMO)",
        prepared_name="Dr. C. Annamalai, MBBS, MD",
        verified_role="Transport & Estates Manager",
        verified_name="Mr. S. Dharmalingam, B.E."
    ))

    return story

def generate_doc_11():
    return build_pdf_document("11_campus_health_transport_and_student_amenities_2025_2026.pdf", get_doc_11_story())


# ======================================================================================
# 12. STUDENT CLUBS, SPORTS & EXTRACURRICULAR HANDBOOK (2025–2026) - 1 PAGE
# ======================================================================================
def get_doc_12_story():
    styles = create_styles()
    story = get_header_story(
        styles,
        doc_id="SJCET/ACT/EXT/2025/12",
        doc_title="Student Clubs, Professional Chapters, Sports & Cultural Handbook (2025–2026)",
        category="Student Affairs & Co-Curricular"
    )

    story.append(Paragraph("1. Professional Technical Chapters & Innovation Hubs", styles['H1']))
    story.append(Paragraph("• <b>IEEE Student Branch:</b> International paper presentations, hackathons, and IEEE Women in Engineering (WIE).<br/>"
                           "• <b>ACM Student Chapter:</b> Algorithmic bootcamps, competitive programming, and open-source sprints.<br/>"
                           "• <b>SAE Collegiate Club:</b> Design and fabrication of all-terrain buggies for BAJA and SUPRA competitions.<br/>"
                           "• <b>Institution's Innovation Council (IIC):</b> Student startup incubation with seed funding up to ₹2.5 Lakhs.", styles['InfoBox']))

    story.append(Paragraph("2. National Service Schemes & Extension Activities", styles['H1']))
    
    ext_data = [
        [Paragraph("Organization Unit", styles['TableHeader']), Paragraph("Faculty Officer in Charge", styles['TableHeader']), Paragraph("Strength / Enrollment", styles['TableHeader']), Paragraph("Key Annual Activities & Certification", styles['TableHeader'])],
        [Paragraph("National Service Scheme (NSS)", styles['TableCellBold']), Paragraph("Dr. S. Balamurugan", styles['TableCell']), Paragraph("2 Units (200 Volunteers)", styles['TableCellCenter']), Paragraph("Annual 7-day rural camp, blood donation drives, tree planting, village literacy programs", styles['TableCell'])],
        [Paragraph("National Cadet Corps (NCC - Army)", styles['TableCellBold']), Paragraph("Lt. Dr. R. Karthikeyan", styles['TableCell']), Paragraph("50 Cadets (1 TN CTC)", styles['TableCellCenter']), Paragraph("Republic Day Camp (RDC) training, weapon firing, Annual Training Camps, 'B' & 'C' Certs", styles['TableCell'])],
        [Paragraph("Youth Red Cross (YRC)", styles['TableCellBold']), Paragraph("Dr. M. Deepa", styles['TableCell']), Paragraph("100 Volunteers", styles['TableCellCenter']), Paragraph("Disaster management workshops, first-aid training, health & hygiene awareness drives", styles['TableCell'])],
        [Paragraph("Rotaract Club of SJCET", styles['TableCellBold']), Paragraph("Prof. V. Vignesh", styles['TableCell']), Paragraph("150 Members", styles['TableCellCenter']), Paragraph("Community outreach, orphan assistance, youth leadership summits, environmental drives", styles['TableCell'])],
    ]
    t_ext = Table(ext_data, colWidths=[115, 110, 105, 210])
    t_ext.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_ext)
    story.append(Spacer(1, 3))

    story.append(Paragraph("3. Sports Facilities, On-Duty (OD) Attendance & Annual Events", styles['H1']))
    story.append(Paragraph("• <b>On-Duty (OD) Attendance:</b> Granted <b>up to 15 days of academic OD attendance</b> per semester for approved sports/cultural participation.<br/>"
                           "• <b>Annual Flagship Events:</b> (1) <i>INVENTIX 2025:</i> National Tech Symposium (Oct 14–15, 2025); (2) <i>RHYTHM 2026:</i> Cultural Fiesta (Feb 20–21, 2026); (3) <i>OLYMPIA 2026:</i> Sports Meet (Mar 12–13, 2026).", styles['Body']))
    story.append(Spacer(1, 4))

    # Formal Signatory Block
    story.append(get_signatory_block(
        styles,
        prepared_role="Director of Physical Education",
        prepared_name="Dr. G. Sivakumar, M.P.Ed., Ph.D.",
        verified_role="Dean of Student Affairs",
        verified_name="Dr. N. Sundarapandian, M.E., Ph.D."
    ))

    return story

def generate_doc_12():
    return build_pdf_document("12_student_clubs_sports_and_extracurricular_handbook_2025_2026.pdf", get_doc_12_story())


# ======================================================================================
# 00. MASTER COMPENDIUM PDF (UNIFIED STORY WITH CONTINUOUS PAGINATION)
# ======================================================================================
def generate_master_compendium():
    styles = create_styles()
    master_story = []

    # ── COVER PAGE (PAGE 1) ───────────────────────────────────────────────────
    master_story.append(Spacer(1, 30))
    master_story.append(Paragraph("ST. JUDE COLLEGE OF ENGINEERING & TECHNOLOGY", styles['CollegeHeader']))
    master_story.append(Paragraph("AN AUTONOMOUS INSTITUTION | AFFILIATED TO ANNA UNIVERSITY, CHENNAI", styles['CollegeSubHeader']))
    master_story.append(Paragraph("Approved by AICTE, New Delhi | Accredited by NAAC with 'A++' Grade (CGPA 3.68/4.00)", styles['DocBadge']))
    master_story.append(Spacer(1, 20))
    
    cover_box = [
        [Paragraph("<font size=15 color='#1e3a8a'><b>OFFICIAL INSTITUTIONAL HANDBOOK &amp; ADMINISTRATIVE REGULATIONS COMPENDIUM</b></font><br/><br/>"
                   "<font size=11 color='#0f172a'><b>ACADEMIC YEAR 2025–2026</b></font><br/><br/>"
                   "<font size=8.5 color='#475569'>A Comprehensive Compendium of Statutes, Academic Regulations, Admission &amp; Fee Schedules, Examination Manuals, Residential Hostel Guidelines, Code of Conduct, Anti-Ragging Statutes, Scholarships, and Student Amenities.</font>", styles['TableCellCenter'])]
    ]
    t_cover = Table(cover_box, colWidths=[520])
    t_cover.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#1e3a8a')),
        ('TOPPADDING', (0,0), (-1,-1), 20),
        ('BOTTOMPADDING', (0,0), (-1,-1), 20),
        ('LEFTPADDING', (0,0), (-1,-1), 20),
        ('RIGHTPADDING', (0,0), (-1,-1), 20),
    ]))
    master_story.append(t_cover)
    master_story.append(Spacer(1, 25))

    meta_pub = [
        [Paragraph("<b>Publication Reference:</b>", styles['MetaKey']), Paragraph("SJCET/COMPENDIUM/2025-26/VOL-I", styles['MetaVal'])],
        [Paragraph("<b>Date of Promulgation:</b>", styles['MetaKey']), Paragraph("July 01, 2025", styles['MetaVal'])],
        [Paragraph("<b>Governing Council Ratification:</b>", styles['MetaKey']), Paragraph("Resolution #42-B (Annual General Meeting)", styles['MetaVal'])],
        [Paragraph("<b>Statutory Jurisdiction:</b>", styles['MetaKey']), Paragraph("All Enrolled Students, Teaching Faculty, and Administrative Offices", styles['MetaVal'])],
        [Paragraph("<b>Campus Location:</b>", styles['MetaKey']), Paragraph("Rajiv Gandhi IT Expressway, OMR, Chennai – 600119, Tamil Nadu, India", styles['MetaVal'])],
        [Paragraph("<b>Official Helpdesk Portal:</b>", styles['MetaKey']), Paragraph("https://helpdesk.stjude.edu.in | helpdesk@stjude.edu.in", styles['MetaVal'])],
    ]
    t_pub = Table(meta_pub, colWidths=[175, 345])
    t_pub.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f1f5f9')),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    master_story.append(t_pub)
    master_story.append(Spacer(1, 20))
    master_story.append(Paragraph("<b>CONFIDENTIALITY &amp; LEGAL NOTICE:</b> This official compendium is published by authority of the Governing Council of St. Jude College of Engineering & Technology. All regulations herein constitute binding contractual obligations between the student/parent and the institution upon admission.", styles['BannerNotice']))
    master_story.append(PageBreak())

    # ── TABLE OF CONTENTS (PAGE 2) ────────────────────────────────────────────
    master_story.append(Paragraph("ST. JUDE COLLEGE OF ENGINEERING & TECHNOLOGY", styles['CollegeHeader']))
    master_story.append(Paragraph("MASTER COMPENDIUM TABLE OF CONTENTS (2025–2026)", styles['DocTitle']))
    master_story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1e3a8a'), spaceAfter=8))

    toc_data = [
        [Paragraph("Section Ref", styles['TableHeader']), Paragraph("Institutional Document Title", styles['TableHeader']), Paragraph("Primary Custodian Department", styles['TableHeader']), Paragraph("Scope / Topics Covered", styles['TableHeader'])],
        [Paragraph("DOC-01", styles['TableCellBold']), Paragraph("Undergraduate & Postgraduate Academic Regulations (CBCS)", styles['TableCell']), Paragraph("Academic Council", styles['TableCell']), Paragraph("Degree Credits, 75% Attendance, Condonation, CGPA, Grading Scale", styles['TableCell'])],
        [Paragraph("DOC-02", styles['TableCellBold']), Paragraph("Admissions, Fee Schedule & UGC Refund Policy", styles['TableCell']), Paragraph("Office of Admissions & Finance", styles['TableCell']), Paragraph("Tuition Fees by Department, Late Fines, UGC Fee Refund Schedule", styles['TableCell'])],
        [Paragraph("DOC-03", styles['TableCellBold']), Paragraph("Examinations & Evaluation Manual", styles['TableCell']), Paragraph("Controller of Examinations (CoE)", styles['TableCell']), Paragraph("Hall Tickets, Malpractice Penalties, Revaluation, Arrear Examinations", styles['TableCell'])],
        [Paragraph("DOC-04", styles['TableCellBold']), Paragraph("Hostel & Residential Life Regulations & Mess Manual", styles['TableCell']), Paragraph("Hostel Wardens & Estates", styles['TableCell']), Paragraph("Room Rent, Mess Timings & Rebate, Curfew 8:30 PM, Biometric Attendance", styles['TableCell'])],
        [Paragraph("DOC-05", styles['TableCellBold']), Paragraph("Institutional & Governmental Scholarships Circular", styles['TableCell']), Paragraph("Student Welfare Office", styles['TableCell']), Paragraph("First Graduate (₹25k), Merit Waivers, Sports Concessions, Post-Matric SC/ST", styles['TableCell'])],
        [Paragraph("DOC-06", styles['TableCellBold']), Paragraph("Career Development & Campus Placement Policy", styles['TableCell']), Paragraph("Centre for Career Dev (CDC)", styles['TableCell']), Paragraph("6.5 CGPA Threshold, Tiers 1-3, Dream Offer Upgrade, Summer Internships", styles['TableCell'])],
        [Paragraph("DOC-07", styles['TableCellBold']), Paragraph("Code of Conduct, Ethics & Anti-Ragging Policy", styles['TableCell']), Paragraph("Discipline Committee", styles['TableCell']), Paragraph("Supreme Court Ragging Penalties, Flying Squad Roster, 24/7 Helplines", styles['TableCell'])],
        [Paragraph("DOC-08", styles['TableCellBold']), Paragraph("Internal Complaints Committee (ICC) & PoSH Charter", styles['TableCell']), Paragraph("ICC Committee", styles['TableCell']), Paragraph("PoSH Act 2013, 90-Day Inquiry Procedure, Confidentiality, Protection", styles['TableCell'])],
        [Paragraph("DOC-09", styles['TableCellBold']), Paragraph("Central Library & Digital Resources Policy", styles['TableCell']), Paragraph("Central Library", styles['TableCell']), Paragraph("Borrowing Limits, Overdue Fines, IEEE/ScienceDirect, Turnitin 15% Cap", styles['TableCell'])],
        [Paragraph("DOC-10", styles['TableCellBold']), Paragraph("Student Grievance Redressal & Ombudsperson Manual", styles['TableCell']), Paragraph("Grievance Redressal Cell", styles['TableCell']), Paragraph("4-Tier Escalation Hierarchy, 15-Day SLA, University Ombudsperson", styles['TableCell'])],
        [Paragraph("DOC-11", styles['TableCellBold']), Paragraph("Campus Health, Fleet Transport & Amenities", styles['TableCell']), Paragraph("Health Centre & Transport", styles['TableCell']), Paragraph("Resident Doctor, ICU Ambulance, 45 Bus Routes, ₹1L Group Insurance", styles['TableCell'])],
        [Paragraph("DOC-12", styles['TableCellBold']), Paragraph("Student Clubs, Sports & Extracurricular Handbook", styles['TableCell']), Paragraph("Physical Education & Clubs", styles['TableCell']), Paragraph("IEEE/ACM/SAE Clubs, NSS/NCC Units, Sports Complex, 15-Day OD Policy", styles['TableCell'])],
    ]
    t_toc = Table(toc_data, colWidths=[55, 175, 125, 185])
    t_toc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    master_story.append(t_toc)
    master_story.append(Spacer(1, 8))
    master_story.append(Paragraph("<i>Note: Each institutional section in this Compendium retains its statutory authority and administrative reference numbering. Complete procedural details follow in full below.</i>", styles['DocBadge']))
    master_story.append(PageBreak())

    # ── APPEND ALL 12 DOCUMENT STORIES WITH INTENTIONAL PAGE BREAKS ─────────────
    docs_story_factories = [
        get_doc_01_story,
        get_doc_02_story,
        get_doc_03_story,
        get_doc_04_story,
        get_doc_05_story,
        get_doc_06_story,
        get_doc_07_story,
        get_doc_08_story,
        get_doc_09_story,
        get_doc_10_story,
        get_doc_11_story,
        get_doc_12_story,
    ]

    for idx, story_fn in enumerate(docs_story_factories):
        doc_elements = story_fn()
        master_story.extend(doc_elements)
        if idx < len(docs_story_factories) - 1:
            master_story.append(PageBreak())

    # Build Master Compendium with MasterNumberedCanvas
    master_filepath = OUTPUT_DIR / "00_master_college_handbook_compendium_2025_2026.pdf"
    doc = SimpleDocTemplate(
        str(master_filepath),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=44,
        bottomMargin=44
    )
    doc.build(master_story, canvasmaker=MasterNumberedCanvas)
    return master_filepath


def main():
    print("=" * 80)
    print("Generating Complete Suite of Official College Documents (PDF) with Mock Data")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("=" * 80)

    # 1. Generate all 12 individual standalone PDFs
    individual_generators = [
        ("01_academic_regulations_2025_2026.pdf", generate_doc_01),
        ("02_admissions_and_fee_structure_2025_2026.pdf", generate_doc_02),
        ("03_examinations_and_evaluation_manual_2025_2026.pdf", generate_doc_03),
        ("04_hostel_and_residential_life_handbook_2025_2026.pdf", generate_doc_04),
        ("05_scholarships_and_financial_aid_circular_2025_2026.pdf", generate_doc_05),
        ("06_training_internship_and_placement_policy_2025_2026.pdf", generate_doc_06),
        ("07_code_of_conduct_ethics_and_anti_ragging_policy_2025_2026.pdf", generate_doc_07),
        ("08_internal_complaints_committee_posh_charter_2025_2026.pdf", generate_doc_08),
        ("09_central_library_and_digital_resources_policy_2025_2026.pdf", generate_doc_09),
        ("10_student_grievance_redressal_and_ombudsperson_manual_2025_2026.pdf", generate_doc_10),
        ("11_campus_health_transport_and_student_amenities_2025_2026.pdf", generate_doc_11),
        ("12_student_clubs_sports_and_extracurricular_handbook_2025_2026.pdf", generate_doc_12),
    ]

    individual_files = []
    for filename, fn in individual_generators:
        p = fn()
        individual_files.append((filename, p))

    # 2. Generate the unified Master Compendium with continuous numbering
    master_path = generate_master_compendium()

    print("\n--- Summary of Generated College Documents ---")
    all_files = [master_path] + [p for _, p in individual_files]
    total_pages = 0
    total_bytes = 0

    for p in all_files:
        reader = pypdf.PdfReader(str(p))
        pages = len(reader.pages)
        size = p.stat().st_size
        total_pages += pages
        total_bytes += size
        print(f"✓ {p.name:<62} | {pages} Pages | {size/1024:.1f} KB")

    print("-" * 80)
    print(f"TOTAL: {len(all_files)} PDF Files | {total_pages} Total Pages | {total_bytes/(1024*1024):.2f} MB")
    print("All documents drafted with full mock data, tables, clauses, contacts, and legal notices!")
    print("=" * 80)

if __name__ == "__main__":
    main()
