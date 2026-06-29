import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import streamlit.components.v1 as components

# ==========================================
# 1. SCIENTIFIC DATA (Zero-Dependency)
# ==========================================
@st.cache_data
def get_el_data(symbol):
    DB = {
        "H": [2.20, 0.37, "#FFFFFF"], "He": [0.00, 0.32, "#D9FFFF"],
        "Li": [0.98, 1.34, "#CC80FF"], "Be": [1.57, 0.90, "#C2FF00"],
        "B": [2.04, 0.82, "#FFB5B5"], "C": [2.55, 0.77, "#909090"],
        "N": [3.04, 0.75, "#3050F8"], "O": [3.44, 0.73, "#FF0D0D"],
        "F": [3.98, 0.71, "#90E050"], "Na": [0.93, 1.54, "#AB5CF2"],
        "Mg": [1.31, 1.30, "#8AFF00"], "Al": [1.61, 1.18, "#BFA6A6"],
        "Si": [1.90, 1.11, "#F0C8A0"], "P": [2.19, 1.06, "#FF8000"],
        "S": [2.58, 1.02, "#FFFF30"], "Cl": [3.16, 0.99, "#1FF01F"],
        "Ti": [1.54, 1.36, "#BFC2C7"], "Fe": [1.83, 1.25, "#E06633"],
        "Cu": [1.90, 1.28, "#C88033"], "Au": [2.54, 1.44, "#FFD123"]
    }
    s = symbol.capitalize()
    return DB.get(s, [2.0, 1.0, "#757575"])

def parse_formula(formula):
    if formula.islower():
        formula = re.sub(r'([a-z])([a-z]?)', lambda x: x.group(0).capitalize(), formula)
    matches = re.findall(r'([A-Z][a-z]*)(\d*)', formula)
    parsed = {}
    for sym, count in matches:
        if not sym:
            continue
        d = get_el_data(sym)
        parsed[sym] = {"n": int(count) if count else 1, "chi": d[0], "rad": d[1], "col": d[2]}
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

            spacing = 2.5
            dim = max(2, int(np.ceil(total_atoms ** (1 / 3))))
            grid_positions = []
            for x in range(dim):
                for y in range(dim):
                    for z in range(dim):
                        grid_positions.append((x * spacing, y * spacing, z * spacing))
                        if len(grid_positions) >= total_atoms:
                            break
                    if len(grid_positions) >= total_atoms:
                        break
                if len(grid_positions) >= total_atoms:
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
