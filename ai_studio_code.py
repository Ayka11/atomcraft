import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
from mendeleev import element
import py3Dmol
import streamlit.components.v1 as components

# --- 1. DATA ENGINE ---
@st.cache_data
def get_el_data(symbol):
    fb = {"H": [2.2, 0.37, "#FFFFFF"], "C": [2.55, 0.77, "#909090"], "O": [3.44, 0.73, "#FF0D0D"], 
          "Na": [0.93, 1.54, "#AB5CF2"], "Cl": [3.16, 0.99, "#1FF01F"], "Ti": [1.54, 1.36, "#BFC2C7"]}
    try:
        e = element(symbol)
        return {"chi": e.electronegativity('pauling') or 2.0, "rad": e.atomic_radius or 1.0, "col": f"#{e.cpk_color}"}
    except:
        if symbol in fb: return {"chi": fb[symbol][0], "rad": fb[symbol][1], "col": fb[symbol][2]}
        return {"chi": 2.0, "rad": 1.0, "col": "#757575"}

def parse_formula(formula):
    if formula.islower():
        formula = re.sub(r'([a-z])([a-z]?)', lambda x: x.group(0).capitalize(), formula)
    matches = re.findall(r'([A-Z][a-z]*)(\d*)', formula)
    parsed = {}
    for sym, count in matches:
        data = get_el_data(sym)
        if data: parsed[sym] = {"n": int(count) if count else 1, "d": data}
    return parsed

# --- 2. UI ---
st.set_page_config(page_title="AtomCraft Pro", layout="wide")
st.markdown("<style>.main { background: #0d1117; color: white; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v3.0")
    user_input = st.text_input("Formula", value="NaCl")
    iso_val = st.slider("Electron Cloud Density", 0.01, 0.50, 0.15)
    st.info("Visualizer: Deep-Lattice Mode")

# --- 3. ANALYTICS ---
comp = parse_formula(user_input)

if comp:
    v_list = list(comp.values())
    total_count = sum(v['n'] for v in v_list)
    all_chis = [v['d']['chi'] for v in v_list]
    delta_chi = max(all_chis) - min(all_chis)
    avg_chi = sum(v['d']['chi'] * v['n'] for v in v_list) / total_count
    
    if delta_chi > 1.7: b_type, b_col = "Ionic", "#ff4b4b"
    elif avg_chi < 1.9 and delta_chi < 0.8: b_type, b_col = "Metallic", "#58a6ff"
    else: b_type, b_col = "Covalent", "#3fb950"

    col_v, col_m = st.columns([2, 1])

    with col_v:
        st.subheader(f"Structure Visualization: {user_input}")
        
        # Build XYZ Lattice
        els = list(comp.keys())
        idx = 0
        xyz = f"8\\nAtomCraft v3\\n"
        for x in [0, 4]:
            for y in [0, 4]:
                for z in [0, 4]:
                    sym = els[idx % len(els)]
                    xyz += f"{sym} {x} {y} {z}\\n"
                    idx += 1
        
        # --- ROBUST 3DMOL EMBED ---
        # This version does not need 'stmol' to work.
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
                
                // Fix for the black/white box issue: check size every 500ms
                setInterval(() => {{ if(div.offsetWidth > 0) viewer.resize(); }}, 500);
            }}
            start();
        </script>
        """
        components.html(html_3d, height=520)

    with col_m:
        st.subheader("Property Prediction")
        st.metric("Bonding Type", b_type)
        
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
    st.error("Invalid formula.")
