import zipfile
from lxml import etree

tbl_expected_order = [
    'tblStyle', 'tblpPr', 'tblOverlap', 'bidiVisual', 'tblStyleRowBandSize',
    'tblStyleColBandSize', 'tblW', 'jc', 'tblCellSpacing', 'tblInd',
    'tblBorders', 'shd', 'tblLayout', 'tblCellMar', 'tblLook', 'tblCaption', 'tblDescription'
]
tbl_order_map = {name: i for i, name in enumerate(tbl_expected_order)}

with zipfile.ZipFile(r'D:\SIH 2026\Satya_Dristi_Complete_Technical_Report.docx') as z:
    content = z.read('word/document.xml')
    root = etree.fromstring(content)
    
    violations = 0
    for idx, tblPr in enumerate(root.xpath('//*[local-name()="tblPr"]')):
        tags = [etree.QName(c).localname for c in tblPr if etree.QName(c).localname in tbl_order_map]
        indices = [tbl_order_map[t] for t in tags]
        if indices != sorted(indices):
            violations += 1
            print(f"Order violation in tblPr #{idx}: {tags}")

    print(f"Total tblPr order violations = {violations}")
