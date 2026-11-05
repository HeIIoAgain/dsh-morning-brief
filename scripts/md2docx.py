#!/usr/bin/env python3
"""Markdown -> minimal but valid .docx (OOXML) converter, dependency-free."""
import re
import sys
import zipfile
from xml.sax.saxutils import escape

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''

ROOT_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''

DOC_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''

STYLES = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W_NS}">
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="宋体"/>
<w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="320" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/>
<w:pPr><w:spacing w:before="120" w:after="240"/><w:jc w:val="left"/></w:pPr>
<w:rPr><w:rFonts w:eastAsia="黑体"/><w:b/><w:sz w:val="36"/><w:szCs w:val="36"/><w:color w:val="1F3864"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="280" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr>
<w:rPr><w:rFonts w:eastAsia="黑体"/><w:b/><w:sz w:val="28"/><w:szCs w:val="28"/><w:color w:val="1F3864"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="200" w:after="100"/><w:outlineLvl w:val="1"/></w:pPr>
<w:rPr><w:rFonts w:eastAsia="黑体"/><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/><w:color w:val="2E5496"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/>
<w:pPr><w:ind w:left="240"/><w:spacing w:after="80"/></w:pPr>
<w:rPr><w:color w:val="595959"/><w:i/><w:sz w:val="19"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListPara"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/>
<w:pPr><w:ind w:left="420" w:hanging="200"/><w:spacing w:after="60"/></w:pPr></w:style>
</w:styles>'''

CORE = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>半导体晨报</dc:title><dc:creator>DSH</dc:creator>
<dcterms:created xsi:type="dcterms:W3CDTF">2026-10-18T23:20:00Z</dcterms:created>
</cp:coreProperties>'''

APP = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<Application>DSH</Application></Properties>'''


def runs_markup(text):
    """Convert inline markdown (**bold**, `code`, [text](url)) into w:r runs."""
    text = text.replace('`', '')
    pattern = re.compile(r'\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)]+)\)')
    out, pos = [], 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            out.append(('', text[pos:m.start()]))
        if m.group(1) is not None:
            out.append(('b', m.group(1)))
        else:
            label, url = m.group(2), m.group(3)
            shown = url if label in ('链接', '来源', 'link') else f'{label}（{url}）'
            out.append(('link', shown))
        pos = m.end()
    if pos < len(text):
        out.append(('', text[pos:]))
    return out or [('', '')]


def para(text, style=None, indent=False):
    ppr = ''
    if style or indent:
        ppr = '<w:pPr>'
        if style:
            ppr += f'<w:pStyle w:val="{style}"/>'
        if indent:
            ppr += '<w:ind w:left="420" w:hanging="200"/>'
        ppr += '</w:pPr>'
    chunks = []
    for kind, value in runs_markup(text):
        rpr = ''
        if kind == 'b':
            rpr = '<w:rPr><w:b/></w:rPr>'
        elif kind == 'link':
            rpr = '<w:rPr><w:color w:val="1F4E79"/><w:u w:val="single"/><w:sz w:val="19"/></w:rPr>'
        chunks.append(f'<w:r>{rpr}<w:t xml:space="preserve">{escape(value)}</w:t></w:r>')
    return f'<w:p>{ppr}{"".join(chunks)}</w:p>'


def table(rows):
    ncol = max(len(r) for r in rows)
    border = ''.join(
        f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="A6A6A6"/>'
        for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV')
    )
    xml = [
        '<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/>',
        '<w:tblW w:w="5000" w:type="pct"/>',
        f'<w:tblBorders>{border}</w:tblBorders>',
        '<w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
        '<w:bottom w:w="40" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar>',
        '</w:tblPr>',
    ]
    for index, row in enumerate(rows):
        cells = list(row) + [''] * (ncol - len(row))
        xml.append('<w:tr>')
        for cell in cells:
            shade = '<w:shd w:val="clear" w:color="auto" w:fill="DEEAF6"/>' if index == 0 else ''
            bold = '<w:rPr><w:b/><w:sz w:val="19"/></w:rPr>' if index == 0 else ''
            text = cell.strip().replace('**', '')
            xml.append(
                f'<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/>{shade}</w:tcPr>'
                f'<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
                f'<w:r>{bold}<w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p></w:tc>'
            )
        xml.append('</w:tr>')
    xml.append('</w:tbl>')
    return ''.join(xml)


def convert(markdown_text):
    body, lines = [], markdown_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith('|') and i + 1 < len(lines) and set(lines[i + 1].strip()) <= set('|-: '):
            rows = []
            header = [c.strip() for c in stripped.strip('|').split('|')]
            rows.append(header)
            i += 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            body.append(table(rows))
            body.append('<w:p/>')
            continue
        if stripped.startswith('# '):
            body.append(para(stripped[2:], 'Title'))
        elif stripped.startswith('## '):
            body.append(para(stripped[3:], 'Heading1'))
        elif stripped.startswith('### '):
            body.append(para(stripped[4:], 'Heading2'))
        elif stripped.startswith('> '):
            body.append(para(stripped[2:], 'Quote'))
        elif stripped in ('---', '***'):
            body.append('<w:p><w:pPr><w:spacing w:after="60"/></w:pPr></w:p>')
        elif re.match(r'^([-*]|\d+\.)\s+', stripped):
            text = re.sub(r'^([-*]|\d+\.)\s+', '', stripped)
            body.append(para('• ' + text, indent=True) if stripped[0] in '-*' else para(text, indent=True))
        else:
            body.append(para(stripped))
        i += 1

    sect = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" '
            'w:header="851" w:footer="992" w:gutter="0"/></w:sectPr>')
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}"><w:body>'
                + ''.join(body) + sect + '</w:body></w:document>')
    return document


def main(src, dst):
    with open(src, encoding='utf-8') as handle:
        markdown_text = handle.read()
    document = convert(markdown_text)
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', CONTENT_TYPES)
        archive.writestr('_rels/.rels', ROOT_RELS)
        archive.writestr('word/document.xml', document)
        archive.writestr('word/styles.xml', STYLES)
        archive.writestr('word/_rels/document.xml.rels', DOC_RELS)
        archive.writestr('docProps/core.xml', CORE)
        archive.writestr('docProps/app.xml', APP)
    print(f'wrote {dst}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
