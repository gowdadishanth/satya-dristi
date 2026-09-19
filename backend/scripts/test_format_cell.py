import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from lxml import etree
import zipfile

doc = docx.Document()
tbl = doc.add_table(rows=2, cols=2)

def format_cell(cell, bg_color=None, top=80, bottom=80, left=120, right=120, borders=None, v_align='center'):
    tcPr = cell._tc.get_or_add_tcPr()
    
    # Clear any conflicting elements to guarantee exact order
    for tag in ['tcBorders', 'shd', 'noWrap', 'tcMar', 'textDirection', 'tcFitText', 'vAlign']:
        existing = tcPr.find(qn(f'w:{tag}'))
        if existing is not None:
            tcPr.remove(existing)
            
    # 1. tcBorders (must precede shd)
    if borders:
        tcBorders = OxmlElement('w:tcBorders')
        for edge in ['top', 'left', 'bottom', 'right']:
            b_def = borders.get(edge)
            if b_def:
                b_elem = OxmlElement(f'w:{edge}')
                b_elem.set(qn('w:val'), b_def.get('val', 'single'))
                b_elem.set(qn('w:sz'), str(b_def.get('sz', 4)))
                b_elem.set(qn('w:space'), '0')
                b_elem.set(qn('w:color'), b_def.get('color', 'CBD5E1'))
                tcBorders.append(b_elem)
        tcPr.append(tcBorders)

    # 2. shd (must follow tcBorders, precede tcMar)
    if bg_color:
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), bg_color)
        tcPr.append(shd)

    # 3. tcMar (must follow shd, precede vAlign)
    tcMar = OxmlElement('w:tcMar')
    for edge, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        m = OxmlElement(f'w:{edge}')
        m.set(qn('w:w'), str(val))
        m.set(qn('w:type'), 'dxa')
        tcMar.append(m)
    tcPr.append(tcMar)

    # 4. vAlign (must follow tcMar)
    if v_align:
        vAlign = OxmlElement('w:vAlign')
        vAlign.set(qn('w:val'), v_align)
        tcPr.append(vAlign)

for row in tbl.rows:
    for cell in row.cells:
        cell.text = "Sample"
        format_cell(cell, bg_color="313851", borders={'bottom': {'sz': 4, 'val': 'single', 'color': 'CBD5E1'}})

doc.save("test_table.docx")

# Validate order
expected_order = [
    'cnfStyle', 'tcW', 'gridSpan', 'hMerge', 'vMerge', 
    'tcBorders', 'shd', 'noWrap', 'tcMar', 'textDirection', 
    'tcFitText', 'vAlign', 'hideMark', 'headers', 'cellIns', 
    'cellDel', 'cellMerge', 'tcPrChange'
]
order_map = {name: i for i, name in enumerate(expected_order)}

with zipfile.ZipFile("test_table.docx") as z:
    content = z.read("word/document.xml")
    root = etree.fromstring(content)
    violations = 0
    for idx, tcPr in enumerate(root.xpath('//*[local-name()="tcPr"]')):
        tags = [etree.QName(c).localname for c in tcPr if etree.QName(c).localname in order_map]
        indices = [order_map[t] for t in tags]
        if indices != sorted(indices):
            violations += 1
            print(f"Violation: {tags}")
    print("Test table violations:", violations)
