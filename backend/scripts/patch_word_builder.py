import re
from pathlib import Path

builder_path = Path(r"D:\SIH 2026\backend\scripts\build_full_word_report.py")
content = builder_path.read_text(encoding="utf-8")

# 1. Replacement for format_cell and table functions
old_helpers = """def set_cell_background(cell, hex_color):
    \"\"\"Applies solid background shading to a table cell.\"\"\"
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    \"\"\"Sets internal padding (in twips) for a table cell.\"\"\"
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_cell_border(cell, **kwargs):
    \"\"\"Sets specific borders on a cell.\"\"\"
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}/>')
    for edge, border_def in kwargs.items():
        val = border_def.get('val', 'single')
        sz = border_def.get('sz', '4')
        color = border_def.get('color', HEX_BORDER)
        tag = f'<w:{edge} {nsdecls("w")} w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        tcBorders.append(parse_xml(tag))
    tcPr.append(tcBorders)"""

new_helpers = """def format_cell(cell, bg_color=None, top=80, bottom=80, left=120, right=120, borders=None, v_align='center'):
    \"\"\"
    Applies background, margins, borders, and vertical alignment in strict ECMA-376 schema sequence:
    1. tcW
    2. tcBorders
    3. shd
    4. tcMar
    5. vAlign
    \"\"\"
    tcPr = cell._tc.get_or_add_tcPr()
    
    # Remove existing conflicting elements to ensure strict order
    for tag in ['tcBorders', 'shd', 'noWrap', 'tcMar', 'textDirection', 'tcFitText', 'vAlign']:
        existing = tcPr.find(qn(f'w:{tag}'))
        if existing is not None:
            tcPr.remove(existing)
            
    # 1. tcBorders (must precede shd and tcMar)
    if borders:
        tcBorders = OxmlElement('w:tcBorders')
        for edge in ['top', 'left', 'bottom', 'right']:
            b_def = borders.get(edge)
            if b_def:
                b_elem = OxmlElement(f'w:{edge}')
                b_elem.set(qn('w:val'), b_def.get('val', 'single'))
                b_elem.set(qn('w:sz'), str(b_def.get('sz', 4)))
                b_elem.set(qn('w:space'), '0')
                b_elem.set(qn('w:color'), b_def.get('color', HEX_BORDER))
                tcBorders.append(b_elem)
        tcPr.append(tcBorders)

    # 2. shd (must follow tcBorders, precede tcMar)
    if bg_color:
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), bg_color)
        tcPr.append(shd)

    # 3. tcMar (must follow shd)
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
        tcPr.append(vAlign)"""

assert old_helpers in content, "old_helpers not found!"
content = content.replace(old_helpers, new_helpers)

# 2. Replacement in add_styled_table
old_table_hdr = """        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], HEX_PRIMARY)
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)"""

new_table_hdr = """        hdr_cells[i].text = title
        format_cell(hdr_cells[i], bg_color=HEX_PRIMARY, top=120, bottom=120, left=140, right=140)"""

assert old_table_hdr in content, "old_table_hdr not found!"
content = content.replace(old_table_hdr, new_table_hdr)

old_table_row = """            row_cells[c_idx].text = str(val)
            set_cell_background(row_cells[c_idx], bg_color)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=120, right=120)
            set_cell_border(row_cells[c_idx], 
                            bottom={'sz': 4, 'val': 'single', 'color': HEX_BORDER},
                            top={'sz': 4, 'val': 'single', 'color': HEX_BORDER})"""

new_table_row = """            row_cells[c_idx].text = str(val)
            format_cell(row_cells[c_idx], bg_color=bg_color, top=80, bottom=80, left=120, right=120,
                        borders={'bottom': {'sz': 4, 'val': 'single', 'color': HEX_BORDER},
                                 'top': {'sz': 4, 'val': 'single', 'color': HEX_BORDER}})"""

assert old_table_row in content, "old_table_row not found!"
content = content.replace(old_table_row, new_table_row)

# 3. Replacement in add_callout
old_callout = """    set_cell_background(cell, HEX_CALLOUT_BG)
    set_cell_margins(cell, top=120, bottom=120, left=180, right=150)
    set_cell_border(cell,
                    left={'sz': 24, 'val': 'single', 'color': HEX_ACCENT},
                    top={'sz': 4, 'val': 'single', 'color': HEX_NEUTRAL},
                    bottom={'sz': 4, 'val': 'single', 'color': HEX_NEUTRAL},
                    right={'sz': 4, 'val': 'single', 'color': HEX_NEUTRAL})"""

new_callout = """    format_cell(cell, bg_color=HEX_CALLOUT_BG, top=120, bottom=120, left=180, right=150,
                borders={'left': {'sz': 24, 'val': 'single', 'color': HEX_ACCENT},
                         'top': {'sz': 4, 'val': 'single', 'color': HEX_NEUTRAL},
                         'bottom': {'sz': 4, 'val': 'single', 'color': HEX_NEUTRAL},
                         'right': {'sz': 4, 'val': 'single', 'color': HEX_NEUTRAL}})"""

assert old_callout in content, "old_callout not found!"
content = content.replace(old_callout, new_callout)

# 4. Replacement in add_code_block
old_code_block = """    set_cell_background(cell, "F1F5F9")
    set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
    set_cell_border(cell,
                    left={'sz': 16, 'val': 'single', 'color': HEX_SECONDARY},
                    top={'sz': 4, 'val': 'single', 'color': HEX_BORDER},
                    bottom={'sz': 4, 'val': 'single', 'color': HEX_BORDER},
                    right={'sz': 4, 'val': 'single', 'color': HEX_BORDER})"""

new_code_block = """    format_cell(cell, bg_color="F1F5F9", top=100, bottom=100, left=150, right=150,
                borders={'left': {'sz': 16, 'val': 'single', 'color': HEX_SECONDARY},
                         'top': {'sz': 4, 'val': 'single', 'color': HEX_BORDER},
                         'bottom': {'sz': 4, 'val': 'single', 'color': HEX_BORDER},
                         'right': {'sz': 4, 'val': 'single', 'color': HEX_BORDER}})"""

assert old_code_block in content, "old_code_block not found!"
content = content.replace(old_code_block, new_code_block)

# 5. Replacement for insert_toc_field
old_toc = r'''def insert_toc_field(doc):
    """Inserts an automated dynamic Microsoft Word Table of Contents field."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run()
    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> TOC \o "1-3" \h \z \u </w:instrText>' % nsdecls('w'))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
    p._p.append(fldChar1)
    p._p.append(instrText)
    p._p.append(fldChar2)
    p._p.append(fldChar3)'''

new_toc = r'''def insert_toc_field(doc):
    """Inserts a schema-valid Microsoft Word Table of Contents field inside runs (w:r)."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    
    # Run 1: begin field
    r1 = p.add_run()
    fld1 = OxmlElement('w:fldChar')
    fld1.set(qn('w:fldCharType'), 'begin')
    r1._r.append(fld1)
    
    # Run 2: field instruction
    r2 = p.add_run()
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    r2._r.append(instr)
    
    # Run 3: separator
    r3 = p.add_run()
    fld2 = OxmlElement('w:fldChar')
    fld2.set(qn('w:fldCharType'), 'separate')
    r3._r.append(fld2)
    
    # Run 4: instruction text
    r4 = p.add_run('Right-click this field and select "Update Field" to refresh the dynamic Table of Contents.')
    r4.font.name = "Calibri"
    r4.font.size = Pt(9.0)
    r4.font.italic = True
    r4.font.color.rgb = COLOR_MUTED
    
    # Run 5: end field
    r5 = p.add_run()
    fld3 = OxmlElement('w:fldChar')
    fld3.set(qn('w:fldCharType'), 'end')
    r5._r.append(fld3)'''

assert old_toc in content, "old_toc not found!"
content = content.replace(old_toc, new_toc)

builder_path.write_text(content, encoding="utf-8")
print("build_full_word_report.py successfully patched!")
