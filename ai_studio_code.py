import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import json
# (st.iframe replaces components.v1.html below — no extra import needed)

# ==========================================
# 1. SCIENTIFIC DATA (Zero-Dependency)
# ==========================================
# [Pauling electronegativity (chi), covalent radius (Angstrom), Jmol/CPK color]
# Coverage: H -> Pu. Anything beyond this falls back to a neutral
# heuristic placeholder in get_el_data() instead of crashing — this IS the
# documented "first-principles fallback" architecture.
# PRODUCTION NOTE: swap ELEMENTS/GROUP_BLOCK for a live pymatgen/mendeleev
# lookup if citation-grade constants are ever required.
ELEMENTS = {
    "H": [2.20, 0.37, "#FFFFFF"], "He": [0.00, 0.32, "#D9FFFF"],
    "Li": [0.98, 1.34, "#CC80FF"], "Be": [1.57, 0.90, "#C2FF00"],
    "B": [2.04, 0.82, "#FFB5B5"], "C": [2.55, 0.77, "#909090"],
    "N": [3.04, 0.75, "#3050F8"], "O": [3.44, 0.73, "#FF0D0D"],
    "F": [3.98, 0.71, "#90E050"], "Ne": [0.00, 0.69, "#B3E3F5"],
    "Na": [0.93, 1.54, "#AB5CF2"], "Mg": [1.31, 1.30, "#8AFF00"],
    "Al": [1.61, 1.18, "#BFA6A6"], "Si": [1.90, 1.11, "#F0C8A0"],
    "P": [2.19, 1.06, "#FF8000"], "S": [2.58, 1.02, "#FFFF30"],
    "Cl": [3.16, 0.99, "#1FF01F"], "Ar": [0.00, 0.97, "#80D1E3"],
    "K": [0.82, 1.96, "#8F40D4"], "Ca": [1.00, 1.74, "#3DFF00"],
    "Sc": [1.36, 1.44, "#E6E6E6"], "Ti": [1.54, 1.36, "#BFC2C7"],
    "V": [1.63, 1.25, "#A6A6AB"], "Cr": [1.66, 1.27, "#8A99C7"],
    "Mn": [1.55, 1.39, "#9C7AC7"], "Fe": [1.83, 1.25, "#E06633"],
    "Co": [1.88, 1.26, "#F090A0"], "Ni": [1.91, 1.21, "#50D050"],
    "Cu": [1.90, 1.38, "#C88033"], "Zn": [1.65, 1.31, "#7D80B0"],
    "Ga": [1.81, 1.26, "#C28F8F"], "Ge": [2.01, 1.22, "#668F8F"],
    "As": [2.18, 1.19, "#BD80E3"], "Se": [2.55, 1.16, "#FFA100"],
    "Br": [2.96, 1.14, "#A62929"], "Kr": [3.00, 1.10, "#5CB8D1"],
    "Rb": [0.82, 2.11, "#702EB0"], "Sr": [0.95, 1.92, "#00FF00"],
    "Y": [1.22, 1.62, "#94FFFF"], "Zr": [1.33, 1.48, "#94E0E0"],
    "Nb": [1.60, 1.37, "#73C2C9"], "Mo": [2.16, 1.45, "#54B5B5"],
    "Tc": [1.90, 1.56, "#3B9E9E"], "Ru": [2.20, 1.26, "#248F8F"],
    "Rh": [2.28, 1.35, "#0A7D8C"], "Pd": [2.20, 1.31, "#006985"],
    "Ag": [1.93, 1.53, "#C0C0C0"], "Cd": [1.69, 1.48, "#FFD98F"],
    "In": [1.78, 1.44, "#A67573"], "Sn": [1.96, 1.41, "#668080"],
    "Sb": [2.05, 1.38, "#9E63B5"], "Te": [2.10, 1.35, "#D47A00"],
    "I": [2.66, 1.33, "#940094"], "Xe": [2.60, 1.30, "#429EB0"],
    "Cs": [0.79, 2.25, "#57178F"], "Ba": [0.89, 1.98, "#00C900"],
    "La": [1.10, 1.69, "#70D4FF"], "Ce": [1.12, 1.65, "#FFFFC7"],
    "Pr": [1.13, 1.65, "#D9FFC7"], "Nd": [1.14, 1.64, "#C7FFC7"],
    "Pm": [1.13, 1.63, "#A3FFC7"], "Sm": [1.17, 1.62, "#8FFFC7"],
    "Eu": [1.20, 1.85, "#61FFC7"], "Gd": [1.20, 1.61, "#45FFC7"],
    "Tb": [1.10, 1.59, "#30FFC7"], "Dy": [1.22, 1.59, "#1FFFC7"],
    "Ho": [1.23, 1.58, "#00FF9C"], "Er": [1.24, 1.57, "#00E675"],
    "Tm": [1.25, 1.56, "#00D452"], "Yb": [1.10, 1.74, "#00BF38"],
    "Lu": [1.27, 1.56, "#00AB24"], "Hf": [1.30, 1.50, "#4DC2FF"],
    "Ta": [1.50, 1.38, "#4DA6FF"], "W": [2.36, 1.46, "#2194D6"],
    "Re": [1.90, 1.59, "#267DAB"], "Os": [2.20, 1.28, "#266696"],
    "Ir": [2.20, 1.37, "#175487"], "Pt": [2.28, 1.28, "#D0D0E0"],
    "Au": [2.54, 1.44, "#FFD123"], "Hg": [2.00, 1.49, "#B8B8D0"],
    "Tl": [1.62, 1.48, "#A6544D"], "Pb": [2.33, 1.47, "#575961"],
    "Bi": [2.02, 1.46, "#9E4FB5"], "Po": [2.00, 1.40, "#AB5C00"],
    "At": [2.20, 1.45, "#754F45"], "Rn": [0.00, 1.45, "#428296"],
    "Fr": [0.70, 2.60, "#420066"], "Ra": [0.90, 2.21, "#007D00"],
    "Ac": [1.10, 2.15, "#70ABFA"], "Th": [1.30, 2.06, "#00BAFF"],
    "Pa": [1.50, 2.00, "#00A1FF"], "U": [1.38, 1.96, "#008FFF"],
    "Np": [1.36, 1.90, "#0080FF"], "Pu": [1.28, 1.87, "#006BFF"],
}

# Group (1-18, or 'Lanthanide'/'Actinide' for the f-block rows) and block
# ('s'/'p'/'d'/'f') — used to infer d-/f-orbital presence per the spec.
GROUP_BLOCK = {
    "H": (1, "s"), "He": (18, "s"),
    "Li": (1, "s"), "Be": (2, "s"), "B": (13, "p"), "C": (14, "p"), "N": (15, "p"),
    "O": (16, "p"), "F": (17, "p"), "Ne": (18, "p"),
    "Na": (1, "s"), "Mg": (2, "s"), "Al": (13, "p"), "Si": (14, "p"), "P": (15, "p"),
    "S": (16, "p"), "Cl": (17, "p"), "Ar": (18, "p"),
    "K": (1, "s"), "Ca": (2, "s"), "Sc": (3, "d"), "Ti": (4, "d"), "V": (5, "d"),
    "Cr": (6, "d"), "Mn": (7, "d"), "Fe": (8, "d"), "Co": (9, "d"), "Ni": (10, "d"),
    "Cu": (11, "d"), "Zn": (12, "d"), "Ga": (13, "p"), "Ge": (14, "p"), "As": (15, "p"),
    "Se": (16, "p"), "Br": (17, "p"), "Kr": (18, "p"),
    "Rb": (1, "s"), "Sr": (2, "s"), "Y": (3, "d"), "Zr": (4, "d"), "Nb": (5, "d"),
    "Mo": (6, "d"), "Tc": (7, "d"), "Ru": (8, "d"), "Rh": (9, "d"), "Pd": (10, "d"),
    "Ag": (11, "d"), "Cd": (12, "d"), "In": (13, "p"), "Sn": (14, "p"), "Sb": (15, "p"),
    "Te": (16, "p"), "I": (17, "p"), "Xe": (18, "p"),
    "Cs": (1, "s"), "Ba": (2, "s"),
    "La": ("Lanthanide", "f"), "Ce": ("Lanthanide", "f"), "Pr": ("Lanthanide", "f"),
    "Nd": ("Lanthanide", "f"), "Pm": ("Lanthanide", "f"), "Sm": ("Lanthanide", "f"),
    "Eu": ("Lanthanide", "f"), "Gd": ("Lanthanide", "f"), "Tb": ("Lanthanide", "f"),
    "Dy": ("Lanthanide", "f"), "Ho": ("Lanthanide", "f"), "Er": ("Lanthanide", "f"),
    "Tm": ("Lanthanide", "f"), "Yb": ("Lanthanide", "f"), "Lu": ("Lanthanide", "f"),
    "Hf": (4, "d"), "Ta": (5, "d"), "W": (6, "d"), "Re": (7, "d"), "Os": (8, "d"),
    "Ir": (9, "d"), "Pt": (10, "d"), "Au": (11, "d"), "Hg": (12, "d"), "Tl": (13, "p"),
    "Pb": (14, "p"), "Bi": (15, "p"), "Po": (16, "p"), "At": (17, "p"), "Rn": (18, "p"),
    "Fr": (1, "s"), "Ra": (2, "s"),
    "Ac": ("Actinide", "f"), "Th": ("Actinide", "f"), "Pa": ("Actinide", "f"),
    "U": ("Actinide", "f"), "Np": ("Actinide", "f"), "Pu": ("Actinide", "f"),
}


def _valence_from(group, block):
    """Valence-electron heuristic. s/p-block follow the standard group-number
    rule. d-block uses the group number itself as a simplified proxy for
    total (s+d) valence electrons. f-block defaults to 3 — the common +3
    oxidation state shared by most lanthanides/actinides — since exact
    valence counting for f-block elements is genuinely context-dependent."""
    if block == "s":
        return group if isinstance(group, int) else 2
    if block == "p":
        return (group - 10) if isinstance(group, int) else 4
    if block == "d":
        return group if isinstance(group, int) else 6
    return 3  # f-block


ELEMENT_INFO = {}
for _sym, (_chi, _rad, _col) in ELEMENTS.items():
    _group, _block = GROUP_BLOCK.get(_sym, (14, "p"))
    ELEMENT_INFO[_sym] = {
        "chi": _chi, "radius": _rad, "color": _col,
        "group": _group, "block": _block,
        "valence": _valence_from(_group, _block),
    }
_FALLBACK = {"chi": 2.0, "radius": 1.0, "color": "#757575",
             "group": 14, "block": "p", "valence": 4}
KNOWN_SYMBOLS = set(ELEMENT_INFO.keys())


@st.cache_data
def get_el_data(symbol):
    s = symbol[0].upper() + symbol[1:].lower() if len(symbol) > 1 else symbol.upper()
    return ELEMENT_INFO.get(s, _FALLBACK)


# ---------- Formula parsing (parentheses, hydrates, ambiguous casing) ----------
def _greedy_match_symbol(text, i):
    if i + 1 < len(text):
        two = text[i:i + 2]
        cand2 = two[0].upper() + two[1].lower()
        if cand2 in KNOWN_SYMBOLS:
            return cand2, i + 2
    return text[i].upper(), i + 1


def _strict_single_letter(text, i):
    return text[i].upper(), i + 1


def _mixed_case_match(text, i):
    m = re.match(r'[A-Za-z][a-z]?', text[i:])
    raw = m.group(0)
    sym = raw[0].upper() + raw[1:].lower()
    return sym, i + len(raw)


def _parse_segment(formula, matcher):
    stack = [{}]
    i, n = 0, len(formula)
    while i < n:
        c = formula[i]
        if c in "([":
            stack.append({})
            i += 1
        elif c in ")]":
            i += 1
            j = i
            while j < n and formula[j].isdigit():
                j += 1
            mult = int(formula[i:j]) if j > i else 1
            i = j
            if len(stack) > 1:
                top = stack.pop()
                for el, cnt in top.items():
                    stack[-1][el] = stack[-1].get(el, 0) + cnt * mult
        elif c.isalpha():
            sym, i = matcher(formula, i)
            j = i
            while j < n and formula[j].isdigit():
                j += 1
            cnt = int(formula[i:j]) if j > i else 1
            i = j
            stack[-1][sym] = stack[-1].get(sym, 0) + cnt
        else:
            i += 1
    while len(stack) > 1:
        top = stack.pop()
        for el, cnt in top.items():
            stack[-1][el] = stack[-1].get(el, 0) + cnt
    return stack[0]


def parse_formula(formula):
    """Supports nested parentheses/multipliers (Fe2(SO4)3), hydrate
    dot-notation (CuSO4.5H2O), and ambiguous casing ('NaCl'/'nacl'/'NACL'
    all resolve correctly; properly-cased input like 'CO' is always trusted
    as Carbon+Oxygen rather than guessed as Cobalt)."""
    formula = formula.strip()
    has_upper = any(c.isupper() for c in formula)
    has_lower = any(c.islower() for c in formula)
    mixed_case = has_upper and has_lower

    segments = re.split(r'[.\u00B7*]', formula)
    combined = {}
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        m = re.match(r'^\d+', seg)
        seg_mult = int(m.group(0)) if m else 1
        rest = seg[m.end():] if m else seg

        if mixed_case:
            seg_counts = _parse_segment(rest, _mixed_case_match)
        else:
            strict_counts = _parse_segment(rest, _strict_single_letter)
            if all(sym in KNOWN_SYMBOLS for sym in strict_counts):
                seg_counts = strict_counts
            else:
                seg_counts = _parse_segment(rest, _greedy_match_symbol)

        for el, cnt in seg_counts.items():
            combined[el] = combined.get(el, 0) + cnt * seg_mult

    parsed = {}
    for sym, count in combined.items():
        if not sym or count <= 0:
            continue
        d = get_el_data(sym)
        parsed[sym] = {
            "n": count, "chi": d["chi"], "rad": d["radius"], "col": d["color"],
            "group": d["group"], "block": d["block"], "valence": d["valence"],
        }
    return parsed


# ==========================================
# 2 & 3. PREDICTIVE BRIDGE LOGIC (van Arkel–Ketelaar + macro properties)
# ==========================================
CATEGORY_COLORS = {
    "Ionic": "#ff4b4b", "Metallic": "#58a6ff",
    "Covalent Network": "#3fb950", "Polar Covalent": "#f0883e",
}

# Elements conventionally regarded as metals (used to detect pure metals and
# alloys whose Pauling chi happens to be high — e.g. W=2.36, Pt=2.28, Au=2.54
# — which a raw "mean chi < threshold" rule would wrongly call non-metallic).
METAL_SYMBOLS = {
    "Li", "Na", "K", "Rb", "Cs", "Fr", "Be", "Mg", "Ca", "Sr", "Ba", "Ra",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Al", "Ga", "In", "Sn", "Tl", "Pb", "Bi", "Po",
    "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Ac", "Th", "Pa", "U", "Np", "Pu",
}


def van_arkel_analysis(mean_chi, delta_chi, symbols=None):
    """Places the compound on a (Mean χ, Δχ) van Arkel–Ketelaar triangle and
    derives continuous Metallic/Covalent/Ionic character percentages via
    inverse-distance weighting to three archetypal corners (purely
    descriptive — shown in the UI as a continuous breakdown).

    The discrete category label uses calibrated rules rather than a raw
    argmax of those percentages: raw electronegativity alone misclassifies
    high-chi metals (W=2.36, Pt=2.28, Au=2.54) as covalent, since chi
    doesn't cleanly separate "metal" from "nonmetal" in the d-block — so
    pure-metal/alloy detection instead checks actual periodic-table
    metal membership (METAL_SYMBOLS) for small Δχ before falling back to
    the standard ionic/covalent chi-based rules."""
    metallic_pt, covalent_pt, ionic_pt = (1.0, 0.0), (2.5, 0.0), (1.8, 3.3)
    pt = (mean_chi, delta_chi)

    def dist(a, b):
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 + 1e-6

    d_m, d_c, d_i = dist(pt, metallic_pt), dist(pt, covalent_pt), dist(pt, ionic_pt)
    inv = np.array([1 / d_m, 1 / d_c, 1 / d_i])
    pct = 100 * inv / inv.sum()
    metallic_pct, covalent_pct, ionic_pct = pct.tolist()

    ionic_character = 100 * (1 - np.exp(-0.25 * delta_chi ** 2))  # Pauling-style, continuous
    is_all_metal = bool(symbols) and all(s in METAL_SYMBOLS for s in symbols)

    if is_all_metal and delta_chi < 1.5:
        category = "Metallic"
    elif ionic_character > 50:
        category = "Ionic"
    elif delta_chi < 0.7:
        category = "Covalent Network"
    else:
        category = "Polar Covalent"

    return {
        "metallic_pct": metallic_pct, "covalent_pct": covalent_pct, "ionic_pct": ionic_pct,
        "ionic_character": ionic_character, "category": category, "point": pt,
        "corners": {"Metallic": metallic_pt, "Covalent": covalent_pt, "Ionic": ionic_pt},
    }


def estimate_band_gap(category, delta_chi):
    if category == "Metallic":
        return 0.0
    return max(0.0, (delta_chi * 2.1) - 0.4)


def estimate_mechanical(analysis, avg_rad):
    """Heuristic 0-100 engineering-trait scores. NOT a DFT/empirical
    mechanical model — swap for a real materials-informatics pipeline
    (e.g. trained on Materials Project elastic-tensor data) in production."""
    covalent_pct, ionic_pct, metallic_pct = (
        analysis["covalent_pct"], analysis["ionic_pct"], analysis["metallic_pct"]
    )
    size_factor = max(0.0, min(1.0, (2.2 - avg_rad) / 1.8))  # smaller atoms -> harder
    hardness = max(0.0, min(100.0, covalent_pct * 0.55 + size_factor * 100 * 0.45))
    ductility = max(0.0, min(100.0, metallic_pct))
    network_weight = 1.0 if analysis["category"] == "Covalent Network" else 0.3
    brittleness = max(0.0, min(100.0,
        ionic_pct * 0.6 + covalent_pct * 0.4 * network_weight - metallic_pct * 0.3))
    return {"Hardness": hardness, "Ductility": ductility, "Brittleness": brittleness}


def estimate_melting(category, is_molecule):
    if is_molecule:
        return "Low", "Discrete molecule — weak intermolecular forces dominate despite strong internal covalent bonds (e.g. ice, dry ice)."
    if category == "Covalent Network":
        return "Extremely High", "Continuous covalent lattice — every atom is part of one bonded network (e.g. diamond, SiC, TiO2)."
    if category == "Ionic":
        return "High", "Strong electrostatic lattice energy holds the ionic crystal together."
    if category == "Metallic":
        return "Moderate–High", "Delocalized 'electron sea' bonding; varies widely by specific metal."
    return "Moderate", "Polar covalent network — intermediate bond strength."


# ==========================================
# 4. APP CONFIGURATION & THEME
# ==========================================
st.set_page_config(page_title="AtomCraft v4.0", layout="wide")
st.markdown("""
<style>
/* Base app background + default text color */
html, body, .main, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #0d1117 !important;
    color: #e6edf3 !important;
}
[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }

/* Headings / body text everywhere */
h1, h2, h3, h4, h5, h6 { color: #f0f6fc !important; }
.main p, .main span, .main label, .main li { color: #c9d1d9; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #11161d !important;
    border-right: 1px solid #21262d;
}
section[data-testid="stSidebar"] * { color: #e6edf3 !important; }
section[data-testid="stSidebar"] input {
    background-color: #0d1117 !important;
    color: #f0f6fc !important;
    border: 1px solid #30363d !important;
}

/* Captions (was washing out to near-invisible grey) */
[data-testid="stCaptionContainer"], .main small { color: #9aa4b2 !important; }

/* Widget labels (Chemical Formula / Electron Cloud Density) */
[data-testid="stWidgetLabel"] p { color: #c9d1d9 !important; font-weight: 500; }

/* st.info box */
[data-testid="stAlert"] { background-color: #11243d !important; border: 1px solid #1f3a5c; }
[data-testid="stAlert"] * { color: #cfe3ff !important; }

/* Metric cards */
div[data-testid="stMetric"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 10px; padding: 12px;
}
[data-testid="stMetricLabel"] p { color: #8b949e !important; }
div[data-testid="stMetricValue"] {
    color: #f0f6fc !important;
    font-size: 1.25rem !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    line-height: 1.25 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] p { color: #8b949e !important; }
.stTabs [aria-selected="true"] p { color: #f0f6fc !important; }

/* Dataframe (Composition tab) */
[data-testid="stDataFrame"] { color: #e6edf3 !important; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v4.0")
    st.caption("Universal Nano-Material Property Designer")
    user_input = st.text_input("Chemical Formula", value="AuCl")
    iso_val = st.slider(
        "Electron Cloud Density", 0.01, 0.50, 0.12,
        help="Isosurface threshold for a synthetic electron-density cloud "
             "built from each atom's valence-electron count and radius "
             "(no real DFT data in heuristic mode). Higher = surface "
             "contracts toward dense atom cores. Lower = surface expands "
             "into a larger diffuse cloud."
    )
    st.info("Universal Prediction Mode — heuristic van Arkel–Ketelaar engine\n\n(element-accurate sphere sizing)")

# ==========================================
# 5. COMPUTATION
# ==========================================
comp = parse_formula(user_input)

if comp:
    v_list = list(comp.values())
    total_n = sum(v['n'] for v in v_list)
    all_chi = [v['chi'] for v in v_list]
    delta_chi = max(all_chi) - min(all_chi)
    avg_chi = sum(v['chi'] * v['n'] for v in v_list) / total_n
    avg_rad = sum(v['rad'] * v['n'] for v in v_list) / total_n

    analysis = van_arkel_analysis(avg_chi, delta_chi, symbols=list(comp.keys()))
    b_type = analysis["category"]
    b_col = CATEGORY_COLORS[b_type]

    counts = {sym: v['n'] for sym, v in comp.items()}
    total_atoms = sum(counts.values())
    hub_candidates = [s for s, n in counts.items() if n == 1]

    def hub_score(s):
        return (s == "H") + (s == "O") * 0.5
    hub_candidates_sorted = sorted(hub_candidates, key=hub_score)
    # BUG FIXED: a single-element formula (e.g. "Cu", "C") trivially has one
    # "hub candidate" with zero ligands, which used to render as one lonely
    # floating atom instead of falling through to the lattice branch.
    is_molecule = bool(hub_candidates_sorted) and total_atoms <= 12 and len(comp) >= 2

    bg = estimate_band_gap(b_type, delta_chi)
    mech = estimate_mechanical(analysis, avg_rad)
    # BUG FIXED: melting estimate no longer trusts the geometry-only
    # is_molecule flag whenever the bonding analysis says Ionic/Metallic/
    # Covalent Network — those are extended-structure categories by
    # definition (e.g. GaAs and MoS2 trivially satisfy the "hub + few
    # ligands" geometry pattern but are real covalent-network semiconductors,
    # not discrete weakly-bound molecules; they were wrongly coming back as
    # "Low" melting). The molecular/weak-intermolecular framing now only
    # applies to "Polar Covalent" — the one category that actually covers
    # discrete small molecules like H2O, CO2, NH3, CO in this model.
    melt_is_molecule = is_molecule and b_type == "Polar Covalent"
    melt_label, melt_desc = estimate_melting(b_type, melt_is_molecule)

    c1, c2 = st.columns([2, 1])

    # ======================= CENTER: 3D LATTICE =======================
    with c1:
        st.subheader(f"Molecular Lattice: {user_input}")

        atom_lines = []
        if is_molecule:
            hub = hub_candidates_sorted[0]
            expanded = [s for s, n in counts.items() for _ in range(n)]
            others = expanded.copy()
            others.remove(hub)
            bond_len = 1.1

            atom_lines.append(f"{hub} 0.00 0.00 0.00")
            n_others = len(others)
            if n_others == 1:
                atom_lines.append(f"{others[0]} {bond_len:.2f} 0.00 0.00")
            elif n_others == 2:
                half_angle = np.radians(104.5 / 2)
                dx, dy = bond_len * np.cos(half_angle), bond_len * np.sin(half_angle)
                atom_lines.append(f"{others[0]} {dx:.2f} {dy:.2f} 0.00")
                atom_lines.append(f"{others[1]} {dx:.2f} {-dy:.2f} 0.00")
            else:
                golden_angle = np.pi * (3 - np.sqrt(5))
                for i, sym2 in enumerate(others):
                    y = 1 - (i / float(n_others - 1)) * 2 if n_others > 1 else 0
                    r = np.sqrt(max(0.0, 1 - y * y))
                    theta = golden_angle * i
                    x, z = np.cos(theta) * r, np.sin(theta) * r
                    atom_lines.append(f"{sym2} {bond_len*x:.2f} {bond_len*y:.2f} {bond_len*z:.2f}")
        else:
            buckets = {sym: [sym] * n for sym, n in counts.items()}
            interleaved = []
            while any(buckets.values()):
                for sym in list(buckets.keys()):
                    if buckets[sym]:
                        interleaved.append(buckets[sym].pop(0))

            MAX_RENDER_ATOMS = 60
            render_n = min(total_atoms, MAX_RENDER_ATOMS)
            if total_atoms > MAX_RENDER_ATOMS:
                st.caption(f"⚠️ Rendering {render_n} of {total_atoms} atoms for performance/clarity.")
            interleaved = interleaved[:render_n]

            spacing = 2.5
            dim = max(2, int(np.ceil(render_n ** (1 / 3))))
            grid_positions = []
            for x in range(dim):
                for y in range(dim):
                    for z in range(dim):
                        grid_positions.append((x * spacing, y * spacing, z * spacing))
                        if len(grid_positions) >= render_n:
                            break
                    if len(grid_positions) >= render_n:
                        break
                if len(grid_positions) >= render_n:
                    break

            for sym, (x, y, z) in zip(interleaved, grid_positions):
                atom_lines.append(f"{sym} {x:.2f} {y:.2f} {z:.2f}")

        xyz = f"{len(atom_lines)}\nAtomCraft v4.0\n" + "\n".join(atom_lines)

        # BUG FIXED (sizing accuracy): the previous version used ONE fixed
        # sphere radius for every element, so e.g. Au and Cl rendered
        # identically sized despite real covalent radii of 1.44 vs 0.99 A.
        # Each element now gets its own scaled sphere radius (scale=0.45,
        # clamped to keep tiny/huge atoms visually sane in a ball-and-stick
        # view) so relative atomic size is genuinely informative.
        radius_map = {
            sym: round(max(0.28, min(0.85, v['rad'] * 0.45)), 3)
            for sym, v in comp.items()
        }
        radius_map_json = json.dumps(radius_map)

        # BUG FIXED (Electron Cloud Density was a no-op): checked the real
        # 3Dmol.js source — addSurface's 'scale' option is ONLY consumed
        # when real volumetric (voldata) data is supplied for CUBE/VASP
        # parsing; for a plain position-based VDW surface (our previous
        # approach) it is silently ignored entirely, so the slider was
        # computing a new value every rerun that nothing downstream ever
        # read. There's no real DFT density grid available in heuristic
        # Universal Mode, so we synthesize one: a sum-of-Gaussians electron
        # density built from each atom's actual valence-electron count and
        # covalent radius, then feed it through 3Dmol's real isosurface
        # threshold mechanism (addIsosurface + isoval) — confirmed from
        # source: voxels with density > isoval are "inside"; raising isoval
        # genuinely contracts the surface toward atom cores, lowering it
        # genuinely expands the surface, exactly matching the original spec.
        # PRODUCTION NOTE: swap this synthetic grid for a real DFT-computed
        # charge-density cube file in Live API Mode.
        atoms_for_density = [
            {"x": x, "y": y, "z": z,
             "w": float(comp[sym]['valence']),
             "sigma": max(0.45, comp[sym]['rad'] * 0.55)}
            for line in atom_lines
            for sym, x, y, z in [(lambda p: (p[0], float(p[1]), float(p[2]), float(p[3])))(line.split())]
        ]
        atoms_for_density_json = json.dumps(atoms_for_density)

        html_3d = f"""
        <div id="viewer3d" style="height: 500px; width: 100%; background-color: #0b0e14; border-radius: 10px;"></div>
        <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
        <script>
            (function() {{
                let element = document.getElementById('viewer3d');
                let viewer = $3Dmol.createViewer(element, {{ backgroundColor: '0x0b0e14' }});

                let xyzData = `{xyz}`;
                viewer.addModel(xyzData, "xyz");

                viewer.setStyle({{}}, {{ stick: {{ radius: 0.12, color: 'grey' }} }});

                let radiusMap = {radius_map_json};
                Object.keys(radiusMap).forEach(function(sym) {{
                    viewer.setStyle({{elem: sym}}, {{
                        sphere: {{ radius: radiusMap[sym], colorscheme: 'Jmol' }},
                        stick: {{ radius: 0.12, color: 'grey' }}
                    }});
                }});

                // ---- Synthesize a Gaussian-sum electron density grid ----
                let atoms = {atoms_for_density_json};
                let pad = 2.5;
                let xs = atoms.map(a => a.x), ys = atoms.map(a => a.y), zs = atoms.map(a => a.z);
                let minX = Math.min(...xs) - pad, maxX = Math.max(...xs) + pad;
                let minY = Math.min(...ys) - pad, maxY = Math.max(...ys) + pad;
                let minZ = Math.min(...zs) - pad, maxZ = Math.max(...zs) + pad;
                let N = 28;
                let dx = (maxX - minX) / (N - 1), dy = (maxY - minY) / (N - 1), dz = (maxZ - minZ) / (N - 1);
                let data = new Float32Array(N * N * N);
                let maxRho = 1e-6;
                for (let ix = 0; ix < N; ix++) {{
                    let x = minX + ix * dx;
                    for (let iy = 0; iy < N; iy++) {{
                        let y = minY + iy * dy;
                        for (let iz = 0; iz < N; iz++) {{
                            let z = minZ + iz * dz;
                            let rho = 0;
                            for (let k = 0; k < atoms.length; k++) {{
                                let a = atoms[k];
                                let ddx = x - a.x, ddy = y - a.y, ddz = z - a.z;
                                let d2 = ddx * ddx + ddy * ddy + ddz * ddz;
                                rho += a.w * Math.exp(-d2 / (2 * a.sigma * a.sigma));
                            }}
                            data[ix * N * N + iy * N + iz] = rho;
                            if (rho > maxRho) maxRho = rho;
                        }}
                    }}
                }}

                let voldata = Object.create($3Dmol.VolumeData.prototype);
                voldata.size = {{ x: N, y: N, z: N }};
                voldata.unit = {{ x: dx, y: dy, z: dz }};
                voldata.origin = {{ x: minX, y: minY, z: minZ }};
                voldata.data = data;
                voldata.matrix = null;

                // Map the slider (0.01-0.50) onto a FRACTION of this specific
                // structure's own peak density, rather than an absolute
                // threshold — guarantees the surface meaningfully contracts
                // (toward 85% of peak) and expands (down to 5% of peak) across
                // the full slider range regardless of which elements/how many
                // atoms are present, instead of depending on fixed constants
                // happening to land in the right absolute range every time.
                let frac = ({iso_val} - 0.01) / (0.50 - 0.01);
                let isoval = maxRho * (0.05 + frac * 0.80);

                viewer.addIsosurface(voldata, {{
                    isoval: isoval,
                    color: '{b_col}',
                    opacity: 0.45,
                    smoothness: 1
                }});

                viewer.zoomTo();
                viewer.render();

                window.addEventListener('resize', function() {{
                    viewer.resize();
                }});
            }})();
        </script>
        """
        st.iframe(html_3d, height=520)

    # ======================= RIGHT: TELEMETRY =======================
    with c2:
        st.subheader("Analysis")
        m1, m2 = st.columns(2)
        m1.metric("Mean χ", f"{avg_chi:.2f}")
        m2.metric("Δχ", f"{delta_chi:.2f}")
        m3, m4 = st.columns(2)
        m3.metric("Avg Radius", f"{avg_rad:.2f} Å")
        m4.metric("Bond Type", b_type)

        tab_bond, tab_band, tab_mech, tab_comp = st.tabs(
            ["Bonding", "Band Structure", "Mechanical", "Composition"]
        )

        with tab_bond:
            corners = analysis["corners"]
            xs = [corners["Metallic"][0], corners["Covalent"][0], corners["Ionic"][0], corners["Metallic"][0]]
            ys = [corners["Metallic"][1], corners["Covalent"][1], corners["Ionic"][1], corners["Metallic"][1]]
            fig_tri = go.Figure()
            fig_tri.add_trace(go.Scatter(x=xs, y=ys, mode="lines",
                                          line=dict(color="#444", width=1), showlegend=False))
            for label, (cx, cy) in corners.items():
                fig_tri.add_trace(go.Scatter(x=[cx], y=[cy], mode="markers+text", text=[label],
                                              textposition="bottom center", textfont=dict(color="#aab4c0"),
                                              marker=dict(size=6, color="#666"), showlegend=False))
            fig_tri.add_trace(go.Scatter(x=[avg_chi], y=[delta_chi], mode="markers",
                                          marker=dict(size=16, color=b_col, line=dict(width=2, color="white")),
                                          showlegend=False))
            fig_tri.update_layout(
                height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e6edf3"), margin=dict(t=20, b=20, l=20, r=20),
                xaxis=dict(title="Mean χ", range=[0.5, 3.2], gridcolor="#21262d", tickfont=dict(color="#e6edf3")),
                yaxis=dict(title="Δχ (ionic axis)", range=[-0.3, 3.6], gridcolor="#21262d", tickfont=dict(color="#e6edf3")),
            )
            st.plotly_chart(fig_tri, theme=None)
            st.caption(
                f"Metallic {analysis['metallic_pct']:.0f}% · Covalent {analysis['covalent_pct']:.0f}% · "
                f"Ionic {analysis['ionic_pct']:.0f}% (Pauling ionic character: {analysis['ionic_character']:.0f}%)"
            )
            st.markdown(f"**Estimated melting profile: {melt_label}**")
            st.caption(melt_desc)

        with tab_band:
            fig_band = go.Figure()
            if b_type == "Metallic" or bg <= 0.05:
                fig_band.add_shape(type="rect", x0=0, x1=1, y0=-2, y1=1,
                                    fillcolor=b_col, opacity=0.5, line=dict(width=0))
                fig_band.add_annotation(x=0.5, y=-0.5, text="Overlapping Bands<br>(Conductor)",
                                         showarrow=False, font=dict(color="white"))
                y_range = [-2.5, 2]
            else:
                fig_band.add_shape(type="rect", x0=0, x1=1, y0=-2, y1=0,
                                    fillcolor="#58a6ff", opacity=0.6, line=dict(width=0))
                fig_band.add_shape(type="rect", x0=0, x1=1, y0=bg, y1=bg + 2,
                                    fillcolor="#ff8000", opacity=0.6, line=dict(width=0))
                fig_band.add_annotation(x=0.5, y=-1, text="Valence Band", showarrow=False, font=dict(color="white"))
                fig_band.add_annotation(x=0.5, y=bg + 1, text="Conduction Band", showarrow=False, font=dict(color="white"))
                fig_band.add_annotation(x=1.25, y=bg / 2, text=f"Eg = {bg:.2f} eV",
                                         showarrow=False, font=dict(color=b_col, size=14))
                y_range = [-2.5, max(bg + 2.5, 3)]
            fig_band.update_layout(
                height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e6edf3"),
                xaxis=dict(visible=False, range=[-0.3, 1.7]),
                yaxis=dict(title="Energy (eV, relative)", range=y_range, gridcolor="#21262d",
                           color="#e6edf3", tickfont=dict(color="#e6edf3")),
                margin=dict(t=20, b=20, l=10, r=10), showlegend=False,
            )
            st.plotly_chart(fig_band, theme=None)
            gap_label = ("Conductor" if (b_type == "Metallic" or bg <= 0.05)
                         else "Semiconductor" if bg <= 3.0 else "Insulator")
            st.caption(f"Classification: **{gap_label}** (Eg ≈ {bg:.2f} eV)")

        with tab_mech:
            cats = list(mech.keys())
            vals = list(mech.values())
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=vals + [vals[0]], theta=cats + [cats[0]], fill="toself",
                line=dict(color=b_col), fillcolor=b_col, opacity=0.5,
            ))
            fig_radar.update_layout(
                polar=dict(bgcolor="rgba(0,0,0,0)",
                           radialaxis=dict(visible=True, range=[0, 100], color="#e6edf3",
                                            gridcolor="#21262d", tickfont=dict(color="#e6edf3")),
                           angularaxis=dict(color="#e6edf3", tickfont=dict(color="#e6edf3"))),
                showlegend=False, paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e6edf3"),
                height=320, margin=dict(t=30, b=30, l=30, r=30),
            )
            st.plotly_chart(fig_radar, theme=None)
            st.caption("Heuristic engineering-trait estimate — not a substitute for measured elastic-tensor data.")

        with tab_comp:
            rows = []
            for k, v in comp.items():
                rows.append({
                    "Sym": k, "n": v["n"], "χ": v["chi"], "Radius (Å)": v["rad"],
                    "Group": v["group"], "Block": v["block"], "Valence e⁻": v["valence"],
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True)
else:
    st.error("Invalid Formula")
