"""Interactive, self-contained HTML visualization (vis-network)."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .graph import KnowledgeGraph

COLORS = {"INTERVENTION": "#2a9d8f", "BIOMARKER": "#e76f51", "BRAIN_REGION": "#8e6cc9",
          "COGNITIVE_DOMAIN": "#3a86c8", "CONDITION": "#c4455e", "POPULATION": "#b08a2e",
          "METHOD": "#6c7a89", "MECHANISM": "#d17fb0", "CONCEPT": "#4f9d4a"}


def graph_payload(kg: KnowledgeGraph, max_nodes: int = 600, center: str | None = None, depth: int = 2) -> dict:
    G = kg.G
    if center:
        sub = kg.neighbors(center, depth=depth, max_edges=2000)
        keep = set(sub.get("nodes", []))
    else:
        keep = {n for n, _ in sorted(G.degree(), key=lambda x: -x[1])[:max_nodes]}
    nodes = []
    for n in keep:
        d = G.nodes[n]
        nodes.append({"id": n, "label": n if len(n) < 40 else n[:38] + "…", "type": d["type"],
                      "value": G.degree(n) + 1, "desc": d.get("description", ""),
                      "aliases": d.get("aliases", []), "profile": d.get("profile"),
                      "docs": [kg.doc_titles.get(i, "?") for i in d["docs"]][:30]})
    edges = []
    for a, b, k, d in G.edges(keys=True, data=True):
        if a in keep and b in keep:
            edges.append({"from": a, "to": b, "label": k, "w": d["weight"],
                          "ev": [{"t": e["text"], "d": e["doc"]} for e in d["evidence"][:4]]})
    return {"nodes": nodes, "edges": edges, "colors": COLORS}


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
:root{--bg:#f7f7f5;--panel:#ffffff;--ink:#1d2327;--muted:#5f6b73;--line:#d9dde0;--accent:#2a9d8f}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#15181b;--panel:#1d2125;--ink:#e6e9eb;--muted:#9aa5ad;--line:#30363b}}
:root[data-theme="dark"]{--bg:#15181b;--panel:#1d2125;--ink:#e6e9eb;--muted:#9aa5ad;--line:#30363b}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--ink)}
header{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:10px 16px;border-bottom:1px solid var(--line);background:var(--panel)}
h1{font-size:16px;margin:0 12px 0 0}input,select{font:inherit;padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink)}
#wrap{display:flex;height:calc(100vh - 54px)}#net{flex:1;min-width:0}
aside{width:380px;max-width:45vw;overflow:auto;border-left:1px solid var(--line);background:var(--panel);padding:14px 16px}
.chip{display:inline-flex;align-items:center;gap:5px;margin:2px 6px 2px 0;font-size:12px;cursor:pointer;user-select:none}
.chip i{width:10px;height:10px;border-radius:50%;display:inline-block}.chip.off{opacity:.35}
.muted{color:var(--muted)}.ev{border-left:3px solid var(--line);padding:2px 8px;margin:6px 0;font-size:13px}
h2{font-size:15px;margin:4px 0}h3{font-size:13px;margin:14px 0 4px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
@media (max-width:760px){#wrap{flex-direction:column;height:auto}#net{height:65vh}aside{width:auto;max-width:none;border-left:0;border-top:1px solid var(--line)}}
</style></head><body>
<header><h1>__TITLE__</h1>
<input id="q" placeholder="Search entity…" list="names"><datalist id="names"></datalist>
<label class="muted">min docs <input id="mw" type="number" min="1" value="1" style="width:56px"></label>
<span id="legend"></span><span class="muted" id="count"></span></header>
<div id="wrap"><div id="net"></div><aside id="side"><p class="muted">Click a node or edge to see its description, aliases, source documents and evidence quotes.</p></aside></div>
<script>
const DATA = __DATA__;
const off = new Set();
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const nodes = new vis.DataSet(), edges = new vis.DataSet();
const byId = Object.fromEntries(DATA.nodes.map(n => [n.id, n]));
function rebuild(){
  const mw = +document.getElementById("mw").value || 1;
  const vis_ = DATA.nodes.filter(n => !off.has(n.type));
  const ok = new Set(vis_.map(n => n.id));
  nodes.clear(); edges.clear();
  nodes.add(vis_.map(n => ({id:n.id,label:n.label,value:n.value,color:DATA.colors[n.type]||"#888",
    font:{color:getComputedStyle(document.body).color,size:13}})));
  const es = DATA.edges.filter(e => ok.has(e.from) && ok.has(e.to) && e.w >= mw);
  edges.add(es.map((e,i) => ({id:i,from:e.from,to:e.to,title:e.label,width:Math.min(1+e.w,7),arrows:"to",
     color:{opacity:.45},_e:e})));
  document.getElementById("count").textContent = `${vis_.length} nodes · ${es.length} edges`;
}
const net = new vis.Network(document.getElementById("net"), {nodes, edges}, {
  nodes:{shape:"dot",scaling:{min:6,max:38}}, edges:{smooth:{type:"continuous"},font:{size:0}},
  physics:{solver:"forceAtlas2Based",forceAtlas2Based:{gravitationalConstant:-45,springLength:110},stabilization:{iterations:250}},
  interaction:{hover:true,tooltipDelay:120}});
const legend = document.getElementById("legend");
Object.entries(DATA.colors).forEach(([t,c]) => { if(!DATA.nodes.some(n=>n.type===t)) return;
  const s=document.createElement("span"); s.className="chip"; s.innerHTML=`<i style="background:${c}"></i>${t}`;
  s.onclick=()=>{ off.has(t)?off.delete(t):off.add(t); s.classList.toggle("off"); rebuild(); }; legend.appendChild(s); });
document.getElementById("names").innerHTML = DATA.nodes.map(n=>`<option value="${esc(n.id)}">`).join("");
document.getElementById("mw").onchange = rebuild;
document.getElementById("q").onchange = e => { const id=e.target.value; if(byId[id]){ net.selectNodes([id]); net.focus(id,{scale:1.2,animation:true}); showNode(id);} };
function showNode(id){
  const n = byId[id], side = document.getElementById("side");
  const rel = DATA.edges.filter(e => e.from===id || e.to===id).sort((a,b)=>b.w-a.w);
  side.innerHTML = `<h2>${esc(n.id)}</h2><div class="muted">${esc(n.type)} · degree ${n.value-1}</div>
   <p>${esc(n.profile ? n.profile.summary : n.desc)}</p>
   ${n.profile ? "<h3>Key facts</h3><ul>"+n.profile.key_facts.map(f=>`<li>${esc(f)}</li>`).join("")+"</ul>" : ""}
   ${n.aliases.length ? `<h3>Aliases</h3><div>${n.aliases.map(esc).join(" · ")}</div>` : ""}
   <h3>Relations (${rel.length})</h3>${rel.slice(0,60).map(e=>`<div class="ev"><b>${esc(e.from)}</b> —${esc(e.label)}→ <b>${esc(e.to)}</b> <span class="muted">(${e.w} doc)</span>${e.ev.slice(0,1).map(v=>`<div class="muted">“${esc(v.t)}” — ${esc(v.d)}</div>`).join("")}</div>`).join("")}
   <h3>Documents (${n.docs.length})</h3><ul>${n.docs.map(d=>`<li>${esc(d)}</li>`).join("")}</ul>`;
}
function showEdge(e){
  document.getElementById("side").innerHTML = `<h2>${esc(e.from)} —${esc(e.label)}→ ${esc(e.to)}</h2>
   <div class="muted">${e.w} supporting document(s)</div><h3>Evidence</h3>${e.ev.map(v=>`<div class="ev">“${esc(v.t)}”<div class="muted">${esc(v.d)}</div></div>`).join("")}`;
}
net.on("click", p => { if(p.nodes.length) showNode(p.nodes[0]); else if(p.edges.length) showEdge(edges.get(p.edges[0])._e); });
net.once("stabilizationIterationsDone", () => net.setOptions({physics:false}));
rebuild();
</script></body></html>"""


def export_html(kg: KnowledgeGraph, out: str | Path, title: str = "Knowledge Graph", **kw) -> Path:
    payload = graph_payload(kg, **kw)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    out.write_text(TEMPLATE.replace("__TITLE__", html.escape(title)).replace("__DATA__", data), encoding="utf-8")
    return out
