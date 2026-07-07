"""Two-sided predicted-bracket SVG (reference-style): R32 flows inward from both
edges to a centre final, with flags and connector lines. Reads bracket.json."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
B = json.loads((REPO / "model" / "data" / "bracket.json").read_text())
OUT = REPO / "model" / "data" / "bracket.svg"

CODE3 = {
    "South Africa": "RSA", "Canada": "CAN", "Germany": "GER", "Paraguay": "PAR",
    "Netherlands": "NED", "Morocco": "MAR", "Brazil": "BRA", "Japan": "JPN",
    "France": "FRA", "Sweden": "SWE", "Ivory Coast": "CIV", "Norway": "NOR",
    "Mexico": "MEX", "Ecuador": "ECU", "England": "ENG", "DR Congo": "COD",
    "United States": "USA", "Bosnia and Herzegovina": "BIH", "Belgium": "BEL",
    "Senegal": "SEN", "Portugal": "POR", "Croatia": "CRO", "Spain": "ESP",
    "Austria": "AUT", "Switzerland": "SUI", "Algeria": "ALG", "Argentina": "ARG",
    "Cape Verde": "CPV", "Colombia": "COL", "Ghana": "GHA", "Australia": "AUS", "Egypt": "EGY",
}
ISO = {
    "South Africa": "za", "Canada": "ca", "Germany": "de", "Paraguay": "py",
    "Netherlands": "nl", "Morocco": "ma", "Brazil": "br", "Japan": "jp",
    "France": "fr", "Sweden": "se", "Ivory Coast": "ci", "Norway": "no",
    "Mexico": "mx", "Ecuador": "ec", "England": "gb-eng", "DR Congo": "cd",
    "United States": "us", "Bosnia and Herzegovina": "ba", "Belgium": "be",
    "Senegal": "sn", "Portugal": "pt", "Croatia": "hr", "Spain": "es",
    "Austria": "at", "Switzerland": "ch", "Algeria": "dz", "Argentina": "ar",
    "Cape Verde": "cv", "Colombia": "co", "Ghana": "gh", "Australia": "au", "Egypt": "eg",
}
FLAG = "https://flagcdn.com/w80/{}.png"  # PNG renders reliably inside SVG <image>

r = B["rounds"]
R32 = {int(k): v for k, v in r["R32"].items()}
R16 = {int(k): v for k, v in r["R16"].items()}
QF = {int(k): v for k, v in r["QF"].items()}
SF = r["SF"]
FIN = r["Final"]["FINAL"]
CH = B["champion"]

# bracket order (top->bottom) per half
L_R32 = [74, 77, 73, 75, 83, 84, 81, 82]
L_R16 = [89, 90, 93, 94]   # 89=74v77 90=73v75 93=83v84 94=81v82
L_QF = [97, 98]            # 97=89v90 98=93v94
R_R32 = [76, 78, 79, 80, 86, 88, 85, 87]
R_R16 = [91, 92, 95, 96]
R_QF = [99, 100]           # 99=91v92 100=95v96

W, H = 1520, 900
TOP, BOT = 84, 868
STEP = (BOT - TOP) / 8
BH = 46
LX = {"r32": 16, "r16": 202, "qf": 372, "sf": 528}
RX = {"r32": 1352, "r16": 1166, "qf": 1006, "sf": 838}
LW = {"r32": 156, "r16": 150, "qf": 138, "sf": 150}
FX, FW, FCY = 690, 150, (TOP + BOT) / 2
PANEL, GREEN, GOLD, DIM, TEXT = "#F5F1EC", "#1F7A52", "#9A6B00", "#6B7686", "#3A4D63"
PILLBG = "#E3DED7"  # matches the R32 card's pick-pill
LINE, BORDER, DIVIDER = "rgba(26,26,26,.22)", "rgba(26,26,26,.12)", "rgba(26,26,26,.07)"


def adv(g):
    w = g["adv_home"] if g["winner"] == g["home"] else g["adv_away"]
    return f"{round(w*100)}%"


def box(x, w, cy, g, gold=False):
    y = cy - BH / 2
    bd = GOLD if gold else BORDER
    s = [f'<rect x="{x}" y="{y:.0f}" width="{w}" height="{BH}" rx="9" fill="{PANEL}" stroke="{bd}" stroke-width="{1.4 if gold else 1}"/>']
    for k, t in enumerate([g["home"], g["away"]]):
        ty = y + (BH * 0.30 if k == 0 else BH * 0.70)
        won = t == g["winner"]
        col = (GOLD if gold else GREEN) if won else DIM
        u = FLAG.format(ISO[t])
        s.append(f'<image href="{u}" xlink:href="{u}" x="{x+9}" y="{ty-7.5:.1f}" width="21" height="15" preserveAspectRatio="xMidYMid slice"/>')
        s.append(f'<text x="{x+38}" y="{ty:.1f}" fill="{col}" font-family="ui-monospace,monospace" font-size="13.5" font-weight="{600 if won else 400}" dominant-baseline="middle">{CODE3[t]}</text>')
        if won:
            s.append(f'<rect x="{x+w-46}" y="{ty-9:.1f}" width="40" height="18" rx="9" fill="{"#EFE3C4" if gold else PILLBG}"/>')
            s.append(f'<text x="{x+w-12}" y="{ty:.1f}" fill="{col}" font-family="ui-monospace,monospace" font-size="10.5" text-anchor="end" dominant-baseline="middle">{adv(g)}</text>')
    s.append(f'<line x1="{x+8}" y1="{cy:.0f}" x2="{x+w-8}" y2="{cy:.0f}" stroke="{DIVIDER}"/>')
    return "".join(s)


def conn(xa, cy1, cy2, xb, cyn):
    mx = (xa + xb) / 2
    return (f'<path d="M{xa},{cy1:.0f} H{mx:.0f} M{xa},{cy2:.0f} H{mx:.0f} '
            f'M{mx:.0f},{cy1:.0f} V{cy2:.0f} M{mx:.0f},{cyn:.0f} H{xb}" fill="none" stroke="{LINE}"/>')


def lbl(x, cy, num, w):
    return f'<text x="{x+w/2:.0f}" y="{cy-BH/2-5:.0f}" fill="{DIM}" font-size="9" text-anchor="middle" letter-spacing="1">M{num}</text>'


cyL32 = {n: TOP + i * STEP + STEP / 2 for i, n in enumerate(L_R32)}
cyL16 = {n: (cyL32[L_R32[2 * i]] + cyL32[L_R32[2 * i + 1]]) / 2 for i, n in enumerate(L_R16)}
cyLqf = {n: (cyL16[L_R16[2 * i]] + cyL16[L_R16[2 * i + 1]]) / 2 for i, n in enumerate(L_QF)}
cyLsf = (cyLqf[97] + cyLqf[98]) / 2
cyR32 = {n: TOP + i * STEP + STEP / 2 for i, n in enumerate(R_R32)}
cyR16 = {n: (cyR32[R_R32[2 * i]] + cyR32[R_R32[2 * i + 1]]) / 2 for i, n in enumerate(R_R16)}
cyRqf = {n: (cyR16[R_R16[2 * i]] + cyR16[R_R16[2 * i + 1]]) / 2 for i, n in enumerate(R_QF)}
cyRsf = (cyRqf[99] + cyRqf[100]) / 2

s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" font-family="ui-sans-serif,system-ui">']
s.append(f'<text x="{W/2:.0f}" y="46" fill="{DIM}" font-size="12.5" text-anchor="middle">Poisson model · favourite advances (90′ + extra time + penalties)</text>')

# ---- connectors (behind) ----
xr = LX["r32"] + LW["r32"]
for i, n in enumerate(L_R16):
    s.append(conn(xr, cyL32[L_R32[2 * i]], cyL32[L_R32[2 * i + 1]], LX["r16"], cyL16[n]))
xr = LX["r16"] + LW["r16"]
for i, n in enumerate(L_QF):
    s.append(conn(xr, cyL16[L_R16[2 * i]], cyL16[L_R16[2 * i + 1]], LX["qf"], cyLqf[n]))
s.append(conn(LX["qf"] + LW["qf"], cyLqf[97], cyLqf[98], LX["sf"], cyLsf))
s.append(conn(LX["sf"] + LW["sf"], cyLsf, cyLsf, FX, FCY))
# right (mirrored: feeder LEFT edge -> target RIGHT edge)
xl = RX["r32"]
for i, n in enumerate(R_R16):
    s.append(conn(xl, cyR32[R_R32[2 * i]], cyR32[R_R32[2 * i + 1]], RX["r16"] + LW["r16"], cyR16[n]))
xl = RX["r16"]
for i, n in enumerate(R_QF):
    s.append(conn(xl, cyR16[R_R16[2 * i]], cyR16[R_R16[2 * i + 1]], RX["qf"] + LW["qf"], cyRqf[n]))
s.append(conn(RX["qf"], cyRqf[99], cyRqf[100], RX["sf"] + LW["sf"], cyRsf))
s.append(conn(RX["sf"], cyRsf, cyRsf, FX + FW, FCY))

# ---- boxes ----
for n in L_R32:
    s.append(lbl(LX["r32"], cyL32[n], n, LW["r32"]) + box(LX["r32"], LW["r32"], cyL32[n], R32[n]))
for n in L_R16:
    s.append(lbl(LX["r16"], cyL16[n], n, LW["r16"]) + box(LX["r16"], LW["r16"], cyL16[n], R16[n]))
for n in L_QF:
    s.append(lbl(LX["qf"], cyLqf[n], n, LW["qf"]) + box(LX["qf"], LW["qf"], cyLqf[n], QF[n]))
s.append(box(LX["sf"], LW["sf"], cyLsf, SF["SF1"]))
for n in R_R32:
    s.append(lbl(RX["r32"], cyR32[n], n, LW["r32"]) + box(RX["r32"], LW["r32"], cyR32[n], R32[n]))
for n in R_R16:
    s.append(lbl(RX["r16"], cyR16[n], n, LW["r16"]) + box(RX["r16"], LW["r16"], cyR16[n], R16[n]))
for n in R_QF:
    s.append(lbl(RX["qf"], cyRqf[n], n, LW["qf"]) + box(RX["qf"], LW["qf"], cyRqf[n], QF[n]))
s.append(box(RX["sf"], LW["sf"], cyRsf, SF["SF2"]))

# semifinal labels
s.append(f'<text x="{LX["sf"]+LW["sf"]/2:.0f}" y="{cyLsf-BH/2-22:.0f}" fill="{DIM}" font-size="11" letter-spacing="1.5" text-anchor="middle">SEMIFINAL 1</text>')
s.append(f'<text x="{RX["sf"]+LW["sf"]/2:.0f}" y="{cyRsf-BH/2-22:.0f}" fill="{DIM}" font-size="11" letter-spacing="1.5" text-anchor="middle">SEMIFINAL 2</text>')

# ---- final + champion ----
s.append(f'<text x="{FX+FW/2:.0f}" y="{FCY-72:.0f}" fill="{TEXT}" font-size="15" letter-spacing="2" text-anchor="middle" font-weight="600">FINAL</text>')
s.append(box(FX, FW, FCY - 30, FIN, gold=True))
# champion plate
cyc = FCY + 70
s.append(f'<rect x="{FX-6}" y="{cyc-32:.0f}" width="{FW+12}" height="80" rx="10" fill="#FBF4E2" stroke="{GOLD}" stroke-width="1.6"/>')
s.append(f'<text x="{FX+FW/2:.0f}" y="{cyc-12:.0f}" fill="{GOLD}" font-size="10" letter-spacing="2" text-anchor="middle">CHAMPION</text>')
s.append(f'<image href="{FLAG.format(ISO[CH])}" xlink:href="{FLAG.format(ISO[CH])}" x="{FX+FW/2-15:.0f}" y="{cyc-2:.0f}" width="30" height="21" preserveAspectRatio="xMidYMid slice"/>')
s.append(f'<text x="{FX+FW/2:.0f}" y="{cyc+40:.0f}" fill="{GOLD}" font-size="19" font-weight="700" text-anchor="middle" font-family="ui-monospace,monospace">{CODE3[CH]}</text>')

s.append("</svg>")
svg = "".join(s)
OUT.write_text(svg)
# Also emit as a TS module so the page can inline it (inline SVG loads the
# external flag <image> elements; an <img src> SVG cannot).
TS = REPO / "src" / "data" / "world-cup" / "bracket-svg.ts"
esc = svg.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
TS.write_text("// Auto-generated by model/bracket_svg.py — do not edit.\nexport const BRACKET_SVG = `" + esc + "`;\n")
print(f"wrote {OUT.relative_to(REPO)} + {TS.relative_to(REPO)} ({len(svg)} bytes); champion {CH}")
