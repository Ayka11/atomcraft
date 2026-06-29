import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import streamlit.components.v1 as components

# ==========================================
# 1. SCIENTIFIC DATA (Zero-Dependency)
# ==========================================
# [Pauling electronegativity (chi), covalent radius (Angstrom), Jmol/CPK color]
# Coverage: H -> Pu. Anything beyond this (or a typo) falls back to a
# neutral heuristic placeholder in get_el_data() instead of crashing —
# this IS the documented "first-principles fallback" from the original spec.
# PRODUCTION NOTE: swap this static table for a live pymatgen/mendeleev
# lookup if exact, citation-grade constants are ever required.
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
KNOWN_SYMBOLS = set(ELEMENTS.keys())


@st.cache_data
def get_el_data(symbol):
    s = symbol[0].upper() + symbol[1:].lower() if len(symbol) > 1 else symbol.upper()
    return ELEMENTS.get(s, [2.0, 1.0, "#757575"])  # generic fallback, never crashes


def _greedy_match_symbol(text, i):
    """Case-insensitive longest-match lookup against KNOWN_SYMBOLS — used
    only as a fallback recovery step (see parse_formula) for sloppily-cased
    input like 'NACL' or 'tio2' where letter boundaries are otherwise lost."""
    if i + 1 < len(text):
        two = text[i:i + 2]
        cand2 = two[0].upper() + two[1].lower()
        if cand2 in KNOWN_SYMBOLS:
            return cand2, i + 2
    return text[i].upper(), i + 1


def _strict_single_letter(text, i):
    """Treat every alpha character as its own one-letter symbol candidate."""
    return text[i].upper(), i + 1


def _mixed_case_match(text, i):
    """Standard IUPAC-style matching: an uppercase letter optionally
    followed by ONE lowercase letter (only valid when input already has
    correct, unambiguous casing)."""
    m = re.match(r'[A-Za-z][a-z]?', text[i:])
    raw = m.group(0)
    sym = raw[0].upper() + raw[1:].lower()
    return sym, i + len(raw)


def _parse_segment(formula, matcher):
    """Stack-based parser: handles nested (parentheses)/[brackets] with
    trailing multipliers (e.g. Fe2(SO4)3) using the given symbol matcher."""
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
            # a stray ')' with no matching '(' is ignored gracefully
        elif c.isalpha():
            sym, i = matcher(formula, i)
            j = i
            while j < n and formula[j].isdigit():
                j += 1
            cnt = int(formula[i:j]) if j > i else 1
            i = j
            stack[-1][sym] = stack[-1].get(sym, 0) + cnt
        else:
            i += 1  # skip spaces, charges, stray punctuation
    while len(stack) > 1:  # gracefully merge any unbalanced groups
        top = stack.pop()
        for el, cnt in top.items():
            stack[-1][el] = stack[-1].get(el, 0) + cnt
    return stack[0]


def parse_formula(formula):
    """Robust formula parser:
    - Supports nested parentheses/multipliers: Ca(OH)2, Fe2(SO4)3
    - Supports hydrate dot-notation: CuSO4.5H2O, CuSO4*5H2O, CuSO4(middle-dot)5H2O
    - Tolerant of ambiguous casing: 'NaCl' / 'nacl' / 'NACL' all resolve to
      Na+Cl. Properly-cased input (mixed upper/lower) is always trusted as-is
      (e.g. 'CO' stays Carbon+Oxygen, never guessed as Cobalt) since real
      casing is the only thing that can correctly disambiguate chemistry
      notation — when it's missing, this is a best-effort recovery, not a
      certainty, and there is no way to fully resolve cases like ambiguous
      'CO' vs 'Co' typed without any case information at all.
    """
    formula = formula.strip()
    has_upper = any(c.isupper() for c in formula)
    has_lower = any(c.islower() for c in formula)
    mixed_case = has_upper and has_lower

    segments = re.split(r'[.\u00B7*]', formula)  # hydrate separators: . · *
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
            # Ambiguous casing: trust single-letter-per-symbol first; only
            # fall back to greedy multi-letter recovery if that produced an
            # element symbol that doesn't actually exist (e.g. 'A', 'L').
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
        parsed[sym] = {"n": count, "chi": d[0], "rad": d[1], "col": d[2]}
    return parsed

# ==========================================
# 2. APP CONFIGURATION
# ==========================================
st.set_page_config(page_title="AtomCraft Pro v3.4", layout="wide")
st.markdown("<style>.main { background: #0d1117; color: white; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v3.4")
    user_input = st.text_input("Chemical Formula", value="NaCl")
    iso_val = st.slider("Electron Cloud Density", 0.01, 0.50, 0.12)
    st.info("System: Manual WebGL Init (Fixed)")

# ==========================================
# 3. COMPUTATION
# ==========================================
comp = parse_formula(user_input)

if comp:
    v_list = list(comp.values())
    total_n = sum(v['n'] for v in v_list)
    all_chi = [v['chi'] for v in v_list]
    delta_chi = max(all_chi) - min(all_chi)
    avg_chi = sum(v['chi'] * v['n'] for v in v_list) / total_n

    if delta_chi > 1.7:
        b_type, b_col = "Ionic", "#ff4b4b"
    elif avg_chi < 1.9 and delta_chi < 1.0:
        b_type, b_col = "Metallic", "#58a6ff"
    else:
        b_type, b_col = "Covalent", "#3fb950"

    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader(f"Molecular Lattice: {user_input}")

        # ---- Geometry builder: discrete small molecule vs. extended solid ----
        # BUG FIXED (accuracy): the previous version ignored the parsed atom
        # counts (v['n']) and always dropped unique elements onto a fixed
        # 8-corner cubic grid with 3 A spacing. That's a fine *approximation*
        # for an extended ionic/network solid (NaCl, TiO2-like), but it is
        # wrong for a discrete molecule like H2O, and 3 A is far larger than
        # a real covalent bond (~0.9-1.5 A), so no bonds were ever drawn.
        counts = {sym: v['n'] for sym, v in comp.items()}
        total_atoms = sum(counts.values())
        hub_candidates = [s for s, n in counts.items() if n == 1]

        atom_lines = []

        # Hub priority: real "central" atoms in chemistry are virtually never
        # H, and rarely O — prefer other single-count elements as the hub
        # (e.g. C in H2CO4) before falling back to O, then H.
        def hub_score(s):
            return (s == "H") + (s == "O") * 0.5
        hub_candidates_sorted = sorted(hub_candidates, key=hub_score)

        if hub_candidates_sorted and total_atoms <= 12:
            # --- Discrete small "hub" molecule: hub atom + ALL remaining atoms,
            # respecting their real counts (works for any number of unique
            # elements, e.g. H2, C1, O4 in H2CO4 -> 6 atoms around the hub) ---
            hub = hub_candidates_sorted[0]
            expanded = [s for s, n in counts.items() for _ in range(n)]
            others = expanded.copy()
            others.remove(hub)
            bond_len = 1.1  # representative covalent bond length (A)

            atom_lines.append(f"{hub} 0.00 0.00 0.00")
            n_others = len(others)
            if n_others == 1:
                atom_lines.append(f"{others[0]} {bond_len:.2f} 0.00 0.00")
            elif n_others == 2:
                half_angle = np.radians(104.5 / 2)  # water-like bent angle
                dx, dy = bond_len * np.cos(half_angle), bond_len * np.sin(half_angle)
                atom_lines.append(f"{others[0]} {dx:.2f} {dy:.2f} 0.00")
                atom_lines.append(f"{others[1]} {dx:.2f} {-dy:.2f} 0.00")
            else:
                # Generic even spread on a sphere around the hub for 3+
                # surrounding atoms (Fibonacci sphere) so every single atom in
                # the formula gets a position — none are silently dropped.
                golden_angle = np.pi * (3 - np.sqrt(5))
                for i, sym2 in enumerate(others):
                    y = 1 - (i / float(n_others - 1)) * 2 if n_others > 1 else 0
                    r = np.sqrt(max(0.0, 1 - y * y))
                    theta = golden_angle * i
                    x, z = np.cos(theta) * r, np.sin(theta) * r
                    atom_lines.append(
                        f"{sym2} {bond_len*x:.2f} {bond_len*y:.2f} {bond_len*z:.2f}"
                    )
        else:
            # --- Extended solid: cubic lattice SIZED to the real atom count ---
            # BUG FIXED (accuracy): this used to be hard-capped at 8 fixed grid
            # corners and cycled only the *unique* symbols modulo 8, so any
            # formula with >2 unique elements (or counts that don't divide
            # evenly into 8) rendered the wrong number of each atom type.
            # Now every atom the formula actually specifies gets placed, in a
            # round-robin (interleaved) order so the lattice still alternates
            # visually rather than clumping same-type atoms together.
            buckets = {sym: [sym] * n for sym, n in counts.items()}
            interleaved = []
            while any(buckets.values()):
                for sym in list(buckets.keys()):
                    if buckets[sym]:
                        interleaved.append(buckets[sym].pop(0))

            # Safety cap: render at most MAX_RENDER_ATOMS spheres so an
            # extreme/typo'd formula (e.g. a stray "H500") can't stall the
            # WebGL viewer. The Analysis panel still uses the FULL real counts.
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

        xyz = f"{len(atom_lines)}\nAtomCraft v3.4\n" + "\n".join(atom_lines)

        # Slider -> VDW surface "scale". Higher density value = tighter,
        # more contracted envelope (mimics a higher iso-value cutoff).
        # Swap this whole block for a real isosurface built from a CIF /
        # volumetric DFT grid once Live API Mode supplies actual density data.
        surf_scale = max(0.3, 1.6 - (iso_val * 3.0))

        html_3d = f"""
        <div id="viewer3d" style="height: 500px; width: 100%; background-color: #0b0e14; border-radius: 10px;"></div>
        <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
        <script>
            (function() {{
                let element = document.getElementById('viewer3d');
                let viewer = $3Dmol.createViewer(element, {{ backgroundColor: '0x0b0e14' }});

                let xyzData = `{xyz}`;
                viewer.addModel(xyzData, "xyz");

                viewer.setStyle({{}}, {{
                    sphere: {{ radius: 0.55, colorscheme: 'Jmol' }},
                    stick: {{ radius: 0.12, color: 'grey' }}
                }});

                // BUG FIXED: addIsosurface(null, ...) is invalid — it needs real
                // volumetric grid data and throws on null, which silently killed
                // the rest of the render. A VDW surface is the correct stand-in
                // for an "electron cloud" envelope when no DFT grid exists.
                viewer.addSurface($3Dmol.SurfaceType.VDW, {{
                    opacity: 0.35,
                    color: '{b_col}',
                    scale: {surf_scale}
                }});

                viewer.zoomTo();
                viewer.render();

                window.addEventListener('resize', function() {{
                    viewer.resize();
                }});
            }})();
        </script>
        """
        components.html(html_3d, height=520)

    with c2:
        st.subheader("Analysis")
        st.metric("Bonding Type", b_type)

        bg = max(0, (delta_chi * 2.1) - 0.4) if b_type != "Metallic" else 0
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=bg,
            title={'text': "Band Gap (eV)"},
            gauge={'axis': {'range': [0, 10]}, 'bar': {'color': b_col}}
        ))
        fig.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.table(pd.DataFrame([{"Sym": k, "χ": v['chi']} for k, v in comp.items()]))
else:
    st.error("Invalid Formula")
