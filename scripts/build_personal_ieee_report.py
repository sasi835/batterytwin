"""Build an institutional cover followed by the IEEE-style BatteryTwin paper."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from pypdf import PdfReader, PdfWriter
from scripts.build_report import report
from src.utils.config import ROOT

TEMP = ROOT / 'tmp/pdfs/personal-ieee'
OUTPUT = ROOT / 'output/pdf/BatteryTwin_IEEE_Project_Report_SriRam_Sasi.pdf'
WIDTH, HEIGHT = A4


def cover():
    target = TEMP / 'cover.pdf'
    c = canvas.Canvas(str(target), pagesize=A4)
    c.setLineWidth(0.7)
    c.rect(25, 25, WIDTH - 50, HEIGHT - 50)
    c.setFont('Times-Bold', 15)
    c.drawCentredString(WIDTH / 2, HEIGHT - 90, 'COIMBATORE INSTITUTE OF TECHNOLOGY')
    style = ParagraphStyle('CoverAffiliation', fontName='Times-Roman', fontSize=11.5,
                           leading=15, alignment=TA_CENTER)
    text = Paragraph('(Government-Aided Autonomous Institution Affiliated to Anna University, Chennai)', style)
    _, height = text.wrap(460, 60)
    text.drawOn(c, (WIDTH - 460) / 2, HEIGHT - 115 - height)
    c.setFont('Times-Roman', 12)
    c.drawCentredString(WIDTH / 2, HEIGHT - 175, 'COIMBATORE - 641 014')
    c.setFont('Times-Bold', 12)
    c.drawCentredString(WIDTH / 2, HEIGHT - 218, 'ADVANCED MACHINE LEARNING LAB - 19MAM56')
    c.drawCentredString(WIDTH / 2, HEIGHT - 247, 'CAT II PROJECT REPORT')
    c.setFont('Times-Bold', 23)
    c.drawCentredString(WIDTH / 2, HEIGHT - 291, 'BatteryTwin')
    c.setFont('Times-Bold', 15)
    c.drawCentredString(WIDTH / 2, HEIGHT - 318, 'AI-Based EV Battery Health Monitoring')
    logo = ROOT / 'tmp/pdfs/lab-report/cit-logo.png'
    if not logo.exists():
        from PIL import Image
        screenshot = Path(r'C:\Users\SriRamSasi\OneDrive\Pictures\Screenshots\Screenshot 2026-10-14 163515.png')
        logo = TEMP / 'cit-logo.png'
        with Image.open(screenshot) as image:
            image.crop((234, 399, 405, 573)).save(logo)
    c.drawImage(str(logo), WIDTH / 2 - 65, 350, width=130, height=132, mask='auto')
    c.setFont('Times-Bold', 12)
    c.drawString(62, 295, 'SUBMITTED TO')
    c.drawString(313, 295, 'SUBMITTED BY')
    c.setFont('Times-Roman', 11)
    c.drawString(62, 270, 'Ms. Hemashree.P')
    c.drawString(62, 249, 'Dr. K. Swathine')
    for i, line in enumerate([
        'Name: SriRam Sasi M',
        'Reg No: 2403717674421052',
        'Department: M.Sc. AIML',
        'Date: 21 October 2026',
        'Subject: Advanced Machine Learning Lab',
        'Subject Code: 19MAM56',
    ]):
        c.setFont('Times-Roman', 10.5)
        c.drawString(313, 270 - i * 21, line)
    c.setFont('Times-Italic', 10.5)
    c.drawCentredString(WIDTH / 2, 91, 'Project report with IEEE-style two-column technical content')
    c.save()
    return target


def build():
    TEMP.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    front = cover()
    paper = report(TEMP / 'ieee-paper.pdf')
    writer = PdfWriter()
    writer.append(front)
    writer.append(paper)
    writer.add_metadata({'/Title': 'BatteryTwin: AI-Based EV Battery Health Monitoring - Project Report',
                         '/Author': 'SriRam Sasi M', '/Subject': '19MAM56 - Advanced Machine Learning Lab CAT II',
                         '/Keywords': 'IEEE, SOH, RUL, Streamlit, Random Forest, LSTM, Docker'})
    with OUTPUT.open('wb') as output:
        writer.write(output)
    reader = PdfReader(OUTPUT)
    cover_text = reader.pages[0].extract_text()
    assert 'SriRam Sasi M' in cover_text and '2403717674421052' in cover_text
    assert '21 October 2026' in cover_text and '19MAM56' in cover_text
    assert 'Abstract' in reader.pages[1].extract_text()
    assert all(page.extract_text().strip() for page in reader.pages)
    body = '\n'.join(p.extract_text() for p in reader.pages[1:])
    assert 'REFERENCES' in body and 'batterytwin.vercel.app' in body
    assert 'public hosting awaits a permitted credential' not in body
    record = {'output': str(OUTPUT), 'pages': len(reader.pages), 'cover_pages': 1,
              'paper_pages': len(reader.pages) - 1, 'student': 'SriRam Sasi M',
              'registration_number': '2403717674421052', 'report_date': '21 October 2026',
              'format': 'institutional cover followed by IEEE-style two-column academic paper',
              'blank_second_page': False, 'visual_review': 'pending'}
    (TEMP / 'verification.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(record, indent=2))
    return OUTPUT


if __name__ == '__main__':
    build()
