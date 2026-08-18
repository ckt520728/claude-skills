# -*- coding: utf-8 -*-
"""桃園市醫療資源分佈報告 -> .docx"""
import copy
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

CJK = "Microsoft JhengHei"
LAT = "Calibri"
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x5A, 0x5F, 0x66)
ACCENT = RGBColor(0x1C, 0x5C, 0xAB)
HDR_FILL = "DCE6F2"
ALT_FILL = "F2F5F8"


def set_run(run, size=11, bold=False, color=INK, cjk=CJK, latin=LAT, italic=False):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = latin
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rpr.append(rf)
    rf.set(qn('w:ascii'), latin)
    rf.set(qn('w:hAnsi'), latin)
    rf.set(qn('w:eastAsia'), cjk)
    return run


def para(doc, text="", size=11, bold=False, color=INK, align=None,
         space_before=0, space_after=6, line=1.45, indent_left=0, italic=False):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line
    if indent_left:
        pf.left_indent = Cm(indent_left)
    if text:
        set_run(p.add_run(text), size=size, bold=bold, color=color, italic=italic)
    return p


def rich(doc, parts, size=11, space_before=0, space_after=6, line=1.45, indent_left=0):
    """parts = [(text, bold, color)]"""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line
    if indent_left:
        pf.left_indent = Cm(indent_left)
    for t, b, c in parts:
        set_run(p.add_run(t), size=size, bold=b, color=c)
    return p


def bullet(doc, text, size=11, indent=0.6):
    p = doc.add_paragraph(style='List Bullet')
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(4)
    pf.line_spacing = 1.4
    pf.left_indent = Cm(indent + 0.4)
    pf.first_line_indent = Cm(-0.4)
    set_run(p.add_run(text), size=size)
    return p


def bullet_rich(doc, parts, size=11, indent=0.6):
    p = doc.add_paragraph(style='List Bullet')
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(4)
    pf.line_spacing = 1.4
    pf.left_indent = Cm(indent + 0.4)
    pf.first_line_indent = Cm(-0.4)
    for t, b, c in parts:
        set_run(p.add_run(t), size=size, bold=b, color=c)
    return p


def heading(doc, text, level=1):
    if level == 0:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2)
        set_run(p.add_run(text), size=22, bold=True, color=INK)
        return p
    if level == 1:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(20)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.keep_with_next = True
        set_run(p.add_run(text), size=15, bold=True, color=ACCENT)
        bottom_border(p, "1C5CAB", 6)
        return p
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(13)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.keep_with_next = True
    set_run(p.add_run(text), size=12, bold=True, color=INK)
    return p


def bottom_border(p, color="1C5CAB", size=6):
    ppr = p._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(size))
    bottom.set(qn('w:space'), '3')
    bottom.set(qn('w:color'), color)
    pbdr.append(bottom)
    ppr.append(pbdr)


def shade(cell, fill):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill)
    tcpr.append(shd)


def cell_borders(cell, color="C9D2DC"):
    tcpr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        e = OxmlElement('w:' + edge)
        e.set(qn('w:val'), 'single')
        e.set(qn('w:sz'), '4')
        e.set(qn('w:space'), '0')
        e.set(qn('w:color'), color)
        borders.append(e)
    tcpr.append(borders)


def repeat_header(row):
    trpr = row._tr.get_or_add_trPr()
    el = OxmlElement('w:tblHeader')
    el.set(qn('w:val'), 'true')
    trpr.append(el)


def make_table(doc, headers, rows, widths, aligns=None, size=9.5,
               bold_rows=(), note=None):
    """widths in cm; aligns: list of 'l'/'c'/'r'"""
    ncol = len(headers)
    aligns = aligns or ['l'] + ['r'] * (ncol - 1)
    t = doc.add_table(rows=1, cols=ncol)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    amap = {'l': WD_ALIGN_PARAGRAPH.LEFT, 'c': WD_ALIGN_PARAGRAPH.CENTER,
            'r': WD_ALIGN_PARAGRAPH.RIGHT}

    hdr = t.rows[0]
    repeat_header(hdr)
    for i, h in enumerate(headers):
        c = hdr.cells[i]
        c.width = Cm(widths[i])
        shade(c, HDR_FILL)
        cell_borders(c)
        p = c.paragraphs[0]
        p.alignment = amap[aligns[i]]
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        set_run(p.add_run(h), size=size, bold=True)

    for ri, r in enumerate(rows):
        row = t.add_row()
        is_bold = ri in bold_rows
        for i, v in enumerate(r):
            c = row.cells[i]
            c.width = Cm(widths[i])
            cell_borders(c)
            if is_bold:
                shade(c, HDR_FILL)
            elif ri % 2 == 1:
                shade(c, ALT_FILL)
            p = c.paragraphs[0]
            p.alignment = amap[aligns[i]]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            set_run(p.add_run(str(v)), size=size, bold=is_bold)

    if note:
        para(doc, note, size=8.5, color=MUTED, space_before=4, space_after=10, line=1.3)
    else:
        para(doc, "", size=6, space_after=6)
    return t


# ---------------------------------------------------------------- document
doc = Document()

sec = doc.sections[0]
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.left_margin = Cm(2.2)
sec.right_margin = Cm(2.2)
sec.top_margin = Cm(2.2)
sec.bottom_margin = Cm(2.0)
CW = 21.0 - 4.4  # 16.6 cm content width

normal = doc.styles['Normal']
normal.font.name = LAT
normal.font.size = Pt(11)
normal.element.rPr.rFonts.set(qn('w:eastAsia'), CJK)

# footer with page number
footer = sec.footer
fp = footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = fp.add_run()
set_run(run, size=8.5, color=MUTED)
fld1 = OxmlElement('w:fldChar'); fld1.set(qn('w:fldCharType'), 'begin')
instr = OxmlElement('w:instrText'); instr.set(qn('xml:space'), 'preserve'); instr.text = ' PAGE '
fld2 = OxmlElement('w:fldChar'); fld2.set(qn('w:fldCharType'), 'end')
run._r.append(fld1); run._r.append(instr); run._r.append(fld2)

# ---------------------------------------------------------------- cover
para(doc, "資料分析報告", size=9.5, bold=True, color=ACCENT, space_after=2)
heading(doc, "桃園市醫療資源分佈分析", level=0)
p = para(doc, "醫師人力、行政區分佈與診所密度", size=13, color=MUTED, space_after=10)
bottom_border(p, "C9D2DC", 6)

rich(doc, [("資料期別　", True, MUTED),
           ("民國 113 年（醫師人力、人口）／ 2026-07-29（健保特約院所名冊）", False, INK)],
     size=10, space_after=2)
rich(doc, [("資料來源　", True, MUTED),
           ("政府資料開放平臺（data.gov.tw）— 桃園市政府主計處、衛生福利部中央健康保險署、桃園市政府警察局", False, INK)],
     size=10, space_after=2)
rich(doc, [("產製日期　", True, MUTED), ("2026 年 8 月 18 日", False, INK)],
     size=10, space_after=16)

# ---------------------------------------------------------------- summary
heading(doc, "摘要", level=1)
para(doc,
     "桃園市 113 年底執業醫師合計 6,791 人（西醫師 4,640、牙醫師 1,499、中醫師 652），"
     "每萬人 29.0 人；全市健保特約診所 1,712 家、醫院 35 家，每萬人診所數 7.32 家。"
     "醫療資源在 13 個行政區之間高度不均：診所密度最高的桃園區（每萬人 11.10 家）"
     "是最低的平鎮區（3.84 家）的 2.9 倍；若以面積計，桃園區與大溪＋復興地區相差約 150 倍。"
     "八德、蘆竹兩區合計 38 萬人口卻無任何一家醫院；復興區僅有 5 家診所，且無牙醫、中醫、"
     "兒科與婦產科。", size=11, space_after=8)
para(doc,
     "須特別說明：現行政府開放資料並未公布醫師的「專科別」人數，也未公布行政區層級的醫師人數。"
     "本報告第一部分為官方醫師人數統計，第二、三部分則以健保特約院所的家數與登記診療科別作為"
     "區域醫療供給的代理指標。", size=10.5, color=MUTED, space_after=6)

# ---------------------------------------------------------------- part 1
heading(doc, "一、醫師人力總量與結構", level=1)

heading(doc, "1.1 113 年底執業醫事人員數", level=2)
make_table(doc,
    ["類別", "男", "女", "合計", "每萬人"],
    [["西醫師", "3,598", "1,042", "4,640", "19.8"],
     ["牙醫師", "1,038", "461", "1,499", "6.4"],
     ["中醫師", "410", "242", "652", "2.8"],
     ["醫師小計", "5,046", "1,745", "6,791", "29.0"],
     ["藥師", "1,217", "1,395", "2,612", "11.2"],
     ["藥劑生", "290", "179", "469", "2.0"],
     ["護理師、護士", "552", "16,968", "17,520", "74.9"],
     ["其他醫事人員", "1,868", "3,123", "4,991", "21.3"],
     ["全體醫事人員", "8,973", "23,410", "32,383", "138.5"]],
    widths=[4.6, 3.0, 3.0, 3.0, 3.0],
    aligns=['l', 'r', 'r', 'r', 'r'],
    bold_rows=(3, 8),
    note="資料來源：桃園市政府主計處「桃園市醫事人員數按醫事人員別分」（dataset 149633），113 年底。"
         "每萬人以 113 年底設籍人口 2,338,648 人計算。"
         "「其他醫事人員」包含呼吸治療師、物理治療師、職能治療師、諮商心理師、營養師、醫事放射師、醫事檢驗師及其他。")

heading(doc, "1.2 醫師人數趨勢（105–113 年）", level=2)
make_table(doc,
    ["年度（民國）", "西醫師", "牙醫師", "中醫師", "醫師合計"],
    [["105", "3,822", "1,094", "491", "5,407"],
     ["106", "3,911", "1,130", "494", "5,535"],
     ["107", "4,021", "1,184", "526", "5,731"],
     ["108", "4,201", "1,247", "595", "6,043"],
     ["109", "4,169", "1,225", "522", "5,916"],
     ["110", "4,322", "1,315", "544", "6,181"],
     ["111", "4,463", "1,397", "602", "6,462"],
     ["112", "4,541", "1,443", "635", "6,619"],
     ["113", "4,640", "1,499", "652", "6,791"],
     ["105→113 增幅", "+21.4%", "+37.0%", "+32.8%", "+25.6%"]],
    widths=[4.0, 3.2, 3.2, 3.0, 3.2],
    aligns=['l', 'r', 'r', 'r', 'r'],
    bold_rows=(9,),
    note="同期人口成長幅度小於醫師成長幅度：108→113 年桃園市人口自 2,249,037 人增至 2,338,648 人（+4.0%），"
         "同期醫師自 6,043 人增至 6,791 人（+12.4%），每萬人醫師數由 26.9 人升至 29.0 人。"
         "104 年度資料明顯不完整（醫事人員總計僅 14,980 人，次年即跳升至 25,338 人），研判為統計基礎變更，故未納入趨勢比較。")

heading(doc, "1.3 關於「科別分配」的資料限制", level=2)
para(doc, "使用者詢問的「科別分配」在現行開放資料中無法直接取得，說明如下：", size=11, space_after=5)
bullet_rich(doc, [("桃園市層級：", True, INK),
    ("主計處的醫事人員統計僅區分「西醫師／牙醫師／中醫師」，不含內科、外科、兒科等專科別。"
     "臺北市另有「醫院專科醫師專任人員數」資料集（dataset 130868），桃園市無對應資料。", False, INK)])
bullet_rich(doc, [("全國層級：", True, INK),
    ("衛生福利部統計處《醫院人力統計》（dataset 6474）與《醫院科別統計》（dataset 6475）含專科別，"
     "但僅以 ZIP 壓縮檔發布、僅涵蓋醫院（不含診所），且最細僅到縣市層級。", False, INK)])
bullet_rich(doc, [("行政區層級：", True, INK),
    ("全國各縣市均無按行政區發布的醫師人數資料。", False, INK)])
para(doc, "因此本報告第二部分改以健保特約院所的家數與登記診療科別，作為區域醫療供給結構的代理指標。",
     size=11, space_before=4, space_after=6)

# ---------------------------------------------------------------- part 2
doc.add_page_break()
heading(doc, "二、各行政區醫療資源分佈", level=1)

heading(doc, "2.1 各行政區院所家數", level=2)
make_table(doc,
    ["行政區", "西醫診所", "牙醫診所", "中醫診所", "診所合計", "醫院"],
    [["桃園區", "240", "190", "98", "528", "9"],
     ["中壢區", "197", "140", "82", "419", "11"],
     ["八德區", "73", "44", "21", "138", "0"],
     ["龜山區", "65", "40", "17", "122", "3"],
     ["蘆竹區", "58", "46", "13", "117", "0"],
     ["楊梅區", "51", "30", "17", "98", "2"],
     ["平鎮區", "39", "34", "15", "88", "5"],
     ["龍潭區", "41", "21", "10", "72", "2"],
     ["大園區", "24", "13", "10", "47", "2"],
     ["大溪區", "19", "16", "5", "40", "0"],
     ["觀音區", "12", "7", "4", "23", "0"],
     ["新屋區", "7", "4", "2", "13", "1"],
     ["復興區", "5", "0", "0", "5", "0"],
     ["全市合計", "831", "586", "295", "1,712", "35"]],
    widths=[2.9, 2.9, 2.9, 2.9, 2.9, 2.1],
    aligns=['l', 'r', 'r', 'r', 'r', 'r'],
    bold_rows=(13,),
    note="資料來源：健保署「健保特約醫事機構—診所／地區醫院／區域醫院／醫學中心」"
         "（dataset 39283 / 39282 / 39281 / 39280），檔案更新日 2026-07-29，已排除已終止合約或歇業之院所。"
         "行政區依院所登記地址判定；全市 1,712 家中有 2 家因地址格式無法歸區，故各區加總為 1,710 家。")

heading(doc, "2.2 醫院層級分佈", level=2)
make_table(doc,
    ["行政區", "醫學中心", "區域醫院", "地區醫院", "合計"],
    [["中壢區", "0", "1", "10", "11"],
     ["桃園區", "0", "5", "4", "9"],
     ["平鎮區", "0", "1", "4", "5"],
     ["龜山區", "1", "1", "1", "3"],
     ["楊梅區", "0", "0", "2", "2"],
     ["龍潭區", "0", "1", "1", "2"],
     ["大園區", "0", "0", "2", "2"],
     ["新屋區", "0", "0", "1", "1"],
     ["八德、蘆竹、大溪、觀音、復興", "0", "0", "0", "0"],
     ["全市合計", "1", "9", "25", "35"]],
    widths=[6.2, 2.6, 2.6, 2.6, 2.6],
    aligns=['l', 'r', 'r', 'r', 'r'],
    bold_rows=(9,),
    note="全市唯一醫學中心為林口長庚紀念醫院（設籍龜山區）。八德區（21.5 萬人）與蘆竹區（17.0 萬人）"
         "為人口逾 15 萬卻無任何醫院之行政區。")

heading(doc, "2.3 西醫診所診療科別分佈（全市 831 家）", level=2)
make_table(doc,
    ["科別", "院所數", "科別", "院所數"],
    [["內科（含次專科）", "132", "復健科", "46"],
     ["外科（含次專科）", "114", "精神科", "38"],
     ["家醫科", "114", "皮膚科", "32"],
     ["兒科", "97", "神經科", "15"],
     ["耳鼻喉科", "79", "泌尿科", "9"],
     ["眼科", "54", "神經外科", "3"],
     ["婦產科", "47", "整形外科", "3"],
     ["骨科", "47", "麻醉科／急診醫學科", "各 1"]],
    widths=[5.0, 3.3, 5.0, 3.3],
    aligns=['l', 'r', 'l', 'r'],
    note="統計對象為「登記提供該科之院所家數」，非醫師人數。一家診所可同時登記多科，故總和大於 831。")

heading(doc, "2.4 兒科與婦產科的區域可近性", level=2)
make_table(doc,
    ["行政區", "兒科院所", "婦產科院所", "人口（113 年）", "備註"],
    [["桃園區", "33", "22", "475,798", ""],
     ["中壢區", "24", "11", "435,050", ""],
     ["八德區", "10", "3", "214,690", ""],
     ["蘆竹區", "7", "2", "169,936", ""],
     ["楊梅區", "6", "1", "—", ""],
     ["龜山區", "5", "2", "183,895", ""],
     ["龍潭區", "4", "3", "127,270", ""],
     ["平鎮區", "3", "0", "229,389", "無婦產科診所"],
     ["大溪區", "3", "1", "—", ""],
     ["大園區", "1", "2", "—", ""],
     ["新屋區", "1", "0", "—", "無婦產科診所"],
     ["觀音區", "0", "0", "—", "兩科皆無"],
     ["復興區", "0", "0", "—", "兩科皆無"],
     ["全市合計", "97", "47", "2,338,648", ""]],
    widths=[2.6, 2.5, 2.8, 3.4, 5.3],
    aligns=['l', 'r', 'r', 'r', 'l'],
    bold_rows=(13,),
    note="人口欄位以「—」標示者，係因該區與鄰區合併於同一警察分局轄區統計，無單獨行政區人口數（詳見 3.1 說明）。"
         "婦產科診所有 70.2%（33/47）集中於桃園、中壢兩區。")

# ---------------------------------------------------------------- part 3
doc.add_page_break()
heading(doc, "三、各行政區診所密度", level=1)

heading(doc, "3.1 統計單元說明", level=2)
para(doc,
     "計算密度所需的人口與面積，採用桃園市政府警察局「轄區現住人口、性別比例及人口密度」"
     "（dataset 26053）113 年資料，此為現有開放資料中最新且同時含人口與面積者。"
     "警察分局轄區有三組為兩區合併統計，故下表為 10 個統計單元而非 13 個行政區：",
     size=11, space_after=5)
bullet(doc, "楊梅分局 ＝ 楊梅區 ＋ 新屋區（174.14 km²）")
bullet(doc, "大園分局 ＝ 大園區 ＋ 觀音區（175.37 km²）")
bullet(doc, "大溪分局 ＝ 大溪區 ＋ 復興區（455.90 km²）")
para(doc, "其餘 7 個分局轄區與行政區界完全一致（面積可逐一核對相符）。診所家數則依院所地址精確歸屬各行政區，"
          "合併單元的診所數為兩區加總。",
     size=10, color=MUTED, space_before=4, space_after=8)

heading(doc, "3.2 診所密度排序", level=2)
make_table(doc,
    ["統計單元", "診所數", "人口", "面積 km²", "每萬人診所數", "每 km² 診所數"],
    [["桃園區", "528", "475,798", "34.8", "11.10", "15.17"],
     ["中壢區", "419", "435,050", "76.5", "9.63", "5.48"],
     ["蘆竹區", "117", "169,936", "75.5", "6.89", "1.55"],
     ["龜山區", "122", "183,895", "72.0", "6.63", "1.69"],
     ["八德區", "138", "214,690", "33.7", "6.43", "4.09"],
     ["龍潭區", "72", "127,270", "75.2", "5.66", "0.96"],
     ["楊梅＋新屋", "111", "230,915", "174.1", "4.81", "0.64"],
     ["大園＋觀音", "70", "164,040", "175.4", "4.27", "0.40"],
     ["大溪＋復興", "45", "107,665", "455.9", "4.18", "0.10"],
     ["平鎮區", "88", "229,389", "47.8", "3.84", "1.84"],
     ["全市", "1,712", "2,338,648", "1,220.9", "7.32", "1.40"]],
    widths=[3.2, 2.3, 3.0, 2.5, 3.0, 2.6],
    aligns=['l', 'r', 'r', 'r', 'r', 'r'],
    bold_rows=(10,),
    note="依「每萬人診所數」由高至低排序。全市平均 7.32 家／萬人；高於平均者僅桃園、中壢兩區。")

heading(doc, "3.3 觀察", level=2)
bullet_rich(doc, [("人口密度差距 2.9 倍。", True, INK),
    ("桃園區每萬人 11.10 家，平鎮區 3.84 家。全市 10 個統計單元中，僅桃園、中壢兩區高於全市平均。", False, INK)])
bullet_rich(doc, [("平鎮區為統計上的異常值，但須謹慎解讀。", True, INK),
    ("平鎮區人口 22.9 萬（全市第四），診所密度卻是全市最低。惟平鎮區緊鄰中壢區，"
     "兩區人口合計 66.4 萬、診所合計 507 家（每萬人 7.63 家，接近全市平均），"
     "顯示存在明顯的跨區就醫。「密度低」在此不必然等同「可近性差」；八德區之於桃園區亦同。", False, INK)])
bullet_rich(doc, [("復興區為真正的醫療資源匱乏地區。", True, INK),
    ("面積 350.8 km²（全市 28.7%），人口 1.1 萬，僅有 5 家西醫診所，"
     "無牙醫診所、無中醫診所、無醫院、無兒科、無婦產科。且其山地地形使跨區就醫成本遠高於平地各區。", False, INK)])
bullet_rich(doc, [("面積密度差距達 150 倍。", True, INK),
    ("桃園區 15.17 家／km²，大溪＋復興 0.10 家／km²。此一差距主要反映都市化程度，"
     "但對無自用交通工具者而言即為實質的就醫距離障礙。", False, INK)])
bullet_rich(doc, [("兩個人口逾 15 萬的行政區完全沒有醫院。", True, INK),
    ("八德區 21.5 萬人、蘆竹區 17.0 萬人，區內皆無任何層級之醫院，急重症照護完全依賴外區。", False, INK)])

# ---------------------------------------------------------------- part 4
heading(doc, "四、資料來源與限制", level=1)

heading(doc, "4.1 資料來源", level=2)
make_table(doc,
    ["資料集", "編號", "提供機關", "期別／更新"],
    [["桃園市醫事人員數按醫事人員別分", "149633", "桃園市政府主計處", "113 年底"],
     ["健保特約醫事機構—診所", "39283", "衛福部中央健康保險署", "2026-07-29"],
     ["健保特約醫事機構—地區醫院", "39282", "衛福部中央健康保險署", "2026-07-29"],
     ["健保特約醫事機構—區域醫院", "39281", "衛福部中央健康保險署", "2026-07-29"],
     ["健保特約醫事機構—醫學中心", "39280", "衛福部中央健康保險署", "2026-07-29"],
     ["警察局轄區現住人口、性別比例及人口密度", "26053", "桃園市政府警察局", "113 年"]],
    widths=[6.6, 2.0, 4.4, 3.6],
    aligns=['l', 'c', 'l', 'l'],
    note="全部資料集皆採「政府資料開放授權條款—第 1 版」，經由政府資料開放平臺（data.gov.tw）取得。")

heading(doc, "4.2 使用限制", level=2)
bullet_rich(doc, [("醫師專科別資料不存在。", True, INK),
    ("如 1.3 所述，桃園市無按專科別發布的醫師人數，行政區層級亦無醫師人數資料。"
     "第二、三部分係以院所家數作為代理指標，不可直接解讀為醫師人力分佈。", False, INK)])
bullet_rich(doc, [("院所家數不等於服務量能。", True, INK),
    ("一家診所可能是單醫師執業，也可能有多位醫師與多科別；醫院的規模差距更大。"
     "本報告未納入病床數、醫師人數、門診人次等量能指標。", False, INK)])
bullet_rich(doc, [("時點不一致。", True, INK),
    ("醫師人力與人口為 113 年底資料，院所名冊為 2026-07-29 快照，兩者相隔約 1.5 年。", False, INK)])
bullet_rich(doc, [("跨區就醫未被納入。", True, INK),
    ("所有密度指標皆以設籍人口為分母，未反映實際就醫流動。桃園市與新北市、新竹縣的縣市界"
     "亦存在跨縣市就醫（如龜山—林口、新屋—新豐），本報告未予處理。", False, INK)])
bullet_rich(doc, [("人口資料集的選擇。", True, INK),
    ("桃園市民政局「各區人口年齡層每月統計」（dataset 168384）可提供 13 個行政區的個別人口，"
     "但該資料集於平臺上正規化後之快照為舊月份（全市僅 215 萬人，與 113 年底 234 萬人相差 8%），"
     "故本報告改採警察局 113 年資料，代價是三組行政區必須合併統計。", False, INK)])

para(doc, "")
p = para(doc, "本報告所有數值均由政府開放資料原始檔案彙總計算，未經任何推估或補值。",
         size=9, color=MUTED, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=10)

import os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "桃園市醫療資源分佈分析報告.docx")
doc.save(out)
print("SAVED:", out)
