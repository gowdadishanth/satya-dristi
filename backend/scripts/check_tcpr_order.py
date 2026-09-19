import zipfile
from lxml import etree

expected_order = [
    'cnfStyle', 'tcW', 'gridSpan', 'hMerge', 'vMerge', 
    'tcBorders', 'shd', 'noWrap', 'tcMar', 'textDirection', 
    'tcFitText', 'vAlign', 'hideMark', 'headers', 'cellIns', 
    'cellDel', 'cellMerge', 'tcPrChange'
]

order_map = {name: i for i, name in enumerate(expected_order)}

with zipfile.ZipFile(r'D:\SIH 2026\Satya_Dristi_Complete_Technical_Report.docx') as z:
    for fname in ['word/document.xml', 'word/header1.xml', 'word/footer1.xml']:
        if fname not in z.namelist():
            continue
        content = z.read(fname)
        root = etree.fromstring(content)
        
        violations = 0
        for idx, tcPr in enumerate(root.xpath('//*[local-name()="tcPr"]')):
            tags = [etree.QName(c).localname for c in tcPr if etree.QName(c).localname in order_map]
            indices = [order_map[t] for t in tags]
            if indices != sorted(indices):
                violations += 1
                if violations <= 5:
                    print(f"Order violation in {fname} tcPr #{idx}: {tags}")

        print(f"File {fname}: total tcPr order violations = {violations}")
