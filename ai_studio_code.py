import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import streamlit.components.v1 as components

# ==========================================
# 1. INTERNAL SCIENTIFIC DATABASE 
# (No mendeleev import needed - avoids crashes)
# ==========================================
@st.cache_data
def get_el_data(symbol):
    # Comprehensive internal dictionary for standard elements
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
        "Ni": [1.91, 1.21, "#50D050"], "Cu": [1.90, 1.28, "#C88033"],
        "Zn": [1.65, 1.31, "#7D80B0"], "Ga": [1.81, 1.26, "#C38E8E"],
        "As": [2.18, 1.19, "#BD80E3"], "Ag": [1.93, 1.44, "#C0C0C0"],
        "Au": [2.54, 1.44, "#FFD123"], "U": [1.38, 1.38, "#008FFF"]
    }
    symbol = symbol.capitalize()
    if symbol in DB:
        return {"chi": DB[symbol][0], "rad": DB[symbol][1], "col": DB[symbol][2]}
    return {"chi": 2.0, "rad": 1.0, "col": "#757575"} # Generic fallback

def parse_formula(formula):
    # Auto-fix lowercase
    if formula.islower():
        formula = re.sub(r'([a-z])([a-z]?)', lambda x: x.group(0).capitalize(), formula)
    matches = re.findall(r'([A-Z][a-z]*)(\d*)', formula)
    parsed = {}
    for sym, count in matches:
        data = get_el_data(sym)
        parsed[sym] = {"n": int(count) if count else 1, "d": data}
    return parsed

# ==========================================
# 2. UI DESIGN
# ==========================================
st.set_page_config(page_title="AtomCraft Pro v3.1", layout="wide")
st.markdown("<style>.main { background: #0d1117; color: white; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v3.1")
    st.caption("Zero-Dependency Engine")
    st.markdown("---")
    user_input = st.text_input("Chemical Formula", value="NaCl")
    iso_val = st.slider("Electron Cloud Density", 0.01, 0.50, 0.15)
    st.success("Visualizer: WebGL-Direct Mode")

# ==========================================
# 3. COMPUTATION
# ==========================================
comp = parse_formula(user_input)

if comp:
    v_list = list(comp.values())
    total_count = sum(v['n'] for v in v_list)
    all_chis = [v['d']['chi'] for v in v_list]
    delta_chi = max(all_chis) - min(all_chis)
    avg_chi = sum(v['d']['chi'] * v['n'] for v in v_list) / total_count
    
    # Classification logic
    if delta_chi > 1.7: b_type, b_col = "Ionic", "#ff4b4b"
    elif avg_chi < 1.9 and delta_chi < 0.8: b_type, b_col = "Metallic", "#58a6ff"
    else: b_type, b_col = "Covalent", "#3fb950"

    col_v, col_m = st.columns([2, 1])

    with col_v:
        st.subheader(f"Structure: {user_input}")
        
        # Build Lattice Data
        els = list(comp.keys())
        idx = 0
        xyz = f"8\\nAtomCraft v3\\n"
        for x in [0, 5]:
            for y in [0, 5]:
                for z in [0, 5]:
                    sym = els[idx % len(els)]
                    xyz += f"{sym} {x} {y} {z}\\n"
                    idx += 1
        
        # --- ZERO-DEPENDENCY WEBGL ENGINE ---
        # We load the library via HTML, not Python import.
        html_3d = f"""
        <div id="container_3d" style="height: 500px; width: 100%; background-color: #0b0e14; border-radius: 10px;"></div>
        <script src="https://3dmol.org/build/3Dmol-min.js"></script>
        <script>
            function start() {{
                if (typeof $3Dmol === 'undefined') {{ setTimeout(start, 100); return; }}
                const div = document.getElementById('container_3d');
                const viewer = $3Dmol.createViewer(div, {{ backgroundColor: '#0b0e14' }});
                viewer.addModel("{xyz}", "xyz");
                viewer.setStyle({{}}, {{sphere: {{radius: 1.5}}}});
                viewer.addIsosurface(null, {{isoval: {iso_val}, color: '{b_col}', opacity: 0.3}});
                viewer.zoomTo();
                viewer.render();
                
                // Keep trying to resize to fix black-box issues
                setInterval(() => {{ if(div.offsetWidth > 0) viewer.resize(); }}, 500);
            }}
            start();
        </script>
        """
        components.html(html_3d, height=520)

    with col_m:
        st.subheader("Property Prediction")
        st.metric("Bonding Regime", b_type)
        
        # Band Gap Gauge
        bg = max(0, (delta_chi * 2.1) - 0.4) if b_type != "Metallic" else 0
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = bg,
            title = {'text': "Band Gap (eV)"},
            gauge = {'axis': {'range': [0, 10]}, 'bar': {'color': b_col}}
        ))
        fig.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=50,b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.table(pd.DataFrame([{"Sym": k, "χ": v['d']['chi']} for k, v in comp.items()]))
else:
    st.error("Formula invalid.")
