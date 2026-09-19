import os
import json
from pathlib import Path
import pypdf

art_dir = Path("C:/Users/gowda/AppData/Local/Temp/playwright-artifacts-ZNROjn")

files = [
    "224b7307-0ba3-4843-9f26-87e1f31e11e2",
    "25e20bcf-e575-4392-bfdf-6a65c1cf31ff",
    "d15c0b09-f762-4781-830a-b4a755749a92",
    "edef3d0e-1ee8-4575-ae66-d43435bad52a",
]

for fname in files:
    fpath = art_dir / fname
    print("=" * 60)
    print(f"File: {fname} (path: {fpath})")
    if not fpath.exists():
        print("  DOES NOT EXIST")
        continue
    size = fpath.stat().st_size
    print(f"  Size: {size} bytes")
    
    # Check PDF
    try:
        reader = pypdf.PdfReader(str(fpath))
        print(f"  [PDF VALID] num_pages = {len(reader.pages)}")
        for idx, page in enumerate(reader.pages):
            text = page.extract_text()
            print(f"    Page {idx+1} text length: {len(text)}, sample: {text[:100]!r}")
    except Exception as e:
        print(f"  [PDF FAILED]: {e}")

    # Check JSON
    try:
        with open(fpath, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        print(f"  [JSON VALID] keys: {list(data.keys())}")
        print(f"    Sample: product={data.get('product')}, report_id={data.get('report_id')}, task={data.get('task')}")
    except Exception as e:
        print(f"  [JSON FAILED]: {e}")
