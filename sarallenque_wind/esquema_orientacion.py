"""Esquema en planta (vista desde arriba, norte arriba) de la interpretación de FINDINGS.md §9:
orientación del WindSonic, bloqueo de la cara sur y desplazamiento del shelter del 2026-09-25.

Uso (desde explorar_qaqc/):
    uv run python sarallenque_wind/esquema_orientacion.py

Salida: sarallenque_wind/esquema_orientacion_sarallenque.html (SVG en línea, sin dependencias).
No es un reporte de datos: posiciones y tamaños son supuestos; los ángulos del viento son las
medianas vectoriales (sin calmas) calculadas con rosas_orientacion.direccion_mediana.
"""
from __future__ import annotations

import math
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent / "esquema_orientacion_sarallenque.html"

DIA, NOCHE = "#eb6834", "#2a78d6"            # mismos colores de franja que build_report.py
INK, INK_2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
SURFACE, PAGE, SHELTER, OBST = "#fcfcfb", "#f9f9f7", "#c3c2b7", "#6b6a64"
W, H = 440, 440
CX, CY = 220, 215                             # posición del sensor en cada panel


def pt(rumbo: float, r: float, cx: float = CX, cy: float = CY) -> tuple[float, float]:
    """Punto a distancia r en el rumbo dado (0 = N, horario), en coordenadas SVG."""
    a = math.radians(rumbo)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def flecha(x1, y1, x2, y2, color, ancho=3, guion="", marca="f"):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="{ancho}" stroke-dasharray="{guion}" marker-end="url(#{marca}{color[1:]})"/>')


def viento(desde: float, color: str, r0=185, r1=70, sep=34, n=3, ancho=3, cx=CX, cy=CY) -> str:
    """n flechas paralelas que llegan desde el rumbo `desde` y van hacia el sensor."""
    out = []
    for k in range(n):
        d = (k - (n - 1) / 2) * sep
        ox, oy = pt(desde + 90, d, cx, cy)
        (x1, y1), (x2, y2) = pt(desde, r0, ox, oy), pt(desde, r1, ox, oy)
        out.append(flecha(x1, y1, x2, y2, color, ancho))
    return "".join(out)


def texto(x, y, t, color=INK_2, tam=12, anc="middle", peso=400):
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-size="{tam}" text-anchor="{anc}" '
            f'font-weight="{peso}">{t}</text>')


def rosa_n(x=W - 30, y=34) -> str:
    return (flecha(x, y + 16, x, y - 12, INK, 2) + texto(x, y + 32, "N", INK, 12, peso=600))


def sensor(marca_n: float, cx=CX, cy=CY) -> str:
    """WindSonic: círculo con la marca N del sensor (hacia dónde cree que está el norte)."""
    x2, y2 = pt(marca_n, 30, cx, cy)
    return (f'<circle cx="{cx}" cy="{cy}" r="11" fill="{SURFACE}" stroke="{INK}" stroke-width="2"/>'
            + flecha(cx, cy, x2, y2, INK, 2, marca="m")
            + (texto(cx + 16, y2 + 4, "N sensor", INK, 11, "start", 600) if marca_n > 90
               else texto(cx - 16, y2 + 10, "N sensor", INK, 11, "end", 600)))


def shelter(cx, cy, fantasma=False) -> str:
    """Shelter al norte del sensor; el sensor va en un mástil sujeto a su cara sur."""
    if fantasma:
        return (f'<rect x="{cx - 28}" y="{cy - 68}" width="56" height="36" rx="3" fill="none" stroke="{MUTED}" '
                f'stroke-width="1.5" stroke-dasharray="5 4"/>')
    return (f'<rect x="{cx - 28}" y="{cy - 68}" width="56" height="36" rx="3" fill="{SHELTER}" stroke="{INK_2}"/>'
            + texto(cx, cy - 46, "shelter", INK_2, 10)
            + f'<line x1="{cx}" y1="{cy - 32}" x2="{cx}" y2="{cy - 11}" stroke="{INK_2}" stroke-width="2"/>')


def obstaculo(x, y, w, h, etiqueta, lx, ly, anc="middle") -> str:
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#rayado)" stroke="{OBST}" stroke-width="1.5"/>'
            + "".join(texto(lx, ly + 14 * i, t, INK_2, 11, anc) for i, t in enumerate(etiqueta)))


def lecturas(filas: list[tuple[str, str, str]]) -> str:
    """Tabla bajo cada panel: (qué, día, noche)."""
    y0 = H - 58
    out = [texto(20, y0, "", INK)]
    out.append(texto(250, y0, "día", DIA, 11, peso=600) + texto(330, y0, "noche", NOCHE, 11, peso=600))
    for i, (q, d, n) in enumerate(filas):
        y = y0 + 16 * (i + 1)
        out.append(texto(20, y, q, INK_2, 11, "start") + texto(250, y, d, INK, 11) + texto(330, y, n, INK, 11))
    return "".join(out)


def svg(titulo: str, cuerpo: str, alto: int = H) -> str:
    marcas = "".join(
        f'<marker id="f{c[1:]}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
        f'<marker id="m{c[1:]}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for c in (DIA, NOCHE, INK, MUTED))
    return (f'<figure><figcaption>{titulo}</figcaption>'
            f'<svg viewBox="0 0 {W} {alto}" role="img" aria-label="{titulo}"><defs>{marcas}'
            f'<pattern id="rayado" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="6" height="6" fill="{SURFACE}"/><line x1="0" y1="0" x2="0" y2="6" stroke="{OBST}" stroke-width="2"/></pattern>'
            f'</defs><rect width="{W}" height="{alto}" fill="{SURFACE}"/>{cuerpo}</svg></figure>')


# ── paneles ──────────────────────────────────────────────────────────────────

def panel_0() -> str:
    """Un sensor con la marca N al sur lee cada viento en el rumbo opuesto."""
    c = [rosa_n(), sensor(180, cy=190)]
    c.append(viento(90, NOCHE, r0=175, r1=40, n=1, cy=190))
    c.append(texto(CX + 120, 170, "llega desde el E (90°)", NOCHE, 12))
    # lo que el logger cree: dirección opuesta
    x1, y1 = pt(270, 175, cy=190)
    x2, y2 = pt(270, 40, cy=190)
    c.append(flecha(x1, y1, x2, y2, MUTED, 3, "7 5"))
    c.append(texto(CX - 120, 170, "se registra desde el O (270°)", INK_2, 12))
    c.append(texto(CX, 300, "El sensor mide el ángulo respecto a su marca N.", INK_2, 12))
    c.append(texto(CX, 318, "Con la marca apuntando al sur, cada viento queda registrado", INK_2, 12))
    c.append(texto(CX, 336, "en el rumbo opuesto: registrado = real + 180°.", INK_2, 12))
    return svg("0 · Sensor con la marca N hacia el sur", "".join(c), 370)


def panel_a() -> str:
    c = [rosa_n(), shelter(CX, CY), sensor(0)]
    c.append(viento(238, DIA))
    c.append(viento(74, NOCHE))
    c.append(texto(CX, 40,"Ubicación anterior (sin coordenada conocida)", MUTED, 11))
    c.append(lecturas([("Registrado = real", "238°", "74°"), ("MQG, mismo periodo", "232°", "95°"),
                       ("Velocidad / MQG", "0.51", "0.68")]))
    return svg("A · Antes del traslado · jul-2024 → jul-2025", "".join(c))


def panel_b() -> str:
    c = [rosa_n(), shelter(CX, CY), sensor(180)]
    # obstáculo al S–SO del sensor
    c.append(obstaculo(CX - 110, CY + 30, 90, 28, ["cara sur tapada", "(elemento sin identificar)"], CX - 10, CY + 76, "start"))
    # noche: llega libre desde el ENE
    c.append(viento(83, NOCHE))
    # día: el flujo del SO choca con el obstáculo (las flechas acaban en su borde inferior)...
    for rumbo in (215, 235):
        r = 32 / -math.cos(math.radians(rumbo))            # hasta y = CY + 32
        x1, y1 = pt(rumbo, 190)
        x2, y2 = pt(rumbo, r)
        c.append(flecha(x1, y1, x2, y2, DIA, 3))
    # ...y lo rodea por el oeste: la curva entra al sensor en la línea de 313° (llega desde el NO)
    x0, y0 = pt(250, 185)
    xc, yc = pt(313, 85)
    x1, y1 = pt(313, 16)
    c.append(f'<path d="M{x0:.1f},{y0:.1f} Q{xc:.1f},{yc:.1f} {x1:.1f},{y1:.1f}" fill="none" stroke="{DIA}" '
             f'stroke-width="3" marker-end="url(#f{DIA[1:]})"/>')
    c.append(texto(CX - 150, CY - 70, "rodea el obstáculo", DIA, 11, "start")
             + texto(CX - 150, CY - 56, "y llega desde el NO", DIA, 11, "start"))
    c.append(lecturas([("Registrado (sensor girado)", "133°", "263°"), ("Real = registrado + 180°", "313°", "83°"),
                       ("MQG, mismo periodo", "239°", "87°")]))
    return svg("B · Tras el traslado · nov-2025 → 25-sep-2026", "".join(c))


def panel_c() -> str:
    dx = 70                                        # desplazamiento al este (exagerado)
    c = [rosa_n(), shelter(CX - dx, CY, fantasma=True), shelter(CX, CY), sensor(0)]
    c.append(flecha(CX - dx, CY - 78, CX - 6, CY - 78, MUTED, 2, marca="m"))
    c.append(texto(CX - dx / 2, CY - 86, "desplazado unos m al E", MUTED, 11))
    # el obstáculo no se mueve: ahora queda al oeste de la línea SO → sensor
    c.append(obstaculo(CX - 110 - dx, CY + 30, 90, 28, ["mismo elemento:", "ya no tapa la cara sur"],
                       CX - 65 - dx, CY + 2))
    # cobertura al este; la noche la atraviesa → flechas finas
    c.append(obstaculo(CX + 40, CY - 40, 16, 80, ["cara este", "más cubierta"], CX + 64, CY + 60, "start"))
    c.append(viento(213, DIA))
    c.append(viento(74, NOCHE, r1=28, sep=30, n=2, ancho=1.5))
    c.append(lecturas([("Registrado = real", "213°", "74°"), ("MQG, mismo periodo (~1 día)", "237°", "45°"),
                       ("Velocidad / MQG (~1 día)", "0.42", "0.42")]))
    return svg("C · Desde el 25-sep-2026 20:00 · orientado al norte", "".join(c))


LEYENDA = f"""<ul class="ley">
<li><span style="background:{DIA}"></span>viento de día (10–17 h)</li>
<li><span style="background:{NOCHE}"></span>viento de noche (22–06 h)</li>
<li><span class="dash"></span>dirección registrada, cuando no es la real</li>
<li><span class="obs"></span>obstáculo o cobertura</li></ul>"""

NOTA = ("Vista en planta, norte arriba. Esquema, no a escala: tamaños, distancias y la posición del obstáculo son "
        "supuestos; el desplazamiento del panel C está exagerado. Las flechas indican hacia dónde va el aire; "
        "su rumbo de origen es la mediana vectorial sin calmas de cada periodo. Flechas finas en C: velocidad "
        "nocturna menor respecto a MQG, con ~1 día de datos. Interpretación completa en met_viewer/FINDINGS.md §9; "
        "rosas en rosas_orientacion_sarallenque.html.")


def main() -> None:
    OUTPUT.write_text(f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Esquema de Sarallenque</title>
<style>
 body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:{PAGE};color:{INK};margin:0;padding:16px}}
 main{{max-width:960px;margin:auto}} h1{{font-size:19px;margin:4px 0}} p{{color:{INK_2};font-size:13px;line-height:1.45}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:16px}}
 figure{{margin:0;background:{SURFACE};border:1px solid rgba(11,11,11,.1);border-radius:8px;padding:8px}}
 figcaption{{font-weight:600;font-size:14px;padding:4px 6px}} svg{{width:100%;height:auto;display:block}}
 .ley{{display:flex;flex-wrap:wrap;gap:16px;list-style:none;padding:0;font-size:13px;color:{INK_2}}}
 .ley span{{display:inline-block;width:22px;height:4px;vertical-align:middle;margin-right:6px}}
 .ley .dash{{height:0;border-top:3px dashed {MUTED}}}
 .ley .obs{{height:12px;background:repeating-linear-gradient(45deg,{OBST} 0 2px,{SURFACE} 2px 5px);border:1px solid {OBST}}}
</style></head><body><main>
<h1>Sarallenque · esquema de orientación, bloqueo y desplazamiento del shelter</h1>
{LEYENDA}
<div class="grid">{panel_0()}{panel_a()}{panel_b()}{panel_c()}</div>
<p>{NOTA}</p></main></body></html>""", encoding="utf-8")
    print(f"HTML: {OUTPUT}")


if __name__ == "__main__":
    main()
