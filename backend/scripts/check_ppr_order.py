import zipfile
from lxml import etree

pPr_order = [
    'pStyle', 'keepNext', 'keepLines', 'pageBreakBefore', 'framePr',
    'widowControl', 'numPr', 'suppressLineNumbers', 'pBdr', 'shd',
    'tabs', 'suppressAutoHyphens', 'kinsoku', 'wordWrap', 'overflowPunct',
    'topLinePunct', 'autoSpaceDE', 'autoSpaceDN', 'bidi', 'adjustRightInd',
    'snapToGrid', 'spacing', 'ind', 'contextualSpacing', 'mirrorIndents',
    'suppressOverlap', 'jc', 'textDirection', 'textAlignment', 'textboxTightWrap',
    'outlineLvl', 'divId', 'cnfStyle', 'rPr', 'sectPr', 'pPrChange'
]
pPr_map = {name: i for i, name in enumerate(pPr_order)}

with zipfile.ZipFile(r'D:\SIH 2026\Satya_Dristi_Complete_Technical_Report.docx') as z:
    content = z.read('word/document.xml')
    root = etree.fromstring(content)
    
    violations = 0
    for idx, pPr in enumerate(root.xpath('//*[local-name()="pPr"]')):
        tags = [etree.QName(c).localname for c in pPr if etree.QName(c).localname in pPr_map]
        indices = [pPr_map[t] for t in tags]
        if indices != sorted(indices):
            violations += 1
            if violations <= 5:
                print(f"Order violation in pPr #{idx}: {tags}")

    print(f"Total pPr order violations = {violations}")
