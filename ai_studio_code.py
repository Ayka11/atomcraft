import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import json
import math
import functools
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


def is_molecule_heuristic(comp):
    """Shared definition of 'looks like a discrete small molecule' used by
    both the 3D geometry builder and the reaction-thermodynamics phase
    guesser, so the two stay consistent with each other."""
    counts = {sym: v['n'] for sym, v in comp.items()}
    total_atoms = sum(counts.values())
    hub_candidates = [s for s, n in counts.items() if n == 1]
    return bool(hub_candidates) and total_atoms <= 12 and len(comp) >= 2


def compute_ionic_fraction(comp):
    """This compound's own ionic-character fraction (0-1), via the same van
    Arkel analysis used for bonding classification. Shared by every visual
    effect that should scale with 'how ionic is this specific species' —
    bond/lattice stretch, electron-cloud solvation blur — so a single
    consistent definition of 'ionic' drives all of them."""
    if len(comp) < 2:
        return 0.0
    v_list = list(comp.values())
    total_n = sum(v['n'] for v in v_list)
    all_chi = [v['chi'] for v in v_list]
    delta_chi = max(all_chi) - min(all_chi)
    avg_chi = sum(v['chi'] * v['n'] for v in v_list) / total_n
    return van_arkel_analysis(avg_chi, delta_chi, symbols=list(comp.keys()))["ionic_character"] / 100


# ==========================================
# 3.5 GEOMETRY + 3D RENDERING (shared by both modes)
# ==========================================
def build_geometry(comp, max_render_atoms=60, epsilon=1.0):
    """Returns (atom_lines, total_atoms, rendered_atom_count, is_molecule).
    Two heuristic templates: a hub-and-ligand layout for small discrete
    molecules (bent/trigonal/spherical-spread depending on ligand count),
    and an interleaved cubic lattice — SIZED TO THE REAL ATOM COUNT, not a
    fixed 8 corners — for extended ionic/network/metallic structures.

    BUG FIXED (epsilon had no visual effect): the Solvent Polarity slider
    only changed a numeric ΔG correction — nothing in the 3D scene
    responded to it at all. Bond lengths and lattice spacing are now
    scaled by a 'dissociation stretch' factor that grows with this
    compound's OWN ionic character (compute_ionic_fraction) and with how
    far epsilon is above 1 (vacuum/gas-phase, where the factor is exactly
    1.0 — i.e. no visual change at the default slider position, matching
    the existing ΔG correction's zero-at-vacuum behavior). This directly
    visualizes ionization/solvation: a polar medium genuinely pulls an
    ionic lattice's atoms apart (real dissociation into separated, solvated
    ions), while a covalent network or metal — which doesn't ionize the
    same way — stays essentially unchanged regardless of solvent polarity."""
    counts = {sym: v['n'] for sym, v in comp.items()}
    total_atoms = sum(counts.values())
    if total_atoms == 0:
        return [], 0, 0, False

    ionic_frac = compute_ionic_fraction(comp)
    stretch = 1.0 + ionic_frac * min(1.5, max(0.0, epsilon - 1.0) / 30.0)

    is_molecule = is_molecule_heuristic(comp)
    atom_lines = []

    # Special-case single-element species (a lone atom like 'Ti', or a
    # diatomic pair like 'O2'/'N2'/'H2'/'Cl2') with a realistic bond length
    # instead of falling through to the generic lattice spacing — this
    # matters most for the Reaction Dashboard, where reactant species are
    # rendered individually (see build_species_layout) and a believable O2
    # bond length is what makes the reactant side visually read as "an O2
    # molecule" rather than two unrelated floating spheres.
    if len(comp) == 1 and total_atoms <= 2:
        sym, v = next(iter(comp.items()))
        if total_atoms == 1:
            return [f"{sym} 0.00 0.00 0.00"], 1, 1, False
        bond_len = max(0.74, v['rad'] * 1.6)  # heuristic scaling vs. real diatomic bond lengths
        return ([f"{sym} {-bond_len/2:.2f} 0.00 0.00", f"{sym} {bond_len/2:.2f} 0.00 0.00"],
                2, 2, True)

    if is_molecule:
        hub_candidates = [s for s, n in counts.items() if n == 1]

        def hub_score(s):
            return (s == "H") + (s == "O") * 0.5
        hub = sorted(hub_candidates, key=hub_score)[0]
        expanded = [s for s, n in counts.items() for _ in range(n)]
        others = expanded.copy()
        others.remove(hub)
        bond_len = 1.1 * stretch

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
        rendered_n = len(atom_lines)
    else:
        buckets = {sym: [sym] * n for sym, n in counts.items()}
        interleaved = []
        while any(buckets.values()):
            for sym in list(buckets.keys()):
                if buckets[sym]:
                    interleaved.append(buckets[sym].pop(0))

        render_n = min(total_atoms, max_render_atoms)
        interleaved = interleaved[:render_n]

        spacing = 2.5 * stretch
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
        rendered_n = render_n

    return atom_lines, total_atoms, rendered_n, is_molecule


def build_radius_map(comp):
    """Per-element visual sphere radius scaled from real covalent radii —
    fixes the classic bug of every atom rendering the same size regardless
    of element (e.g. Au vs Cl looking identical)."""
    return {sym: round(max(0.28, min(0.85, v['rad'] * 0.45)), 3) for sym, v in comp.items()}


def build_density_atoms(atom_lines, comp, temp_k=298.0, epsilon=1.0):
    """Per-atom (position, valence weight, gaussian width) used to
    synthesize a fake electron-density grid for the isosurface — see
    render_3dmol_html for why this exists instead of a no-op 'scale'.

    Two physical effects scale the Gaussian width (sigma), i.e. how
    diffuse/blurry each atom's electron cloud looks:

    1. THERMAL MOTION (Debye-Waller-style): real atoms in a lattice or
    molecule vibrate, and the RMS vibrational amplitude scales with
    sqrt(T) in the classical (high-temperature) limit — this is exactly
    why X-ray/neutron crystallography atomic displacement parameters
    (B-factors) grow with temperature, blurring the time-averaged electron
    density. thermal_factor = 1.0 exactly at T=298K (the slider's default),
    floored at 0.5 rather than going to zero — even at very low T, real
    atoms still have nonzero zero-point vibrational motion.

    2. IONIC SOLVATION BLUR: in a polar medium, dissociated ions get
    surrounded by a diffuse solvation shell (solvent molecules orienting
    around the ion) — visualized here as the electron cloud for ionic-
    character atoms spreading out further as epsilon increases, on top of
    (and independent from) the bond/lattice stretch in build_geometry.
    Defaults to exactly 1.0 at epsilon=1 (vacuum)."""
    thermal_factor = max(0.5, 1.0 + 0.6 * (math.sqrt(max(temp_k, 50.0) / 298.0) - 1.0))
    ionic_frac = compute_ionic_fraction(comp)
    solvation_blur = 1.0 + ionic_frac * min(1.2, max(0.0, epsilon - 1.0) / 40.0)
    sigma_scale = thermal_factor * solvation_blur

    atoms = []
    for line in atom_lines:
        parts = line.split()
        sym, x, y, z = parts[0], float(parts[1]), float(parts[2]), float(parts[3])
        atoms.append({
            "x": x, "y": y, "z": z,
            "w": float(comp[sym]['valence']),
            "sigma": max(0.45, comp[sym]['rad'] * 0.55) * sigma_scale,
        })
    return atoms


def build_species_layout(species_list, spacing=3.0, per_species_cap=16, max_species_shown=6,
                          epsilon=1.0, temp_k=298.0, pressure_atm=1.0):
    """Lays out each species in a reactant/product list as its OWN distinct,
    spatially-separated cluster within one shared scene, instead of merging
    every species' atom counts into a single blob.

    BUG FIXED: combined_composition() merges all reactant species (and
    separately all product species) into one atom-count dictionary before
    rendering. For ANY balanced equation, total atom counts are identical
    on both sides by definition — that's what 'balanced' means — so a
    geometry built only from atom counts is mathematically guaranteed to
    produce the same shape for reactants and products. The actual
    difference between the two states is bonding TOPOLOGY (e.g. a separate
    Ti atom + separate O2 molecule vs. one bonded TiO2 structure), which
    combined_composition discarded entirely. This function renders each
    species with its own geometry (so O2 looks like a bonded pair, TiO2
    looks like a bonded triatomic, etc.) and places them side-by-side with
    visible gaps, so 'before' visibly reads as separate molecules and
    'after' visibly reads as a different, bonded structure.

    PRESSURE: at the everyday pressures this slider covers (1-500 atm),
    real compression of a solid/liquid's internal bond lengths is
    genuinely imperceptible — for a typical bulk modulus (~50-200 GPa),
    500 atm (~0.05 GPa) compresses a lattice by a few hundredths of a
    percent, far below what's worth faking visually. So pressure is NOT
    applied to intra-species bond/lattice spacing (build_geometry ignores
    it). What IS physically significant at these pressures is gas
    density/volume (PV = nRT) — so pressure instead compresses the GAP
    BETWEEN separate species clusters here, which is the most defensible
    place to show 'higher pressure packs molecules closer together'
    without overstating solid-state compressibility. compression=1.0
    exactly at P=1 atm (no change from prior behavior).

    Returns (atom_lines, total_atoms_real, rendered_atom_count,
    display_comp, truncated_species, density_atoms) where display_comp is
    a merged {symbol: element_data} dict (counts aside, just for radius
    lookups) and density_atoms is built PER-SPECIES (each species' own
    ionic character drives its own thermal/solvation blur, then positions
    are shifted by that species' offset) rather than on the flattened
    blob, for the same reason the geometry itself is built per-species.
    """
    shown = species_list[:max_species_shown]
    truncated_species = len(species_list) > max_species_shown

    compression = 1.0 / (1.0 + 0.3 * math.log10(max(pressure_atm, 1.0)))
    effective_spacing = spacing * compression

    atom_lines_all = []
    density_atoms_all = []
    display_comp = {}
    offset_x = 0.0
    total_atoms_real = 0

    for sp in shown:
        comp = sp["comp"]
        for sym, v in comp.items():
            display_comp.setdefault(sym, v)
        lines, total, rendered, _ = build_geometry(comp, max_render_atoms=per_species_cap, epsilon=epsilon)
        total_atoms_real += total

        local_density = build_density_atoms(lines, comp, temp_k=temp_k, epsilon=epsilon)

        xs = []
        for line in lines:
            parts = line.split()
            sym, x, y, z = parts[0], float(parts[1]), float(parts[2]), float(parts[3])
            xs.append(x)
            atom_lines_all.append(f"{sym} {x + offset_x:.2f} {y:.2f} {z:.2f}")
        for da in local_density:
            da["x"] += offset_x
            density_atoms_all.append(da)

        cluster_width = (max(xs) - min(xs)) if xs else 0.0
        offset_x += cluster_width + effective_spacing

    return atom_lines_all, total_atoms_real, len(atom_lines_all), display_comp, truncated_species, density_atoms_all



def render_3dmol_html(div_id, xyz, radius_map, atoms_for_density, b_col, iso_val, height=520):
    """Renders one independent 3Dmol viewer. Each call uses its OWN unique
    div id and its own explicit $3Dmol.createViewer(...) call (rather than
    the fragile 'viewer_3Dmoljs' auto-init class + indexing into
    $3Dmol.viewers[0]/[1] by registration order) — this is what makes
    placing two independent viewers side-by-side (Reaction Design
    Dashboard) safe: there's no shared global registry to race against.

    Electron Cloud Density: there's no real DFT density grid in heuristic
    mode, so we synthesize one (sum-of-Gaussians from each atom's actual
    valence-electron count + covalent radius) and feed it through 3Dmol's
    REAL isosurface threshold mechanism (addIsosurface + isoval, confirmed
    against the library source) rather than the no-op addSurface 'scale'
    parameter, which is silently ignored for non-volumetric surfaces.
    PRODUCTION NOTE: swap this synthetic grid for a real DFT-computed
    charge-density cube file in Live API Mode.
    """
    radius_map_json = json.dumps(radius_map)
    atoms_for_density_json = json.dumps(atoms_for_density)
    return f"""
    <div id="{div_id}" style="height: {height}px; width: 100%; background-color: #0b0e14; border-radius: 10px;"></div>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <script>
        (function() {{
            let element = document.getElementById('{div_id}');
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

            let atoms = {atoms_for_density_json};
            if (atoms.length > 0) {{
                let pad = 2.5;
                let xs = atoms.map(a => a.x), ys = atoms.map(a => a.y), zs = atoms.map(a => a.z);
                let minX = Math.min(...xs) - pad, maxX = Math.max(...xs) + pad;
                let minY = Math.min(...ys) - pad, maxY = Math.max(...ys) + pad;
                let minZ = Math.min(...zs) - pad, maxZ = Math.max(...zs) + pad;
                let N = 26;
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

                let frac = ({iso_val} - 0.01) / (0.50 - 0.01);
                let isoval = maxRho * (0.05 + frac * 0.80);

                viewer.addIsosurface(voldata, {{
                    isoval: isoval,
                    color: '{b_col}',
                    opacity: 0.45,
                    smoothness: 1
                }});
            }}

            viewer.zoomTo();
            viewer.render();

            window.addEventListener('resize', function() {{
                viewer.resize();
            }});
        }})();
    </script>
    """


# ==========================================
# 4. REACTION DESIGN ENGINE (Thermodynamics)
# ==========================================
# Reference standard enthalpies of formation (kJ/mol, approximate literature
# values, simplest-ratio formula unit). PRODUCTION NOTE: swap for a live
# NIST-JANAF / Materials Project formation-energy lookup for citation-grade
# numbers. Anything not in this table falls back to a transparent bonding-
# character heuristic (see estimate_formation_enthalpy).
RAW_HF_TABLE = {
    "H2O": -285.8, "CO2": -393.5, "NH3": -45.9, "CH4": -74.8,
    "NaCl": -411.2, "KCl": -436.5, "MgCl2": -641.3, "CaCl2": -795.8,
    "AgCl": -127.0, "HCl": -92.3, "HF": -273.3, "HBr": -36.3, "HI": 26.5,
    "TiO2": -944.0, "Al2O3": -1675.7, "Fe2O3": -824.2, "Fe3O4": -1118.4,
    "CaO": -635.1, "MgO": -601.6, "SiO2": -910.7, "CuO": -157.3,
    "Cu2O": -168.6, "ZnO": -350.5, "NiO": -239.7, "PbO": -217.3,
    "ZrO2": -1100.6, "Cr2O3": -1139.7, "MnO2": -520.0, "WO3": -842.9,
    "V2O5": -1550.6, "Ga2O3": -1089.1, "Li2O": -597.9, "Na2O": -414.2,
    "K2O": -363.2, "BaO": -548.1, "SrO": -590.8, "B2O3": -1273.5,
    "CaCO3": -1206.9, "SO2": -296.8, "SO3": -395.7, "NO": 90.3,
    "NO2": 33.2, "N2O": 82.0, "H2S": -20.6, "PCl3": -319.7, "P4O10": -2984.0,
    "CCl4": -135.4, "CS2": 89.0, "C2H2": 227.4, "C2H4": 52.4, "C2H6": -84.7,
    "C6H6": 49.0, "SiC": -65.3, "TiC": -184.5, "WC": -38.0, "GaAs": -78.0,
}


def _normalize_comp(comp):
    """Reduces a parsed composition to its simplest integer ratio and a
    canonical sorted key, so e.g. 'Fe4O6' and 'Fe2O3' both hit the same
    reference-table entry (then get rescaled back up by the same factor)."""
    counts = {sym: v['n'] for sym, v in comp.items()}
    g = functools.reduce(math.gcd, counts.values())
    g = g if g else 1
    reduced = {sym: n // g for sym, n in counts.items()}
    return tuple(sorted(reduced.items())), g


_NORMALIZED_HF = {}
for _f, _val in RAW_HF_TABLE.items():
    _c = parse_formula(_f)
    _key, _ = _normalize_comp(_c)
    _NORMALIZED_HF[_key] = _val


def estimate_formation_enthalpy(comp):
    """Returns (delta_Hf kJ/mol-per-formula-unit-as-written, source_label).

    BUG FIXED relative to the originally-pasted draft: that version assigned
    non-zero 'enthalpies' to pure elements (e.g. Cu: -157 kJ/mol — that's
    actually close to Cu2O's real value, suggesting a copy/paste mismatch
    between an element row and a compound's data). By definition, an
    element in its standard state has Hf == 0; that's not a heuristic
    shortcut, it IS the thermodynamic reference convention every other
    value is measured relative to."""
    if len(comp) == 1:
        return 0.0, "standard state (ΔHf ≡ 0 by definition)"

    key, g = _normalize_comp(comp)
    if key in _NORMALIZED_HF:
        return _NORMALIZED_HF[key] * g, "known reference value"

    # Heuristic fallback: more ionic/covalent bonding character and more
    # atoms per formula unit -> more exothermic formation, scaled by however
    # many "reduced formula units" the typed formula actually represents.
    all_chi = [v['chi'] for v in comp.values()]
    delta_chi = max(all_chi) - min(all_chi)
    total_n = sum(v['n'] for v in comp.values())
    avg_chi = sum(v['chi'] * v['n'] for v in comp.values()) / total_n
    analysis = van_arkel_analysis(avg_chi, delta_chi, symbols=list(comp.keys()))
    ionic_frac = analysis["ionic_character"] / 100
    covalent_frac = analysis["covalent_pct"] / 100

    counts = {sym: v['n'] for sym, v in comp.items()}
    reduced_atoms = sum(n // g for n in counts.values())
    per_bond = -(60 + 220 * ionic_frac + 90 * covalent_frac)
    hf = per_bond * max(0, reduced_atoms - 1) * g
    return max(-4000.0, min(50.0, hf)), "heuristic estimate (no reference data)"


def guess_phase(comp, is_molecule):
    """Simplified STP phase guess used only to pick a representative
    standard molar entropy. Real phase determination needs an actual
    phase diagram; this is a coarse heuristic, not a melting/boiling-point
    calculation."""
    syms = set(comp.keys())
    if len(syms) == 1:
        sym = next(iter(syms))
        return "gas" if sym in {"H", "N", "O", "F", "Cl"} else "solid"
    nonmetal_only = syms.issubset({"H", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"})
    return "gas" if (nonmetal_only and is_molecule) else "solid"


def estimate_standard_entropy(comp, is_molecule, explicit_phase=None):
    """Rough S° (J/mol·K) by phase, scaled gently by atom count (more atoms
    -> more vibrational/rotational modes -> more entropy). Calibrated
    loosely against real S° ranges: gases ~130-260, liquids ~50-120,
    aqueous species ~80-200 (solvent ordering lowers it vs. pure gas),
    solid elements ~25-35, solid compounds ~40-160.

    If explicit_phase is given (from a state symbol the user typed, e.g.
    'NaCl(s)'), it OVERRIDES the heuristic guess_phase() — trusting what
    the user explicitly stated is more reliable than guessing from
    composition alone."""
    phase = explicit_phase or guess_phase(comp, is_molecule)
    total_atoms = sum(v['n'] for v in comp.values())
    if phase == "gas":
        s = min(260.0, 130 + 12 * total_atoms)
    elif phase == "liquid":
        s = min(120.0, 50 + 7 * total_atoms)
    elif phase == "aqueous":
        s = min(200.0, 80 + 10 * total_atoms)
    else:
        s = 30.0 if len(comp) == 1 else min(160.0, 40 + 9 * total_atoms)
    return s, phase


R_KJ = 0.0083145  # kJ/(mol*K)


_STATE_SYMBOL_RE = re.compile(r'\(\s*(s|g|l|aq)\s*\)\s*$', re.IGNORECASE)
_PHASE_FROM_TAG = {"s": "solid", "g": "gas", "l": "liquid", "aq": "aqueous"}
_TRAILING_CHARGE_RE = re.compile(r'(\^?\d*[+\-])\s*$')


def parse_equation(eqn):
    """Splits 'aA + bB -> cC + dD' into coefficient/formula pairs on each
    side. Coefficient parsing is regex-anchored on leading digits only
    (unlike a naive '[A-Za-z0-9]*' formula match), so it stays correct for
    formulas containing parentheses/hydrates, e.g. '3Ca(OH)2 -> ...'.

    Supports: plain '->', '=', and equilibrium arrows ('⇌', '↔', '<=>',
    '<->') as synonyms — direction is always evaluated left-to-right as
    written. Also strips trailing state symbols (s)/(g)/(l)/(aq) and uses
    them as an authoritative phase override for the entropy/Δn_gas
    calculation (overriding the heuristic guess_phase), since an explicit
    user-provided phase is more reliable than a guess.

    NOT supported: explicit ionic charge notation (e.g. 'Na+', 'Cl-',
    'SO4^2-'). The '+' used for a charge is structurally indistinguishable
    from the '+' used to separate species in this grammar (e.g. 'Na+ + Cl-'
    — is that second '+' a charge or a separator?), so charged species are
    flagged with a warning rather than silently mis-parsed."""
    eqn = eqn.strip()
    # BUG FIXED: equilibrium-arrow variants must be normalized BEFORE the
    # bare '=' fallback runs, otherwise '<=>' gets corrupted (the naive
    # single '=' replace turned 'N2 + 3H2 <=> 2NH3' into the nonsense
    # 'N2 + 3H2 <-> 2NH3' split as '<' / '> 2NH3', silently producing wrong
    # species rather than failing loudly).
    for arrow in ("\u21cc", "\u2194", "<=>", "<->", "\u2192"):
        eqn = eqn.replace(arrow, "->")
    if "->" not in eqn and "=" in eqn:
        eqn = eqn.replace("=", "->", 1)
    if "->" not in eqn:
        return None, None, "Equation must contain '->' (or '=', '⇌', '<=>') separating reactants and products."
    parts = eqn.split("->")
    if len(parts) != 2:
        return None, None, "Equation must contain exactly one reactants/products separator."

    charge_warning = [False]

    def process_side(raw):
        species = []
        for item in raw.split("+"):
            item = item.strip()
            if not item:
                continue

            state_match = _STATE_SYMBOL_RE.search(item)
            explicit_phase = None
            if state_match:
                explicit_phase = _PHASE_FROM_TAG[state_match.group(1).lower()]
                item = item[:state_match.start()].strip()
            if not item:
                continue

            if _TRAILING_CHARGE_RE.search(item):
                charge_warning[0] = True

            m = re.match(r'^(\d*)\s*(.*)$', item)
            coeff = int(m.group(1)) if m.group(1) else 1
            formula_str = m.group(2).strip()
            if not formula_str:
                continue
            comp = parse_formula(formula_str)
            if not comp:
                continue
            species.append({
                "coeff": coeff, "formula": formula_str, "comp": comp,
                "explicit_phase": explicit_phase,
            })
        return species

    reactants = process_side(parts[0])
    products = process_side(parts[1])
    if not reactants or not products:
        return None, None, "Could not parse one or both sides of the equation."
    if charge_warning[0]:
        return reactants, products, (
            "⚠️ Ionic charge notation (e.g. 'Na+', 'Cl-') is not supported — the "
            "'+'/'-' characters collide with this parser's species-separator and "
            "coefficient grammar, so charges may be parsed incorrectly. Results "
            "below may be unreliable; consider writing neutral formula units instead."
        )
    return reactants, products, None


def check_atom_balance(reactants, products):
    from collections import Counter
    rc, pc = Counter(), Counter()
    for r in reactants:
        for sym, v in r["comp"].items():
            rc[sym] += v["n"] * r["coeff"]
    for p in products:
        for sym, v in p["comp"].items():
            pc[sym] += v["n"] * p["coeff"]
    return rc, pc, (rc == pc)


def compute_reaction_thermo(reactants, products, temp_k, pressure_atm):
    """Hess's-law ΔH, phase-weighted ΔS, and ΔG = ΔH - TΔS + a pressure
    correction term that only kicks in when the reaction's gas-phase mole
    count actually changes: ΔG_pressure = Δn_gas · R · T · ln(P). This is
    the real ideal-gas free-energy dependence on pressure (mu(P) = mu° +
    RT ln(P/P°)) summed over the net change in gas moles — e.g. for the
    Haber process (N2 + 3H2 -> 2NH3, Δn_gas = -2), this correctly predicts
    that HIGHER pressure favors ammonia formation (lowers ΔG), matching the
    real-world reason industrial ammonia synthesis runs at high pressure.

    BUG FIXED relative to the originally-pasted draft: that version created
    a 'pressure' slider that was never referenced anywhere in the ΔG
    calculation — a dead control, identical in spirit to the earlier
    Electron Cloud Density slider bug. It's also fixed for ΔS, which used a
    single hardcoded constant (-0.15 kJ/mol·K) for every reaction regardless
    of what was actually typed; ΔS here is now derived per-species from a
    phase-aware entropy estimate, so it actually changes per reaction."""
    h_react = h_prod = 0.0
    s_react = s_prod = 0.0
    gas_mol_react = gas_mol_prod = 0.0

    for r in reactants:
        hf, src = estimate_formation_enthalpy(r["comp"])
        s, phase = estimate_standard_entropy(r["comp"], is_molecule_heuristic(r["comp"]),
                                              explicit_phase=r.get("explicit_phase"))
        r["hf"], r["hf_source"], r["s"], r["phase"] = hf, src, s, phase
        h_react += r["coeff"] * hf
        s_react += r["coeff"] * s
        if phase == "gas":
            gas_mol_react += r["coeff"]

    for p in products:
        hf, src = estimate_formation_enthalpy(p["comp"])
        s, phase = estimate_standard_entropy(p["comp"], is_molecule_heuristic(p["comp"]),
                                              explicit_phase=p.get("explicit_phase"))
        p["hf"], p["hf_source"], p["s"], p["phase"] = hf, src, s, phase
        h_prod += p["coeff"] * hf
        s_prod += p["coeff"] * s
        if phase == "gas":
            gas_mol_prod += p["coeff"]

    delta_h = h_prod - h_react
    delta_s_j = s_prod - s_react          # J/mol*K
    delta_s_kj = delta_s_j / 1000.0       # kJ/mol*K
    delta_n_gas = gas_mol_prod - gas_mol_react
    pressure_term = delta_n_gas * R_KJ * temp_k * math.log(max(pressure_atm, 1e-6))
    delta_g = delta_h - temp_k * delta_s_kj + pressure_term

    return {
        "delta_h": delta_h, "delta_s_j": delta_s_j, "delta_g": delta_g,
        "delta_n_gas": delta_n_gas, "pressure_term": pressure_term,
        "spontaneous": delta_g < 0,
    }


def estimate_ionic_charge_proxy(comp):
    """Heuristic effective charge magnitude used only for the Born
    solvation estimate below — NOT a real oxidation-state calculation.
    Scales with how ionic the bonding character is and the average
    valence-electron count, clamped to a believable +1..+3 range."""
    v_list = list(comp.values())
    total_n = sum(v["n"] for v in v_list)
    all_chi = [v["chi"] for v in v_list]
    delta_chi = max(all_chi) - min(all_chi) if len(all_chi) > 1 else 0.0
    avg_chi = sum(v["chi"] * v["n"] for v in v_list) / total_n
    avg_valence = sum(v["valence"] * v["n"] for v in v_list) / total_n
    avg_rad = sum(v["rad"] * v["n"] for v in v_list) / total_n
    analysis = van_arkel_analysis(avg_chi, delta_chi, symbols=list(comp.keys()))
    ionic_frac = analysis["ionic_character"] / 100
    z = max(0.3, min(3.0, ionic_frac * (avg_valence / 2.0)))
    return z, avg_rad


def estimate_solvation_energy(comp, epsilon):
    """Born solvation free energy (kJ/mol): ΔG_solv = -694 * z²/r * (1 - 1/ε),
    using the standard Born-model constant (≈694 kJ·mol⁻¹·Å for z in
    elementary charge, r in Angstrom). A real, named electrostatic effect:
    a polar medium (high dielectric constant ε, e.g. water ≈ 80)
    stabilizes charge-separated species far more than a nonpolar one
    (e.g. vacuum/gas-phase, ε = 1, where the term is exactly zero) — this
    is the physical basis for why ionic compounds dissociate/ionize so much
    more readily in water than in an organic solvent. 'z' here is a
    heuristic charge proxy (see estimate_ionic_charge_proxy), not a real
    oxidation-state calculation."""
    z, r = estimate_ionic_charge_proxy(comp)
    r = max(r, 0.3)
    return -694.0 * (z ** 2) / r * (1 - 1 / epsilon)


def estimate_side_solvation_energy(species_list, epsilon):
    """Sums solvation energy across each individual species on one side of
    a reaction (weighted by its coefficient), rather than computing it on
    combined_composition()'s merged atom-count blob.

    BUG FIXED: calling estimate_solvation_energy directly on a merged blob
    is wrong for the same root reason build_species_layout was needed for
    visualization — merging discards which atoms were actually bonded
    together. For 'Na + Cl2', combined_composition() merges Na and Cl into
    one dict, and van Arkel analysis on THAT merged dict sees a large
    electronegativity difference (3.16 - 0.93) and reports high ionic
    character — even though elemental sodium metal and chlorine gas, sitting
    side by side, are not actually an ionic compound. Computed per-species
    instead, Na alone and Cl2 alone each correctly show ~0 ionic character
    (single-element Δχ = 0), while an actual ionic compound like NaCl
    appearing as a species on either side still correctly shows strong
    solvation stabilization in a polar medium."""
    return sum(sp["coeff"] * estimate_solvation_energy(sp["comp"], epsilon) for sp in species_list)



def combined_composition(species_list):
    """Sums atom counts across every species on one side of an equation
    (weighted by stoichiometric coefficient) into one composition dict, for
    a single combined before/after 3D snapshot of that side of the
    reaction."""
    counts = {}
    for sp in species_list:
        for sym, v in sp["comp"].items():
            counts[sym] = counts.get(sym, 0) + v["n"] * sp["coeff"]
    combined = {}
    for sym, n in counts.items():
        d = get_el_data(sym)
        combined[sym] = {
            "n": n, "chi": d["chi"], "rad": d["radius"], "col": d["color"],
            "group": d["group"], "block": d["block"], "valence": d["valence"],
        }
    return combined


def bonding_color_for(comp):
    v_list = list(comp.values())
    total_n = sum(v["n"] for v in v_list)
    all_chi = [v["chi"] for v in v_list]
    delta_chi = max(all_chi) - min(all_chi)
    avg_chi = sum(v["chi"] * v["n"] for v in v_list) / total_n
    analysis = van_arkel_analysis(avg_chi, delta_chi, symbols=list(comp.keys()))
    return CATEGORY_COLORS[analysis["category"]], analysis


# ==========================================
# 5. APP CONFIGURATION & THEME
# ==========================================
st.set_page_config(page_title="AtomCraft v4.1", layout="wide")
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

/* Captions */
[data-testid="stCaptionContainer"], .main small { color: #9aa4b2 !important; }

/* Widget labels */
[data-testid="stWidgetLabel"] p { color: #c9d1d9 !important; font-weight: 500; }

/* st.info / st.warning / st.error / st.success boxes */
[data-testid="stAlert"] * { color: #e6edf3 !important; }

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

/* Dataframe */
[data-testid="stDataFrame"] { color: #e6edf3 !important; }

/* Radio (mode toggle) styled closer to a segmented control */
div[role="radiogroup"] { gap: 4px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v4.1")
    st.caption("Universal Nano-Material Property Designer")
    mode = st.radio(
        "Mode",
        ["Material Property Inspector", "Reaction Design Dashboard"],
        help="Inspector analyzes one formula's bonding/structure. Dashboard "
             "analyzes a full reaction's thermodynamics and synthesis path."
    )
    st.markdown("---")

    if mode == "Material Property Inspector":
        user_input = st.text_input("Chemical Formula", value="AuCl")
    else:
        eqn_input = st.text_input(
            "Chemical Equation", value="Ti + O2 -> TiO2",
            help="Use '+' between species and '->' to separate reactants "
                 "from products, e.g. '2H2 + O2 -> 2H2O'. Coefficients are "
                 "used as typed — equations are not auto-balanced."
        )

    iso_val = st.slider(
        "Electron Cloud Density", 0.01, 0.50, 0.12,
        help="Isosurface threshold for a synthetic electron-density cloud "
             "built from each atom's valence-electron count and radius "
             "(no real DFT data in heuristic mode). Higher = surface "
             "contracts toward dense atom cores. Lower = surface expands "
             "into a larger diffuse cloud."
    )

    if mode == "Material Property Inspector":
        st.info("Universal Prediction Mode — heuristic van Arkel–Ketelaar engine\n\n(element-accurate sphere sizing)")
    else:
        st.info("Reaction Design Dashboard — heuristic ΔH/ΔS/ΔG engine\n\n(known-compound lookup + bonding-based fallback)")

# ==========================================
# 6A. MATERIAL PROPERTY INSPECTOR
# ==========================================
if mode == "Material Property Inspector":
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

        bg = estimate_band_gap(b_type, delta_chi)
        mech = estimate_mechanical(analysis, avg_rad)
        is_molecule = is_molecule_heuristic(comp)
        melt_is_molecule = is_molecule and b_type == "Polar Covalent"
        melt_label, melt_desc = estimate_melting(b_type, melt_is_molecule)

        c1, c2 = st.columns([2, 1])

        with c1:
            st.subheader(f"Molecular Lattice: {user_input}")
            atom_lines, total_atoms, rendered_n, _ = build_geometry(comp)
            if rendered_n < total_atoms:
                st.caption(f"⚠️ Rendering {rendered_n} of {total_atoms} atoms for performance/clarity.")
            xyz = f"{len(atom_lines)}\nAtomCraft v4.1\n" + "\n".join(atom_lines)
            radius_map = build_radius_map(comp)
            density_atoms = build_density_atoms(atom_lines, comp)
            html_3d = render_3dmol_html("viewerMain", xyz, radius_map, density_atoms, b_col, iso_val, height=520)
            st.iframe(html_3d, height=520)

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

# ==========================================
# 6B. REACTION DESIGN DASHBOARD
# ==========================================
else:
    reactants, products, err = parse_equation(eqn_input)

    if reactants is None:
        st.error(f"{err} Use the format: '2H2 + O2 -> 2H2O'")
    else:
        if err:
            st.warning(err)
        rc, pc, balanced = check_atom_balance(reactants, products)
        if not balanced:
            st.warning(
                f"⚠️ Equation may not be atom-balanced — Reactant atoms: {dict(rc)} "
                f"vs Product atoms: {dict(pc)}. Calculations below still use the "
                f"coefficients exactly as typed."
            )

        # Computed once up front since both Controls (ΔG/solvation) and
        # Visualization (bonding-color tint) need the per-side composition.
        reactant_comp = combined_composition(reactants)
        product_comp = combined_composition(products)

        c_ctrl, c_viz, c_therm = st.columns([1, 1.6, 1.2])

        with c_ctrl:
            st.subheader("Reaction Controls")
            temp = st.slider("Temperature (K)", 100, 3000, 298,
                              help="Used in ΔG = ΔH - TΔS. Also visually blurs the "
                                   "electron-cloud isosurface in the 3D viewports — "
                                   "real atomic vibration amplitude grows with √T "
                                   "(the same effect behind crystallography's "
                                   "temperature-dependent B-factors). No change at "
                                   "298K (the default).")
            pressure = st.slider(
                "Pressure (atm)", 1, 500, 1,
                help="Changes ΔG when the reaction's gas-phase mole count differs "
                     "between products and reactants (Δn_gas ≠ 0), via "
                     "ΔG_pressure = Δn_gas · R · T · ln(P). Also visually compresses "
                     "the spacing BETWEEN separate species in the 3D viewports "
                     "(real gas compression, PV=nRT) — bond lengths within a single "
                     "species aren't compressed, since that effect is genuinely "
                     "imperceptible below GPa-scale pressures. No change at 1 atm."
            )

            st.markdown("**Reaction Environment**")
            epsilon = st.slider(
                "Solvent Polarity — Dielectric Constant (ε)", 1.0, 80.0, 1.0, step=1.0,
                help="Models ionization/dissociation via the Born solvation "
                     "equation: a polar medium stabilizes the more "
                     "ionic/charge-separated side of the reaction more than "
                     "the other, shifting ΔG accordingly. Reference points: "
                     "vacuum/gas-phase ε=1 (no effect, this is the default), "
                     "hexane ε≈2, ethanol ε≈24, water ε≈80."
            )
            catalyst = st.checkbox(
                "Catalyst Present", value=False,
                help="A catalyst lowers the activation-energy barrier "
                     "(reaction coordinate hump) WITHOUT changing ΔH, ΔS, "
                     "or ΔG — catalysts affect kinetics, not thermodynamics. "
                     "This only changes the Energy Profile chart, not the "
                     "ΔG/spontaneity verdict below."
            )

            thermo = compute_reaction_thermo(reactants, products, temp, pressure)
            solv_react = estimate_side_solvation_energy(reactants, epsilon)
            solv_prod = estimate_side_solvation_energy(products, epsilon)
            solv_correction = solv_prod - solv_react
            delta_g_total = thermo["delta_g"] + solv_correction
            spontaneous_total = delta_g_total < 0

            st.metric("ΔH (reaction)", f"{thermo['delta_h']:.1f} kJ/mol")
            st.metric("ΔS (reaction)", f"{thermo['delta_s_j']:.1f} J/mol·K")
            st.metric(f"ΔG @ {temp} K, {pressure} atm, ε={epsilon:.0f}", f"{delta_g_total:.1f} kJ/mol")
            if abs(solv_correction) > 0.5:
                st.caption(
                    f"ΔG breakdown: {thermo['delta_g']:.1f} (gas-phase) "
                    f"{'+' if solv_correction >= 0 else '−'} {abs(solv_correction):.1f} "
                    f"(solvation/ionization) = {delta_g_total:.1f} kJ/mol"
                )

            if spontaneous_total:
                st.success("✅ Spontaneous (ΔG < 0) at these conditions")
            else:
                st.error("❌ Non-spontaneous (ΔG > 0) at these conditions")

            reaction_type = "Exothermic (Heat Releasing)" if thermo["delta_h"] < 0 else "Endothermic (Requires Energy Input)"
            st.markdown(f"**{reaction_type}**")

            if abs(thermo["delta_n_gas"]) > 1e-9:
                direction = "raises" if thermo["pressure_term"] > 0 else "lowers"
                st.caption(
                    f"Δn(gas) = {thermo['delta_n_gas']:+.1f} mol → pressure {direction} "
                    f"ΔG by {abs(thermo['pressure_term']):.1f} kJ/mol at {pressure} atm."
                )
            else:
                st.caption("No net change in gas-phase moles — pressure has negligible effect on this reaction's ΔG.")

            with st.expander("Per-species thermodynamic data"):
                rows = []
                for r in reactants:
                    rows.append({"Role": "Reactant", "Species": f"{r['coeff']}{r['formula']}",
                                 "ΔHf (kJ/mol)": round(r["hf"], 1), "S° (J/mol·K)": round(r["s"], 1),
                                 "Phase (guess)": r["phase"], "Source": r["hf_source"]})
                for p in products:
                    rows.append({"Role": "Product", "Species": f"{p['coeff']}{p['formula']}",
                                 "ΔHf (kJ/mol)": round(p["hf"], 1), "S° (J/mol·K)": round(p["s"], 1),
                                 "Phase (guess)": p["phase"], "Source": p["hf_source"]})
                st.dataframe(pd.DataFrame(rows), hide_index=True)
                st.caption("ΔHf/S° are reference-table values where available, otherwise a transparent "
                           "bonding-character/phase heuristic — not DFT-grade thermochemistry. Solvation "
                           "uses a heuristic charge proxy, not real oxidation-state analysis.")

        with c_viz:
            st.subheader("Synthesis Pipeline")
            v1, v2 = st.columns(2)

            # BUG FIXED: previously both viewports rendered
            # combined_composition(...) — merging every species on a side
            # into one atom-count blob. For a balanced equation, reactant
            # and product atom counts are IDENTICAL by definition, so the
            # two viewports were mathematically guaranteed to look the
            # same. Each species is now laid out as its own separated
            # cluster (see build_species_layout), so 'Ti + O2' visibly
            # reads as two distinct unbonded species, while 'TiO2' visibly
            # reads as one bonded structure.
            r_col, r_analysis = bonding_color_for(reactant_comp)
            p_col, p_analysis = bonding_color_for(product_comp)

            with v1:
                st.caption("Reactant State — " + ", ".join(f"{r['coeff']}{r['formula']}" for r in reactants))
                (r_atom_lines, r_total, r_rendered, r_display_comp, r_trunc,
                 r_density_atoms) = build_species_layout(reactants, epsilon=epsilon, temp_k=temp, pressure_atm=pressure)
                if r_rendered < r_total:
                    st.caption(f"⚠️ Rendering {r_rendered} of {r_total} atoms.")
                if r_trunc:
                    st.caption("⚠️ Showing first 6 species only.")
                r_xyz = f"{len(r_atom_lines)}\nReactants\n" + "\n".join(r_atom_lines)
                r_radius_map = build_radius_map(r_display_comp)
                r_html = render_3dmol_html("viewerReact", r_xyz, r_radius_map, r_density_atoms, r_col, iso_val, height=320)
                st.iframe(r_html, height=320)

            with v2:
                st.caption("Product State — " + ", ".join(f"{p['coeff']}{p['formula']}" for p in products))
                (p_atom_lines, p_total, p_rendered, p_display_comp, p_trunc,
                 p_density_atoms) = build_species_layout(products, epsilon=epsilon, temp_k=temp, pressure_atm=pressure)
                if p_rendered < p_total:
                    st.caption(f"⚠️ Rendering {p_rendered} of {p_total} atoms.")
                if p_trunc:
                    st.caption("⚠️ Showing first 6 species only.")
                p_xyz = f"{len(p_atom_lines)}\nProducts\n" + "\n".join(p_atom_lines)
                p_radius_map = build_radius_map(p_display_comp)
                p_html = render_3dmol_html("viewerProd", p_xyz, p_radius_map, p_density_atoms, p_col, iso_val, height=320)
                st.iframe(p_html, height=320)

        with c_therm:
            st.subheader("Energy Profile")
            delta_h = thermo["delta_h"]
            # TS hump height is a qualitative heuristic (scales with |ΔH|,
            # never the actual computed activation barrier), but is now
            # GUARANTEED to sit above both endpoints regardless of how large
            # or positive delta_h is, fixing a case the original draft's
            # simpler 'act_energy = abs(delta_h)*0.3+100' formula could miss
            # for strongly endothermic reactions (TS could end up BELOW the
            # product energy, breaking the visual "hump"). A present
            # catalyst lowers this barrier (kinetics only) without touching
            # delta_h/delta_g, matching real catalyst behavior.
            act_energy_height = max(40.0, abs(delta_h) * 0.25)
            if catalyst:
                act_energy_height *= 0.35
            ts_y = max(0.0, delta_h) + act_energy_height
            x_vals = [0, 1, 2]
            y_vals = [0, ts_y, delta_h]
            curve_color = "#3fb950" if spontaneous_total else "#ff4b4b"

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_vals, y=y_vals, mode="lines+markers", line_shape="spline",
                line=dict(color=curve_color, width=4), marker=dict(size=8, color=curve_color),
            ))
            fig.update_layout(
                title=f"Reaction Coordinate — {reaction_type.split(' (')[0]}"
                      + (" (catalyzed)" if catalyst else ""),
                xaxis=dict(title="Reaction Progress", showticklabels=False, gridcolor="#21262d"),
                # BUG FIXED: axis was labeled "Free Energy" but the curve is
                # built from delta_h (an enthalpy diagram is also the
                # conventional choice for textbook reaction-coordinate
                # plots); ΔG/spontaneity is reported as a single number in
                # Reaction Controls instead, since it depends on T/P/solvent
                # in ways not meaningful to plot along a reaction-progress axis.
                yaxis=dict(title="Enthalpy (kJ/mol, relative to reactants)", gridcolor="#21262d",
                           tickfont=dict(color="#e6edf3")),
                height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e6edf3"),
                annotations=[
                    dict(x=0, y=0, text="Reactants", showarrow=True, arrowhead=1, font=dict(color="#e6edf3")),
                    dict(x=1, y=ts_y, text="Transition State", showarrow=True, font=dict(color="#e6edf3")),
                    dict(x=2, y=delta_h, text="Products", showarrow=True, font=dict(color="#e6edf3")),
                ],
            )
            st.plotly_chart(fig, theme=None)
            st.caption(
                "Activation-energy hump height is a qualitative heuristic "
                "(scales with |ΔH|, reduced ~65% when a catalyst is present), "
                "not a computed transition-state barrier — swap for a real "
                "NEB/DFT barrier calculation in production. Curve color "
                "reflects overall ΔG-based spontaneity (including solvation)."
            )

st.caption("AtomCraft v4.1 | Universal Nano-Material Property Designer & Reaction Thermodynamics Unit")
