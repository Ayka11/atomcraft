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

        # ---- Build a PROPERLY newlined XYZ block (mock 8-atom cubic lattice) ----
        # BUG FIXED: the original used "\\n" (a literal backslash+n), which is
        # NOT a line break, so the 3Dmol XYZ parser could never split atoms.
        els = list(comp.keys())
        atom_lines = []
        idx = 0
        for x in [0, 3]:
            for y in [0, 3]:
                for z in [0, 3]:
                    sym = els[idx % len(els)]
                    atom_lines.append(f"{sym} {x:.2f} {y:.2f} {z:.2f}")
                    idx += 1
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
