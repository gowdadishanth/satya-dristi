from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import pypdf

def clean_pdf_text(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    replacements = {
        '²': ' sq km',
        '³': ' cu m',
        '·': ' - ',
        '—': ' -- ',
        '–': '-',
        '“': '"',
        '”': '"',
        '‘': "'",
        '’': "'",
        '…': '...',
        '\u00a0': ' ',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('ascii', 'ignore').decode('ascii')

doc = SimpleDocTemplate('backend/test_clean.pdf', pagesize=letter)
styles = getSampleStyleSheet()
story = [Paragraph(clean_pdf_text('Test km² with middle dot · and dash —'), styles['Normal'])]
doc.build(story)

reader = pypdf.PdfReader('backend/test_clean.pdf')
print('Extracted:', reader.pages[0].extract_text())
