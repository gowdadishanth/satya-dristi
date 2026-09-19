import zipfile
from lxml import etree

with zipfile.ZipFile(r'D:\SIH 2026\Satya_Dristi_Complete_Technical_Report.docx') as z:
    for name in z.namelist():
        if name.endswith('.xml'):
            content = z.read(name)
            root = etree.fromstring(content)
            
            # Check for illegal children of w:p
            for p in root.xpath('//*[local-name()="p"]'):
                for child in p:
                    tag = etree.QName(child).localname
                    # Allowed in w:p: pPr, r, fldSimple, hyperlink, bookmarkStart, bookmarkEnd, commentRangeStart, commentRangeEnd, moveFromRangeStart, moveFromRangeEnd, moveToRangeStart, moveToRangeEnd, oMath, oMathPara, smartTag, subDoc
                    if tag in ['fldChar', 'instrText']:
                        print(f"ERROR in {name}: <w:p> contains illegal direct child <w:{tag}>!")

            # Check for multiple tcBorders in tcPr
            for tcPr in root.xpath('//*[local-name()="tcPr"]'):
                borders = [c for c in tcPr if etree.QName(c).localname == 'tcBorders']
                if len(borders) > 1:
                    print(f"ERROR in {name}: multiple <w:tcBorders> inside <w:tcPr>!")
                shds = [c for c in tcPr if etree.QName(c).localname == 'shd']
                if len(shds) > 1:
                    print(f"ERROR in {name}: multiple <w:shd> inside <w:tcPr>!")

            # Check empty cells
            for tc in root.xpath('//*[local-name()="tc"]'):
                children = [etree.QName(c).localname for c in tc]
                if 'p' not in children and 'tbl' not in children:
                    print(f"ERROR in {name}: <w:tc> has no paragraph or table!")

print("Validation completed.")
