"""Prueba visual del consenso espacial del viento: mapa horario de vectores, consenso IDW frente a la dirección real.

Datos: tabla meteorologia de database_duck, último año (desde 2025-11-01), horario.
  - Dirección de cada estación: WindDir_D1_WVT (vectorial) si existe; si no, WindDir_Avg.
  - Consenso en una estación: media de los vectores (u, v) = velocidad · (sen θ, cos θ) de las demás,
    ponderada por 1/d², y su dirección. Se excluye Dique_pie_botadero (indicación del usuario).
  - La "verdad" de la estación evaluada es su WindDir_D1_WVT.
El consenso se recalcula en el navegador con la misma fórmula, así que el HTML permite variar las vecinas.

Uso (desde explorar_qaqc/):
    uv run python -m wind_vector.spatial_consensus
Salida: wind_vector/output/consenso_espacial.html
"""
from __future__ import annotations

import json
import re
from itertools import combinations
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DB = HERE.parents[2] / "database_duck" / "anglo_ambiental.db"
STATIONS_PY = HERE.parent / "met_viewer" / "stations.py"
OUT = HERE / "output" / "consenso_espacial.html"
SINCE = "2025-11-01"
EXCLUDED = {"Dique_pie_botadero"}


def coordinates() -> dict[str, tuple[float, float]]:
    """Coordenadas UTM de met_viewer/stations.py, leídas como texto (su import depende de anglo_reporte)."""
    src = STATIONS_PY.read_text(encoding="utf-8")
    return {m[0]: (float(m[1]), float(m[2])) for m in re.findall(r'"([^"]+)":\s+Station\((\d+), (\d+)', src)}


def angdiff(a, b):
    d = np.abs((a - b) % 360)
    return np.minimum(d, 360 - d)


def main() -> None:
    xy = coordinates()
    con = duckdb.connect(str(DB), read_only=True)
    df = con.execute(f"""
        select estacion_id st, timestamp ts, WindDir_D1_WVT d1, WindDir_Avg a, WS_ms_Avg ws
        from meteorologia where timestamp >= '{SINCE}' and WindDir_Avg is not null""").df()
    df = df[df.st.isin(xy) & ~df.st.isin(EXCLUDED)]
    df["dir"] = df.d1.fillna(df.a)
    hours = pd.date_range(df.ts.min(), df.ts.max(), freq="h")
    piv = {c: df.pivot(index="ts", columns="st", values=c).reindex(hours) for c in ("dir", "ws", "d1", "a")}
    names = sorted(piv["dir"].columns)
    has_d1 = {s: bool(piv["d1"][s].notna().any()) for s in names}

    def enc(frame: pd.DataFrame, scale: float) -> dict[str, list]:
        return {s: [None if np.isnan(x) else int(round(x * scale)) for x in frame[s].to_numpy(float)] for s in names}

    # Diferencia media entre pares (horas con ≥ 1 m/s en ambas).
    pairs = []
    for s1, s2 in combinations(names, 2):
        ok = (piv["ws"][s1] > 1) & (piv["ws"][s2] > 1) & piv["dir"][s1].notna() & piv["dir"][s2].notna()
        if ok.sum() < 500:
            continue
        e = angdiff(piv["dir"][s1][ok], piv["dir"][s2][ok])
        hr = piv["dir"].index[ok].hour
        night = (hr >= 22) | (hr <= 6)
        day = (hr >= 10) & (hr <= 17)
        km = float(np.hypot(xy[s1][0] - xy[s2][0], xy[s1][1] - xy[s2][1]) / 1000)
        pairs.append(dict(a=s1, b=s2, km=round(km, 2), n=int(ok.sum()), all=round(float(e.mean()), 1),
                          day=round(float(e[day].mean()), 1), night=round(float(e[night].mean()), 1),
                          both_d1=has_d1[s1] and has_d1[s2]))

    payload = {
        "t0": hours[0].strftime("%Y-%m-%dT%H:%M"), "n": len(hours), "names": names,
        "xy": {s: xy[s] for s in names}, "d1": has_d1,
        "dir": enc(piv["dir"], 1), "ws": enc(piv["ws"], 10), "truth": enc(piv["d1"], 1), "avg": enc(piv["a"], 1),
        "pairs": pairs, "excluded": sorted(EXCLUDED),
    }
    html = TEMPLATE.replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    OUT.write_text(html, encoding="utf-8")
    print(f"{OUT.name}: {OUT.stat().st_size / 2**20:.1f} MB, {len(names)} estaciones, {len(hours)} horas, "
          f"{len(pairs)} pares")


TEMPLATE = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Consenso espacial del viento</title>
<style>
:root{--bg:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--cons:#0b0b0b;--hl:#eda100}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;
--grid:#2c2c2a;--axis:#383835;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--cons:#f0efec;--hl:#c98500}}
:root[data-theme="dark"]{--bg:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--axis:#383835;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--cons:#f0efec;--hl:#c98500}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,Segoe UI,sans-serif}
main{max-width:1180px;margin:0 auto;padding:16px}h1{font-size:22px;margin:4px 0 4px}h2{font-size:17px;margin:28px 0 6px}
p,li{color:var(--ink2)}.card{background:var(--surface);border:1px solid var(--grid);border-radius:10px;padding:12px}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:8px 0}
.controls label{color:var(--ink2);font-size:13px}select,input,button{font:inherit;color:var(--ink);background:var(--surface);
border:1px solid var(--axis);border-radius:6px;padding:4px 8px}button{cursor:pointer}
.grid2{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,2fr);gap:12px}@media(max-width:860px){.grid2{grid-template-columns:1fr}}
svg{width:100%;height:auto;display:block}.lbl{font-size:10px;fill:var(--ink2)}.axis{stroke:var(--axis)}.gl{stroke:var(--grid)}
.tick{font-size:10px;fill:var(--muted)}table{border-collapse:collapse;width:100%;font-size:13px}
td,th{padding:4px 6px;border-bottom:1px solid var(--grid);text-align:right}th:first-child,td:first-child{text-align:left}
th{color:var(--ink2);font-weight:600}.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;color:var(--ink2);margin:6px 0}
.sw{display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:5px;border-radius:2px}
#tip{position:fixed;pointer-events:none;background:var(--surface);border:1px solid var(--axis);border-radius:6px;padding:6px 8px;
font-size:12px;display:none;z-index:9;color:var(--ink);box-shadow:0 2px 8px rgba(0,0,0,.15)}
.big{font-size:20px;font-weight:600;color:var(--ink)}code{font-size:12px}
</style></head><body><main>
<h1>Consenso espacial del viento</h1>
<p>Datos horarios de <code>database_duck</code> desde 2025-11-01. Cada flecha apunta hacia donde sopla el viento; su largo es la velocidad.
Azul: estación con dirección vectorial (<code>WindDir_D1_WVT</code>). Naranja: solo <code>WindDir_Avg</code>.</p>
<div class="card"><b>Cómo se calcula el consenso en la estación evaluada E</b>
<ol>
<li>Para cada vecina i (todas salvo E y las excluidas): u<sub>i</sub> = v<sub>i</sub>·sen θ<sub>i</sub>, w<sub>i</sub> = v<sub>i</sub>·cos θ<sub>i</sub>, con θ la dirección (D1 si existe, si no <code>WindDir_Avg</code>) y v la velocidad media.</li>
<li>Peso p<sub>i</sub> = 1/d<sub>i</sub>², con d la distancia a E en km. Solo vecinas con dato esa hora y a ≤ la distancia máxima elegida.</li>
<li>U = Σp·u / Σp, W = Σp·w / Σp; dirección de consenso = atan2(U, W).</li>
<li>Error = diferencia angular (0–180°) entre el consenso y el <code>WindDir_D1_WVT</code> de E. Horas con velocidad de E &gt; 1 m/s. «Norte»: D1 de E a ≤ 45° del norte.</li>
</ol>
<span id="excl"></span></div>

<h2>1. Mapa hora a hora</h2>
<div class="controls">
<label>Estación evaluada <select id="target"></select></label>
<label>Vecinas <select id="pool"><option value="all">toda la red</option><option value="d1">solo con D1</option></select></label>
<label>Distancia máx. (km) <input id="maxkm" type="number" value="999" min="1" style="width:80px"></label>
</div>
<div class="controls">
<button data-step="-24">−1 d</button><button data-step="-1">−1 h</button>
<input id="slider" type="range" min="0" value="0" style="flex:1;min-width:200px">
<button data-step="1">+1 h</button><button data-step="24">+1 d</button>
<input id="when" type="datetime-local" step="3600">
</div>
<div class="grid2">
<div class="card"><svg id="map" viewBox="0 0 720 520" role="img" aria-label="Mapa de vectores de viento"></svg>
<div class="legend"><span><span class="sw" style="background:var(--s1)"></span>con D1</span>
<span><span class="sw" style="background:var(--s2)"></span>solo WindDir_Avg</span>
<span><span class="sw" style="background:var(--cons)"></span>consenso en la estación evaluada (discontinua)</span>
<span><span class="sw" style="background:var(--hl)"></span>estación evaluada (real)</span></div>
<p style="font-size:12px">Fuera del mapa (entran en el cálculo con peso 1/d²): <span id="offmap"></span></p></div>
<div class="card">
<div id="hourinfo"></div>
<h3 style="font-size:14px;margin:12px 0 4px">Error en todo el año (estación evaluada, vecinas elegidas)</h3>
<table id="summary"></table>
<h3 style="font-size:14px;margin:12px 0 4px">Vecinas en esta hora (peso relativo)</h3>
<table id="nbtable"></table>
</div></div>

<h2>2. Dirección real y consenso, 7 días hasta la hora elegida</h2>
<div class="card"><svg id="ts" viewBox="0 0 1100 300" role="img" aria-label="Serie de dirección"></svg>
<div class="legend"><span><span class="sw" style="background:var(--hl)"></span>D1 real de la estación evaluada</span>
<span><span class="sw" style="background:var(--cons)"></span>consenso</span>
<span><span class="sw" style="background:var(--s2)"></span>WindDir_Avg de la propia estación</span></div></div>

<h2>3. Diferencia media de dirección entre pares de estaciones</h2>
<div class="controls"><label>Franja <select id="band"><option value="all">todas las horas</option><option value="day">día 10–17 h</option><option value="night">noche 22–06 h</option></select></label></div>
<div class="card"><svg id="pairs" viewBox="0 0 1100 380" role="img" aria-label="Diferencia por pares frente a distancia"></svg>
<div class="legend"><span><span class="sw" style="background:var(--s1)"></span>ambas con D1</span>
<span><span class="sw" style="background:var(--s2)"></span>al menos una solo con WindDir_Avg</span></div>
<p style="font-size:12px">Horas con &gt; 1 m/s en ambas estaciones. 90° es lo que da el azar (direcciones independientes).</p></div>
</main><div id="tip"></div>
<script>
const D=__DATA__;
const $=s=>document.querySelector(s), NS="http://www.w3.org/2000/svg";
const T0=new Date(D.t0+":00Z"); const N=D.n;
const fmt=i=>{const d=new Date(T0.getTime()+i*3600e3);return d.toISOString().slice(0,16).replace("T"," ")};
const rad=x=>x*Math.PI/180, deg=x=>(x*180/Math.PI+360)%360;
const ad=(a,b)=>{let d=Math.abs((a-b)%360);return Math.min(d,360-d)};
const el=(tag,attrs,parent)=>{const e=document.createElementNS(NS,tag);for(const k in attrs)e.setAttribute(k,attrs[k]);if(parent)parent.appendChild(e);return e};
const tip=$("#tip");function showTip(ev,html){tip.innerHTML=html;tip.style.display="block";tip.style.left=(ev.clientX+12)+"px";tip.style.top=(ev.clientY+12)+"px"}
function hideTip(){tip.style.display="none"}
$("#excl").textContent="Excluidas del cálculo: "+D.excluded.join(", ")+".";
const targets=D.names.filter(s=>D.d1[s]);
targets.forEach(s=>$("#target").add(new Option(s,s)));
$("#target").value="Cortadera";
const km=(a,b)=>Math.hypot(D.xy[a][0]-D.xy[b][0],D.xy[a][1]-D.xy[b][1])/1000;
// Extensión del mapa: núcleo de estaciones (se dejan fuera las lejanas)
const core=D.names.filter(s=>km(s,"Papujune")<30), off=D.names.filter(s=>!core.includes(s));
$("#offmap").textContent=off.join(", ")||"ninguna";
const xs=core.map(s=>D.xy[s][0]), ys=core.map(s=>D.xy[s][1]);
const x0=Math.min(...xs)-1500,x1=Math.max(...xs)+1500,y0=Math.min(...ys)-1500,y1=Math.max(...ys)+1500;
const sc=Math.min(720/(x1-x0),520/(y1-y0));
const px=s=>[(D.xy[s][0]-x0)*sc+(720-(x1-x0)*sc)/2, 520-((D.xy[s][1]-y0)*sc+(520-(y1-y0)*sc)/2)];
function neighbours(t){const pool=$("#pool").value, mx=+$("#maxkm").value||999;
  return D.names.filter(s=>s!==t&&(pool==="all"||D.d1[s])&&km(s,t)<=mx)}
function consensus(t,i,nb){let U=0,W=0,P=0;const used=[];
  for(const s of nb){const d=D.dir[s][i],v=D.ws[s][i];if(d==null||v==null)continue;const p=1/km(s,t)**2;
    U+=p*v/10*Math.sin(rad(d));W+=p*v/10*Math.cos(rad(d));P+=p;used.push([s,p])}
  if(!P)return null;return {dir:deg(Math.atan2(U/P,W/P)),spd:Math.hypot(U/P,W/P),used:used.map(([s,p])=>[s,p/P])}}
function arrow(g,x,y,dirFrom,spd,color,dash,w){ // flecha hacia donde sopla
  if(spd<0.3){el("circle",{cx:x,cy:y,r:4,fill:"none",stroke:color,"stroke-width":2},g);return}
  const L=Math.min(14*spd,90),a=rad(dirFrom+180),dx=Math.sin(a)*L,dy=-Math.cos(a)*L;
  el("line",{x1:x,y1:y,x2:x+dx,y2:y+dy,stroke:color,"stroke-width":w||2.5,"stroke-linecap":"round","stroke-dasharray":dash||""},g);
  const h=7,b=rad(dirFrom+180);const hx=x+dx,hy=y+dy;
  for(const s of[-1,1]){const c=b+Math.PI+s*0.45;el("line",{x1:hx,y1:hy,x2:hx+Math.sin(c)*h,y2:hy-Math.cos(c)*h,stroke:color,"stroke-width":w||2.5,"stroke-linecap":"round"},g)}}
let cur=0;
function drawMap(){const svg=$("#map");svg.innerHTML="";const t=$("#target").value,i=cur;
  el("rect",{x:0,y:0,width:720,height:520,fill:"var(--surface)"},svg);
  // barra de escala 2 km
  const bx=20,by=505;el("line",{x1:bx,y1:by,x2:bx+2000*sc,y2:by,stroke:"var(--ink2)","stroke-width":2},svg);
  el("text",{x:bx,y:by-5,class:"lbl"},svg).textContent="2 km";
  el("text",{x:700,y:20,class:"lbl","text-anchor":"end"},svg).textContent="N ↑";
  const nb=neighbours(t),c=consensus(t,i,nb),g=el("g",{},svg);
  for(const s of core){const [x,y]=px(s),d=D.dir[s][i],v=D.ws[s][i];const isT=s===t;
    const col=isT?"var(--hl)":(D.d1[s]?"var(--s1)":"var(--s2)");
    const gg=el("g",{},g);
    el("circle",{cx:x,cy:y,r:isT?6:3.5,fill:col,stroke:"var(--surface)","stroke-width":2},gg);
    if(d!=null&&v!=null)arrow(gg,x,y,d,v/10,col,"",isT?3.5:2.5);
    if(isT&&c)arrow(gg,x,y,c.dir,c.spd,"var(--cons)","5 4",2.5);
    el("text",{x:x+7,y:y-6,class:"lbl"},gg).textContent=s.replace("_CR","").slice(0,16);
    const hit=el("circle",{cx:x,cy:y,r:14,fill:"transparent"},gg);
    hit.addEventListener("mousemove",ev=>showTip(ev,`<b>${s}</b><br>${D.d1[s]?"D1":"WindDir_Avg"}: ${d==null?"—":d+"°"}<br>velocidad: ${v==null?"—":(v/10).toFixed(1)+" m/s"}<br>a ${km(s,t).toFixed(1)} km de ${t}`));
    hit.addEventListener("mouseleave",hideTip)}
  const tr=D.truth[t][i],own=D.avg[t][i];
  $("#hourinfo").innerHTML=`<div class="big">${fmt(i)}</div>
   <div>${t}: D1 real <b>${tr==null?"—":tr+"°"}</b> · WindDir_Avg ${own==null?"—":own+"°"} · velocidad ${D.ws[t][i]==null?"—":(D.ws[t][i]/10).toFixed(1)+" m/s"}</div>
   <div>Consenso: <b>${c?c.dir.toFixed(0)+"°":"—"}</b> (${c?c.spd.toFixed(1):"—"} m/s) · error <b>${c&&tr!=null?ad(c.dir,tr).toFixed(0)+"°":"—"}</b></div>`;
  const rows=c?c.used.sort((a,b)=>b[1]-a[1]).slice(0,8):[];
  $("#nbtable").innerHTML="<tr><th>Vecina</th><th>km</th><th>peso</th><th>dir.</th><th>m/s</th></tr>"+rows.map(([s,p])=>
   `<tr><td>${s}</td><td>${km(s,t).toFixed(1)}</td><td>${(100*p).toFixed(0)} %</td><td>${D.dir[s][i]}°</td><td>${(D.ws[s][i]/10).toFixed(1)}</td></tr>`).join("");
  $("#slider").value=i;$("#when").value=new Date(T0.getTime()+i*3600e3).toISOString().slice(0,16);
  drawTs()}
function summary(){const t=$("#target").value,nb=neighbours(t);const acc={all:[0,0,0,0],north:[0,0,0,0]};
  for(let i=0;i<N;i++){const tr=D.truth[t][i],v=D.ws[t][i],own=D.avg[t][i];if(tr==null||v==null||v<=10||own==null)continue;
    const c=consensus(t,i,nb);if(!c)continue;const e=ad(c.dir,tr),eo=ad(own,tr);
    for(const k of(ad(tr,0)<=45?["all","north"]:["all"])){acc[k][0]++;acc[k][1]+=e;acc[k][2]+=eo;acc[k][3]+=e>30?1:0}}
  const r=(k,l)=>{const a=acc[k];return `<tr><td>${l}</td><td>${a[0]}</td><td>${(a[2]/a[0]).toFixed(1)}°</td><td>${(a[1]/a[0]).toFixed(1)}°</td><td>${(100*a[3]/a[0]).toFixed(0)} %</td></tr>`};
  $("#summary").innerHTML="<tr><th></th><th>horas</th><th>error WindDir_Avg propio</th><th>error consenso</th><th>consenso &gt; 30°</th></tr>"+r("all","todas")+r("north","norte (±45°)")}
function drawTs(){const svg=$("#ts");svg.innerHTML="";const t=$("#target").value,nb=neighbours(t);
  const W=1100,H=300,L=40,R=10,Tp=10,B=30,a=Math.max(0,cur-167),b=cur;
  const X=i=>L+(i-a)/(b-a||1)*(W-L-R),Y=d=>Tp+(360-d)/360*(H-Tp-B);
  for(const d of[0,90,180,270,360]){el("line",{x1:L,x2:W-R,y1:Y(d),y2:Y(d),class:"gl"},svg);el("text",{x:L-6,y:Y(d)+3,class:"tick","text-anchor":"end"},svg).textContent=d+"°"}
  for(let i=a;i<=b;i++){if((i+Math.round(T0.getUTCHours()))%24===0){el("line",{x1:X(i),x2:X(i),y1:Tp,y2:H-B,class:"gl"},svg);
    el("text",{x:X(i)+3,y:H-12,class:"tick"},svg).textContent=fmt(i).slice(5,10)}}
  for(let i=a;i<=b;i++){const tr=D.truth[t][i],own=D.avg[t][i],c=consensus(t,i,nb);
    if(own!=null)el("circle",{cx:X(i),cy:Y(own),r:2.5,fill:"var(--s2)"},svg);
    if(c)el("circle",{cx:X(i),cy:Y(c.dir),r:3,fill:"none",stroke:"var(--cons)","stroke-width":1.5},svg);
    if(tr!=null)el("circle",{cx:X(i),cy:Y(tr),r:3.5,fill:"var(--hl)",stroke:"var(--surface)","stroke-width":1},svg);
    const hit=el("rect",{x:X(i)-3,y:Tp,width:6,height:H-Tp-B,fill:"transparent"},svg);
    hit.addEventListener("mousemove",ev=>showTip(ev,`${fmt(i)}<br>D1 real: ${tr??"—"}°<br>consenso: ${c?c.dir.toFixed(0):"—"}°<br>WindDir_Avg: ${own??"—"}°<br>velocidad: ${D.ws[t][i]==null?"—":(D.ws[t][i]/10).toFixed(1)} m/s`));
    hit.addEventListener("mouseleave",hideTip);hit.addEventListener("click",()=>{cur=i;drawMap()})}
  el("line",{x1:X(b),x2:X(b),y1:Tp,y2:H-B,stroke:"var(--ink2)","stroke-dasharray":"3 3"},svg)}
function drawPairs(){const svg=$("#pairs");svg.innerHTML="";const k=$("#band").value;
  const W=1100,H=380,L=44,R=10,Tp=10,B=34,mx=Math.ceil(Math.max(...D.pairs.map(p=>p.km))/10)*10;
  const lx=v=>Math.log10(Math.max(v,0.3)),X=v=>L+(lx(v)-lx(0.5))/(lx(mx)-lx(0.5))*(W-L-R),Y=d=>Tp+(120-d)/120*(H-Tp-B);
  for(const d of[0,30,60,90,120]){el("line",{x1:L,x2:W-R,y1:Y(d),y2:Y(d),class:"gl"},svg);el("text",{x:L-6,y:Y(d)+3,class:"tick","text-anchor":"end"},svg).textContent=d+"°"}
  for(const v of[0.5,1,2,5,10,20,50,100,200].filter(v=>v<=mx)){el("line",{x1:X(v),x2:X(v),y1:Tp,y2:H-B,class:"gl"},svg);el("text",{x:X(v),y:H-16,class:"tick","text-anchor":"middle"},svg).textContent=v+" km"}
  el("text",{x:W-R,y:H-2,class:"tick","text-anchor":"end"},svg).textContent="distancia entre estaciones (escala log)";
  for(const p of D.pairs){const c=p.both_d1?"var(--s1)":"var(--s2)";
    const dot=el("circle",{cx:X(p.km),cy:Y(Math.min(p[k],120)),r:4.5,fill:c,stroke:"var(--surface)","stroke-width":1.5},svg);
    dot.addEventListener("mousemove",ev=>showTip(ev,`<b>${p.a} – ${p.b}</b><br>${p.km} km · ${p.n} h<br>todas ${p.all}° · día ${p.day}° · noche ${p.night}°`));
    dot.addEventListener("mouseleave",hideTip)}}
$("#slider").max=N-1;
document.querySelectorAll("button[data-step]").forEach(b=>b.onclick=()=>{cur=Math.min(N-1,Math.max(0,cur+ +b.dataset.step));drawMap()});
$("#slider").oninput=e=>{cur=+e.target.value;drawMap()};
$("#when").onchange=e=>{const i=Math.round((new Date(e.target.value+":00Z")-T0)/3600e3);if(i>=0&&i<N){cur=i;drawMap()}};
for(const id of["#target","#pool","#maxkm"])$(id).onchange=()=>{drawMap();summary()};
$("#band").onchange=drawPairs;
// arranque: primera hora de la última semana con viento del norte en la estación evaluada
cur=N-1;for(let i=N-1;i>N-24*30;i--){const tr=D.truth.Cortadera[i];if(tr!=null&&ad(tr,0)<=20&&D.ws.Cortadera[i]>20){cur=i;break}}
drawMap();summary();drawPairs();
</script></body></html>"""


if __name__ == "__main__":
    main()
