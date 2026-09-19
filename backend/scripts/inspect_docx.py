import zipfile
from lxml import etree

with zipfile.ZipFile(r'D:\SIH 2026\Satya_Dristi_Complete_Technical_Report.docx') as z:
    xml_content = z.read('word/document.xml')
    root = etree.fromstring(xml_content)

    print("Checking fldChar parents:")
    for elem in root.xpath('//*[local-name()="fldChar"]'):
        print("fldChar parent:", elem.getparent().tag)

    print("Checking instrText parents:")
    for elem in root.xpath('//*[local-name()="instrText"]'):
        print("instrText parent:", elem.getparent().tag)
