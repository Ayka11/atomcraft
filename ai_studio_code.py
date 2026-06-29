import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit.components.v1 as components
import re
from mp_api.client import MPRester

# ==========================================
# 1. SCIENTIFIC DATA & HEURISTICS ENGINE
# ==========================================
# Comprehensive element data for Universal Mode
ELEMENT_DB = {
    "H": {"z": 1, "chi": 2.20, "rad": 0.37, "val": 1, "color": "#FFFFFF", "name": "Hydrogen"},
    "Li": {"z": 3, "chi": 0.98, "rad": 1.34, "val": 1, "color": "#CC80FF", "name": "Lithium"},
    "Be": {"z": 4, "chi": 1.57, "rad": 0.90, "val": 2, "color": "#C2FF00", "name": "Beryllium"},
    "B": {"z": 5, "chi": 2.04, "rad": 0.82, "val": 3, "color": "#FFB5B5", "name": "Boron"},
    "C": {"z": 6, "chi": 2.55, "rad": 0.77, "val": 4, "color": "#909090", "name": "Carbon"},
    "N": {"z": 7, "chi": 3.04, "rad": 0.75, "val": 5, "color": "#3050F8", "name": "Nitrogen"},
    "O": {"z": 8, "chi": 3.44, "rad": 0.73, "val": 6, "color": "#FF0D0D", "name": "Oxygen"},
    "F": {"z": 9, "chi": 3.98, "rad": 0.71, "val": 7, "color": "#90E050", "name": "Fluorine"},
    "Na": {"z": 11, "chi": 0.93, "rad": 1.54, "val": 1, "color": "#AB5CF2", "name": "Sodium"},
    "Mg": {"z": 12, "chi": 1.31, "rad": 1.30, "val": 2, "color": "#8AFF00", "name": "Magnesium"},
    "Al": {"z": 13, "chi": 1.61, "rad": 1.18, "val": 3, "color": "#BFA6A6", "name": "Aluminum"},
    "Si": {"z": 14, "chi": 1.90, "rad": 1.11, "val": 4, "color": "#F0C8A0", "name": "Silicon"},
    "P": {"z": 15, "chi": 2.19, "rad": 1.06, "val": 5, "color": "#FF8000", "name": "Phosphorus"},
    "S": {"z": 16, "chi": 2.58, "rad": 1.02, "val": 6, "color": "#FFFF30", "name": "Sulfur"},
    "Cl": {"z": 17, "chi": 3.16, "rad": 0.99, "val": 7, "color": "#1FF01F", "name": "Chlorine"},
    "Ti": {"z": 22, "chi": 1.54, "rad": 1.36, "val": 4, "color": "#BFC2C7", "name": "Titanium"},
    "Fe": {"z": 26, "chi": 1.83, "rad": 1.25, "val": 8, "color": "#E06633", "name": "Iron"},
    "Cu": {"z": 29, "chi": 1.90, "rad": 1.28, "val": 11, "color": "#C88033", "name": "Copper"},
    "Ga": {"z": 31, "chi": 1.81, "rad": 1.26, "val": 3, "color": "#C38E8E", "name": "Gallium"},
    "As": {"z": 33, "chi": 2.18, "rad": 1.19, "val": 5, "color": "#BD80E3", "name": "Arsenic"},
    "Mo": {"z": 42, "chi": 2.16, "rad": 1.36, "val": 6, "color": "#54B5B5", "name": "Molybdenum"},
    "Au": {"z": 79, "chi": 2.54, "rad": 1.44, "val": 11, "color": "#FFD123", "name": "Gold"}
}

def parse_formula(formula):
    pattern = r'([A-Z][a-z]*)(\d*)'
    res = re.findall(pattern, formula)
    return {el: (int(n) if n else 1) for el, n in res}

def get_properties(formula_dict):
    try:
        elements = list(formula_dict.keys())
        counts = list(formula_dict.values())
        total = sum(counts)
        
        avg_chi = sum(ELEMENT_DB[el]['chi'] * counts[i] for i, el in enumerate(elements)) / total
        delta_chi = max([ELEMENT_DB[el]['chi'] for el in elements]) - min([ELEMENT_DB[el]['chi'] for el in elements])
        avg_rad = sum(ELEMENT_DB[el]['rad'] * counts[i] for i, el in enumerate(elements)) / total
        
        # van Arkel–Ketelaar Classification
        if delta_chi > 1.7: b_type = "Ionic"
        elif avg_chi < 1.9 and delta_chi < 0.8: b_type = "Metallic"
        elif avg_chi > 2.1 and delta_chi < 1.0: b_type = "Covalent Network"
        else: b_type = "Polar Covalent"
        
        return avg_chi, delta_chi, avg_rad, b_type
    except KeyError as e:
        st.error(f"Element {e} not in AtomCraft database yet.")
        return None

# ==========================================
# 2. UI LAYOUT & THEME
# ==========================================
st.set_page_config(page_title="AtomCraft | Nano-Material Designer", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #0a0c10; border-right: 1px solid #30363d; }
    .metric-card { background: #161b22; padding: 20px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2312/2312685.png", width=80)
    st.title("AtomCraft Engine")
    st.markdown("---")
    formula_in = st.text_input("Chemical Formula", "TiO2")
    mode = st.selectbox("Data Mode", ["Universal Prediction", "Materials Project (Live)"])
    iso_val = st.slider("Electron Isosurface", 0.01, 0.50, 0.12)
    
    if mode == "Materials Project (Live)":
        api_key = st.text_input("API Key", type="password")

# LOGIC EXECUTION
comp = parse_formula(formula_in)
props = get_properties(comp)

if props:
    avg_chi, delta_chi, avg_rad, bond_type = props
    
    # 3D VISUALIZATION BUILDER
    def get_3d_lattice(comp, iso):
        # Generate JS for 3Dmol.js
        atoms = []
        els = list(comp.keys())
        # Simple cubic approximation for universal mode
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    el = els[(i+j+k) % len(els)]
                    atoms.append(f"{{elem: '{el}', x: {i*3}, y: {j*3}, z: {k*3}}}")
        
        atoms_js = ",".join(atoms)
        color = ELEMENT_DB[els[0]]['color']
        
        html = f"""
        <div id="container" style="height: 500px; width: 100%; background: #0d1117;"></div>
        <script src="https://3dmol.org/build/3Dmol-min.js"></script>
        <script>
            var viewer = $3Dmol.createViewer('container', {{backgroundColor: '#0d1117'}});
            var data = [{atoms_js}];
            data.forEach(a => {{
                viewer.addSphere({{center: {{x:a.x, y:a.y, z:a.z}}, radius: 1.0, color: '{color}'}});
            }});
            viewer.addIsosurface(null, {{isoval: {iso}, color: 'cyan', opacity: 0.3}});
            viewer.zoomTo();
            viewer.render();
        </script>
        """
        return html

    # LAYOUT COLUMNS
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Atomic Lattice Configuration: {formula_in}")
        components.html(get_3d_lattice(comp, iso_val), height=520)

    with col2:
        st.subheader("Analytics Telemetry")
        
        # Metric Cards
        st.markdown(f"""
        <div class="metric-card">
            <small>Primary Bonding</small><br>
            <strong style="font-size: 20px; color: #58a6ff;">{bond_type}</strong>
        </div><br>
        <div class="metric-card">
            <small>Electronegativity Δ</small><br>
            <strong style="font-size: 20px; color: #3fb950;">{delta_chi:.2f} χ</strong>
        </div>
        """, unsafe_allow_html=True)
        
        # Band Gap Plotly
        bg = max(0, (delta_chi * 2) - 0.5) if bond_type != "Metallic" else 0
        fig_bg = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = bg,
            title = {'text': "Predicted Band Gap (eV)"},
            gauge = {'axis': {'range': [None, 10]}, 'bar': {'color': "#58a6ff"}}
        ))
        fig_bg.update_layout(height=250, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_bg, use_container_width=True)
        
        # Radar Chart
        radar_data = pd.DataFrame(dict(
            r=[80 if bond_type=="Covalent Network" else 30, 
               90 if bond_type=="Metallic" else 10,
               avg_rad*40, 
               delta_chi*20],
            theta=['Hardness','Ductility','Stability', 'Insulation']))
        fig_radar = px.line_polar(radar_data, r='r', theta='theta', line_close=True)
        fig_radar.update_traces(fill='toself')
        fig_radar.update_layout(height=250, paper_bgcolor='rgba(0,0,0,0)', polar=dict(bgcolor='#161b22'))
        st.plotly_chart(fig_radar, use_container_width=True)

st.markdown("---")
st.caption("AtomCraft v1.0 Production Build | Computational Materials Science Unit")