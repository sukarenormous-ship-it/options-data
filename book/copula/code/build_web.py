"""สร้างหน้าอ่านออนไลน์ (artifact) จากไฟล์ markdown ของหนังสือ

    python3 book/copula/code/build_web.py <ไฟล์ผลลัพธ์.html>

แปลง markdown เป็น HTML ตั้งแต่ตอน build (ไม่พึ่ง CDN ตอนเปิดหน้า)
แล้วรวมทุกบทไว้ในหน้าเดียว สลับบทด้วย JavaScript สั้น ๆ

ต้องการ: pip install markdown
"""
import json
import os
import re
import sys

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.dirname(HERE)
GH = ("https://github.com/sukarenormous-ship-it/options-data/blob/"
      "claude/copula-reading-guide-sex85z/book/copula/")

PARTS = [
    (None, [("README", "หน้าปกและสารบัญ", None)]),
    ("ภาค 1 — รากฐาน", [
        ("01-why-copula", "ทำไม correlation ถึงไม่พอ", "1"),
        ("02-sklar-and-pit", "Sklar's Theorem และ PIT", "2"),
        ("03-reading-copula-plots", "อ่านภาพ copula ให้เป็น", "3"),
    ]),
    ("ภาค 2 — เครื่องมือ", [
        ("04-families", "ตระกูลของ copula", "4"),
        ("05-estimation", "การประมาณค่าและเลือกโมเดล", "5"),
        ("06-time-varying", "Dependence ที่เปลี่ยนตามเวลา", "6"),
    ]),
    ("ภาค 3 — เอาไปใช้เทรด", [
        ("07-architecture-residual", "residual มาจากไหน", "7"),
        ("08-conditional-signal", "จาก copula เป็นสัญญาณ", "8"),
        ("09-dependence-is-not-reversion", "Dependence ≠ Reversion", "9"),
        ("10-risk-overlay", "Copula ในบทบาท risk overlay", "10"),
    ]),
    ("ภาค 4 — วางที่ให้ถูกและพิสูจน์", [
        ("11-where-copula-belongs", "copula ควรอยู่ตรงไหนในระบบ", "11"),
        ("12-experiment-design", "ออกแบบการทดลองให้ยุติธรรม", "12"),
        ("13-pitfalls", "หลุมพรางและกฎตัดสินโมเดล", "13"),
    ]),
    ("ภาคผนวก", [
        ("appendix-a-formulas", "สัญลักษณ์และสูตรรวม", "A"),
        ("appendix-b-code", "โค้ดที่รันได้จริง", "B"),
        ("appendix-c-reading", "อ่านต่อ", "C"),
        ("appendix-d-vine", "Vine copula", "D"),
    ]),
]

ORDER = [s for _, items in PARTS for s, _, _ in items]
KEY_CHAPTER = "09-dependence-is-not-reversion"   # บทแกนของทั้งเล่ม

NAV_LINE = re.compile(r'^\[←.*\]\(.*\)\s*$|^\[← สารบัญ.*$', re.M)


def load(slug):
    with open(os.path.join(BOOK, slug + ".md"), encoding="utf-8") as fh:
        text = fh.read()

    # ตัดแถบนำทางท้ายบท — หน้าเว็บมีปุ่มก่อนหน้า/ถัดไปของตัวเอง
    lines = [ln for ln in text.split("\n")
             if not (ln.startswith("[←") or ln.startswith("[บทที่ 1](")
                     or (ln.startswith("[") and "](README.md)" in ln and "|" in ln))]
    text = "\n".join(lines).rstrip()
    while text.endswith("---"):
        text = text[:-3].rstrip()

    # ลิงก์ภายในเล่ม → hash route ; ลิงก์ไฟล์อื่น → GitHub
    text = re.sub(r'\]\((\.\./\.\./README\.md)\)',
                  '](https://github.com/sukarenormous-ship-it/options-data#readme)', text)
    text = re.sub(r'\]\((code/[^)]+)\)', lambda m: f']({GH}{m.group(1)})', text)
    text = re.sub(r'\]\(([0-9a-z][0-9a-z-]*)\.md\)', r'](#/\1)', text)
    return text


MD = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])


def to_html(text):
    MD.reset()
    html = MD.convert(text)
    # ตารางกว้าง ๆ ต้องเลื่อนในกล่องตัวเอง ไม่ใช่ทั้งหน้า
    html = html.replace("<table>", '<div class="tablewrap"><table>')
    html = html.replace("</table>", "</table></div>")
    # ลิงก์ออกนอกเล่มเปิดแท็บใหม่
    html = re.sub(r'<a href="(https?://[^"]+)"',
                  r'<a href="\1" target="_blank" rel="noopener"', html)
    return html


docs = {slug: to_html(load(slug)) for slug in ORDER}

# ---- สารบัญข้างซ้าย (สร้างเป็น HTML คงที่ เพื่อให้อ่านได้แม้ JS ยังไม่ทำงาน) ----
nav = []
for part, items in PARTS:
    if part:
        nav.append(f'<p class="part">{part}</p>')
    nav.append('<ul class="chapters">')
    for slug, title, num in items:
        key = ' data-key="1"' if slug == KEY_CHAPTER else ""
        marker = f'<span class="num">{num}</span>' if num else '<span class="num">◆</span>'
        nav.append(f'<li><a href="#/{slug}" data-slug="{slug}"{key}>'
                   f'{marker}<span class="ct">{title}</span></a></li>')
    nav.append("</ul>")
NAV_HTML = "\n".join(nav)

TEMPLATE = r"""<title>Copula สำหรับ Statistical Arbitrage</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Thai:wght@400;500;600&family=Noto+Serif+Thai:wght@500;600;700&display=swap">
<style>
:root{
  --paper:#f6f7f9; --surface:#ffffff; --ink:#14161a; --ink-soft:#3d434d;
  --muted:#5c6470; --rule:#e2e5ea; --rule-soft:#eceef2;
  --lower:#1f5fa8; --upper:#b26a16;
  --lower-wash:#eaf1f9; --upper-wash:#faf1e3;
  --code-bg:#f0f2f5;
  --sans:"IBM Plex Sans Thai","IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --serif:"Noto Serif Thai",Georgia,"Times New Roman",serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --sidebar:288px;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#0f1115; --surface:#161920; --ink:#e5e8ee; --ink-soft:#c3c9d4;
    --muted:#98a0ad; --rule:#272c35; --rule-soft:#1e222a;
    --lower:#7fb3e8; --upper:#e0a455;
    --lower-wash:#151f2c; --upper-wash:#241d12;
    --code-bg:#1a1e26;
  }
}
:root[data-theme="dark"]{
  --paper:#0f1115; --surface:#161920; --ink:#e5e8ee; --ink-soft:#c3c9d4;
  --muted:#98a0ad; --rule:#272c35; --rule-soft:#1e222a;
  --lower:#7fb3e8; --upper:#e0a455;
  --lower-wash:#151f2c; --upper-wash:#241d12;
  --code-bg:#1a1e26;
}

*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:var(--sans);font-size:16px;line-height:1.75;
  -webkit-font-smoothing:antialiased}
a{color:var(--lower)}
:focus-visible{outline:2px solid var(--lower);outline-offset:2px;border-radius:2px}

/* ---------- โครงหน้า ---------- */
.shell{display:grid;grid-template-columns:var(--sidebar) minmax(0,1fr);min-height:100vh}
.shell>div{min-width:0}

.side{border-right:1px solid var(--rule);background:var(--surface);
  position:sticky;top:0;height:100vh;overflow-y:auto;padding:28px 20px 48px;
  display:flex;flex-direction:column;gap:22px}

.brand{display:flex;flex-direction:column;gap:12px;padding-bottom:20px;
  border-bottom:1px solid var(--rule)}
.mark{width:56px;height:56px;display:block}
.brand h1{margin:0;font-family:var(--serif);font-weight:700;font-size:19px;
  line-height:1.35;letter-spacing:-.01em;text-wrap:balance}
.brand .sub{margin:0;color:var(--muted);font-size:12.5px;line-height:1.55;
  letter-spacing:.02em}

.part{margin:0;font-size:11px;font-weight:600;letter-spacing:.11em;
  text-transform:uppercase;color:var(--muted)}
.chapters{list-style:none;margin:8px 0 0;padding:0;display:flex;
  flex-direction:column;gap:1px}
.chapters a{display:flex;gap:11px;align-items:baseline;padding:7px 10px;
  border-radius:5px;text-decoration:none;color:var(--ink-soft);font-size:14px;
  line-height:1.45;transition:background .12s,color .12s}
.chapters a:hover{background:var(--rule-soft);color:var(--ink)}
.chapters a[aria-current="page"]{background:var(--lower-wash);color:var(--ink);
  font-weight:600}
.num{font-family:var(--mono);font-size:11.5px;color:var(--muted);
  min-width:16px;font-variant-numeric:tabular-nums;flex:none}
.chapters a[aria-current="page"] .num{color:var(--lower)}
.chapters a[data-key] .ct::after{content:"";display:inline-block;width:5px;
  height:5px;border-radius:50%;background:var(--upper);margin-inline-start:7px;
  vertical-align:middle}

.side-foot{margin-top:auto;padding-top:18px;border-top:1px solid var(--rule);
  display:flex;flex-direction:column;gap:9px;font-size:12px;color:var(--muted)}
.side-foot a{color:var(--muted);text-decoration:none;border-bottom:1px solid var(--rule)}
.side-foot a:hover{color:var(--ink)}
.legend{display:flex;gap:14px;font-size:11px}
.legend span{display:flex;align-items:center;gap:5px}
.legend i{width:7px;height:7px;border-radius:50%;display:block}

/* ---------- แถบบนสำหรับจอเล็ก ---------- */
.topbar{display:none;position:sticky;top:0;z-index:20;background:var(--surface);
  border-bottom:1px solid var(--rule);padding:10px 14px;align-items:center;gap:12px}
.topbar strong{font-size:14px;font-weight:600;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.menu{border:1px solid var(--rule);background:transparent;color:var(--ink);
  border-radius:6px;padding:6px 11px;font:inherit;font-size:13px;cursor:pointer}

.progress{position:fixed;top:0;left:0;height:2px;background:var(--upper);
  width:0;z-index:40;transition:width .1s linear}

/* ---------- คอลัมน์อ่าน ---------- */
main{padding:56px 40px 120px;display:flex;justify-content:center;min-width:0}
article{width:100%;max-width:69ch;min-width:0}

article h1{font-family:var(--serif);font-size:33px;font-weight:700;
  line-height:1.28;letter-spacing:-.015em;margin:0 0 6px;text-wrap:balance}
article h2{font-family:var(--serif);font-size:22px;font-weight:600;
  line-height:1.4;margin:52px 0 4px;padding-top:22px;
  border-top:1px solid var(--rule);text-wrap:balance}
article h3{font-size:16.5px;font-weight:600;margin:32px 0 2px;color:var(--ink)}
article p{margin:14px 0;color:var(--ink-soft)}
article strong{color:var(--ink);font-weight:600}
article ul,article ol{margin:14px 0;padding-inline-start:22px;color:var(--ink-soft)}
article li{margin:5px 0}
article li::marker{color:var(--muted)}

/* คำนำบท */
article > blockquote:first-of-type{margin:22px 0 34px;padding:16px 20px;
  background:var(--lower-wash);border:0;border-inline-start:2px solid var(--lower);
  border-radius:0 5px 5px 0}
article blockquote{margin:22px 0;padding:2px 0 2px 20px;
  border-inline-start:2px solid var(--upper);color:var(--ink-soft)}
article blockquote p{margin:7px 0}
article blockquote strong{color:var(--ink)}

article hr{border:0;border-top:1px solid var(--rule);margin:38px 0}
article hr + h2{border-top:0;padding-top:0;margin-top:24px}   /* เลี่ยงเส้นคู่ */

article code{font-family:var(--mono);font-size:.875em;background:var(--code-bg);
  padding:1.5px 5px;border-radius:3px;color:var(--ink)}
article pre{background:var(--code-bg);border:1px solid var(--rule);
  border-radius:7px;padding:16px 18px;overflow-x:auto;margin:20px 0;
  line-height:1.6}
article pre code{background:none;padding:0;font-size:13px;color:var(--ink-soft);
  white-space:pre}

.tablewrap{overflow-x:auto;margin:22px 0}
article table{border-collapse:collapse;width:100%;font-size:14px;
  font-variant-numeric:tabular-nums}
article th{text-align:start;font-weight:600;color:var(--ink);
  border-bottom:1.5px solid var(--rule);padding:9px 14px 9px 0;
  font-size:12px;letter-spacing:.05em;text-transform:uppercase;
  white-space:nowrap}
article td{border-bottom:1px solid var(--rule-soft);padding:10px 14px 10px 0;
  color:var(--ink-soft);vertical-align:top}
article tr:last-child td{border-bottom:0}

/* ---------- ปุ่มก่อนหน้า/ถัดไป ---------- */
.pager{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:64px;
  padding-top:26px;border-top:1px solid var(--rule)}
.pager a{display:flex;flex-direction:column;gap:3px;padding:15px 17px;
  border:1px solid var(--rule);border-radius:7px;text-decoration:none;
  background:var(--surface);transition:border-color .15s}
.pager a:hover{border-color:var(--lower)}
.pager .dir{font-size:11px;letter-spacing:.09em;text-transform:uppercase;
  color:var(--muted)}
.pager .ttl{font-size:14.5px;color:var(--ink);font-weight:500;line-height:1.4}
.pager .next{text-align:end}
.pager .spacer{border:0;background:none}

@media (max-width:900px){
  .shell{grid-template-columns:minmax(0,1fr)}
  .topbar{display:flex}
  .side{position:fixed;inset:0 auto 0 0;width:min(320px,86vw);z-index:30;
    transform:translateX(-102%);transition:transform .22s ease;
    box-shadow:0 0 0 100vmax rgba(0,0,0,0);height:100dvh}
  .side.open{transform:none;box-shadow:0 24px 60px rgba(0,0,0,.28)}
  main{padding:30px 20px 90px}
  article h1{font-size:27px}
  article h2{font-size:20px}
  .pager{grid-template-columns:1fr}
}
@media (prefers-reduced-motion:reduce){
  *{transition:none!important;animation:none!important;scroll-behavior:auto!important}
}
</style>

<div class="progress" id="progress"></div>

<div class="shell">
  <aside class="side" id="side">
    <div class="brand">
      <svg class="mark" viewBox="0 0 56 56" aria-hidden="true">
        <rect x="4.5" y="4.5" width="47" height="47" rx="2" fill="none"
              stroke="currentColor" stroke-opacity=".28"/>
        <g id="markdots"></g>
      </svg>
      <h1>Copula สำหรับ<br>Statistical Arbitrage</h1>
      <p class="sub">หนังสืออ่านสำหรับคนที่จะเอาไปใช้จริง<br>13 บท · 3 ภาคผนวก · โค้ดที่ทดสอบแล้ว</p>
    </div>
    <nav id="toc">__NAV__</nav>
    <div class="side-foot">
      <div class="legend">
        <span><i style="background:var(--lower)"></i>lower tail</span>
        <span><i style="background:var(--upper)"></i>upper tail</span>
      </div>
      <a href="https://github.com/sukarenormous-ship-it/options-data/tree/claude/copula-reading-guide-sex85z/book/copula"
         target="_blank" rel="noopener">ต้นฉบับและโค้ดบน GitHub →</a>
    </div>
  </aside>

  <div>
    <div class="topbar">
      <button class="menu" id="menu" aria-expanded="false">สารบัญ</button>
      <strong id="crumb">Copula สำหรับ Statistical Arbitrage</strong>
    </div>
    <main><article id="content"></article></main>
  </div>
</div>

<script>
const DOCS = __DOCS__;
const ORDER = __ORDER__;
const TITLES = __TITLES__;

const content = document.getElementById("content");
const side = document.getElementById("side");
const crumb = document.getElementById("crumb");

/* จุดบนสี่เหลี่ยมหน่วย — ภาพ scatter ของ copula ที่มี tail dependence จริง ๆ
   (คงที่ ไม่สุ่มใหม่ทุกครั้ง เพื่อให้เครื่องหมายเหมือนเดิมเสมอ) */
(function drawMark(){
  const pts=[[.07,.10],[.12,.17],[.09,.24],[.18,.12],[.16,.28],[.23,.20],[.28,.33],
             [.34,.27],[.31,.44],[.42,.38],[.39,.52],[.47,.45],[.53,.57],[.5,.68],
             [.61,.5],[.58,.63],[.66,.71],[.72,.6],[.7,.8],[.78,.73],[.83,.86],
             [.87,.79],[.9,.91],[.76,.9],[.93,.83],[.22,.06],[.06,.35]];
  const g=document.getElementById("markdots");
  g.innerHTML=pts.map(([x,y])=>{
    const corner = (x<.3&&y<.3) ? "var(--lower)" : (x>.7&&y>.7) ? "var(--upper)" : "currentColor";
    const op = corner==="currentColor" ? .34 : .95;
    return `<circle cx="${(4.5+x*47).toFixed(2)}" cy="${(51.5-y*47).toFixed(2)}" r="1.5"
            fill="${corner}" fill-opacity="${op}"/>`;
  }).join("");
})();

function slugFromHash(){
  const h = location.hash.replace(/^#\/?/, "");
  return DOCS[h] ? h : "README";
}

function render(){
  const slug = slugFromHash();
  content.innerHTML = DOCS[slug];       // เรนเดอร์มาแล้วตอน build

  // ปุ่มก่อนหน้า / ถัดไป
  const i = ORDER.indexOf(slug);
  const link = (j,dir,label) => j>=0 && j<ORDER.length
    ? `<a class="${dir}" href="#/${ORDER[j]}"><span class="dir">${label}</span>
       <span class="ttl">${TITLES[ORDER[j]]}</span></a>`
    : '<span class="spacer"></span>';
  const pager = document.createElement("nav");
  pager.className = "pager";
  pager.innerHTML = link(i-1,"prev","← ก่อนหน้า") + link(i+1,"next","ถัดไป →");
  content.appendChild(pager);

  crumb.textContent = TITLES[slug];
  document.querySelectorAll("#toc a").forEach(a=>{
    if(a.dataset.slug===slug) a.setAttribute("aria-current","page");
    else a.removeAttribute("aria-current");
  });
  side.classList.remove("open");
  document.getElementById("menu").setAttribute("aria-expanded","false");
  window.scrollTo(0,0);
}

document.getElementById("menu").addEventListener("click", e=>{
  const open = side.classList.toggle("open");
  e.currentTarget.setAttribute("aria-expanded", String(open));
});

const bar = document.getElementById("progress");
addEventListener("scroll", ()=>{
  const max = document.body.scrollHeight - innerHeight;
  bar.style.width = (max>40 ? (scrollY/max)*100 : 0) + "%";
}, {passive:true});

addEventListener("hashchange", render);
render();
</script>
"""

titles = {slug: (f"บทที่ {num} · {title}" if num and num.isdigit()
                 else (f"ภาคผนวก {num} · {title}" if num else title))
          for _, items in PARTS for slug, title, num in items}

html = (TEMPLATE
        .replace("__NAV__", NAV_HTML)
        .replace("__DOCS__", json.dumps(docs, ensure_ascii=False))
        .replace("__ORDER__", json.dumps(ORDER, ensure_ascii=False))
        .replace("__TITLES__", json.dumps(titles, ensure_ascii=False)))

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "book.html")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(html)
print(f"เขียน {out} ({len(html)/1024:.0f} KB, {len(docs)} บท)")
