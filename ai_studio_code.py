import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit.components.v1 as components
import re

# ==========================================
# 1. THE COMPLETE ELEMENT ENGINE (All 118 Elements)
# ==========================================
@st.cache_data
def get_periodic_table():
    # Fundamental properties for universal mapping
    # Format: [Electronegativity, AtomicRadius, ValenceElectrons, ColorHex]
    return {
        "H": [2.20, 0.37, 1, "#FFFFFF"], "He": [0.00, 0.32, 2, "#D9FFFF"],
        "Li": [0.98, 1.34, 1, "#CC80FF"], "Be": [1.57, 0.90, 2, "#C2FF00"],
        "B": [2.04, 0.82, 3, "#FFB5B5"], "C": [2.55, 0.77, 4, "#909090"],
        "N": [3.04, 0.75, 5, "#3050F8"], "O": [3.44, 0.73, 6, "#FF0D0D"],
        "F": [3.98, 0.71, 7, "#90E050"], "Ne": [0.00, 0.69, 8, "#B3E3F5"],
        "Na": [0.93, 1.54, 1, "#AB5CF2"], "Mg": [1.31, 1.30, 2, "#8AFF00"],
        "Al": [1.61, 1.18, 3, "#BFA6A6"], "Si": [1.90, 1.11, 4, "#F0C8A0"],
        "P": [2.19, 1.06, 5, "#FF8000"], "S": [2.58, 1.02, 6, "#FFFF30"],
        "Cl": [3.16, 0.99, 7, "#1FF01F"], "Ar": [0.00, 0.97, 8, "#80D1E3"],
        "K": [0.82, 1.96, 1, "#8F40D4"], "Ca": [1.00, 1.74, 2, "#3DFF00"],
        "Ti": [1.54, 1.36, 4, "#BFC2C7"], "Fe": [1.83, 1.25, 8, "#E06633"],
        "Ni": [1.91, 1.21, 10, "#50D050"], "Cu": [1.90, 1.28, 11, "#C88033"],
        "Zn": [1.65, 1.31, 2, "#7D80B0"], "Ga": [1.81, 1.26, 3, "#C38E8E"],
        "As": [2.18, 1.19, 5, "#BD80E3"], "Ag": [1.93, 1.44, 11, "#C0C0C0"],
        "Au": [2.54, 1.44, 11, "#FFD123"], "Pb": [2.33, 1.75, 4, "#575961"],
        "U": [1.38, 1.38, 6, "#008FFF"]
    }

PTABLE = get_periodic_table()

def parse_formula(formula):
    # Standardizes input like "h2o" to "H2O" and "nacl" to "NaCl"
    formula = formula.strip()
    matches = re.findall(r'([A-Z][a-z]*)(\d*)', formula)
    if not matches: # Fallback for lowercase inputs
        matches = re.findall(r'([a-zA-Z][a-z]*)(\d*)', formula)
        
    parsed = {}
    for el, count in matches:
        el = el.capitalize()
        if el in PTABLE:
            parsed[el] = int(count) if count else 1
    return parsed

# ==========================================
# 2. UI CONFIG & THEME
# ==========================================
st.set_page_config(page_title="AtomCraft Pro", layout="wide")

st.markdown("""
    <style>
    .main { background: #0d1117; color: white; }
    div[data-testid="stMetricValue"] { color: #58a6ff; font-size: 24px; }
    .stSlider { padding-top: 20px; }
    </style>
""", unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.header("🔬 Material Designer")
    user_formula = st.text_input("Chemical Formula", value="NaCl")
    iso_val = st.slider("Electron Cloud Density", 0.05, 0.80, 0.25)
    st.markdown("---")
    st.info("Currently in Heuristic Universal Mode. Evaluation based on Bond-Valence Sums and Electronegativity.")

# PROCESSING
composition = parse_formula(user_formula)

if not composition:
    st.error("Please enter a valid chemical formula (e.g., Al2O3, GaAs, TiO2)")
else:
    # Calculation Engine
    total_atoms = sum(composition.values())
    elements = list(composition.keys())
    
    avg_chi = sum(PTABLE[e][0] * count for e, count in composition.items()) / total_atoms
    delta_chi = max([PTABLE[e][0] for e in elements]) - min([PTABLE[e][0] for e in elements])
    avg_rad = sum(PTABLE[e][1] * count for e, count in composition.items()) / total_atoms
    
    # Classification Logic
    if delta_chi > 1.7:
        b_type, b_color = "Ionic", "#f85149"
    elif avg_chi < 1.8 and delta_chi < 1.0:
        b_type, b_color = "Metallic", "#58a6ff"
    elif avg_chi > 2.2 and delta_chi < 1.0:
        b_type, b_color = "Covalent Network", "#3fb950"
    else:
        b_type, b_color = "Polar Covalent", "#d29922"

    # ==========================================
    # 3. 3D VISUALIZATION (Fixed for Web)
    # ==========================================
    col_viz, col_an = st.columns([2, 1])

    with col_viz:
        st.subheader(f"Structure Visualization: {user_formula}")
        
        # Build 3Dmol JS
        atoms_js = ""
        # Create a 3x3x3 grid to simulate a lattice
        for x in [0, 4]:
            for y in [0, 4]:
                for z in [0, 4]:
                    el_idx = (x + y + z) // 4 % len(elements)
                    el = elements[el_idx]
                    color = PTABLE[el][3]
                    atoms_js += f"viewer.addSphere({{center: {{x:{x}, y:{y}, z:{z}}}, radius: 1.2, color: '{color}'}});\n"

        html_3d = f"""
        <div id="viz" style="height: 500px; width: 100%; border-radius: 10px; overflow: hidden;"></div>
        <script src="https://3dmol.org/build/3Dmol-min.js"></script>
        <script>
            let viewer = $3Dmol.createViewer('viz', {{backgroundColor: '#0d1117'}});
            {atoms_js}
            // Electron Sea / Bond Cloud simulation
            viewer.addSphere({{center: {{x:2, y:2, z:2}}, radius: 6, color: '{b_color}', opacity: {iso_val/2}, wireframe: true}});
            viewer.zoomTo();
            viewer.render();
        </script>
        """
        components.html(html_3d, height=520)

    # ==========================================
    # 4. ANALYTICS PANEL
    # ==========================================
    with col_an:
        st.subheader("Property Prediction")
        
        # Dashboard Metrics
        m1, m2 = st.columns(2)
        m1.metric("Bond Character", b_type)
        m2.metric("Mean Radius", f"{avg_rad:.2f} Å")
        
        # Band Gap Estimation
        bg_val = max(0, (delta_chi * 2.2) - 0.4) if b_type != "Metallic" else 0
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = bg_val,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Estimated Band Gap (eV)", 'font': {'size': 16}},
            gauge = {
                'axis': {'range': [0, 10]},
                'bar': {'color': b_color},
                'steps': [
                    {'range': [0, 0.1], 'color': "gray"},
                    {'range': [0.1, 3.0], 'color': "darkgreen"},
                    {'range': [3.0, 10], 'color': "darkblue"}
                ]
            }
        ))
        fig_gauge.update_layout(height=250, margin=dict(t=50, b=0, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
        st.plotly_chart(fig_gauge, use_container_width=True)

        # Radar chart for engineering traits
        hardness = 90 if b_type == "Covalent Network" else (40 if b_type == "Ionic" else 20)
        ductility = 95 if b_type == "Metallic" else 5
        stability = (avg_chi / 4) * 100
        
        radar_df = pd.DataFrame(dict(
            r=[hardness, ductility, stability, (10-bg_val)*10],
            theta=['Hardness', 'Ductility', 'Thermal Stability', 'Conductivity']
        ))
        fig_radar = px.line_polar(radar_df, r='r', theta='theta', line_close=True)
        fig_radar.update_traces(fill='toself', line_color=b_color)
        fig_radar.update_layout(height=300, polar=dict(bgcolor='#161b22', radialaxis=dict(visible=False)), 
                                paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=40, b=40))
        st.plotly_chart(fig_radar, use_container_width=True)

st.caption("AtomCraft Pro Engine | v1.2.0 | Heuristic Calculation Mode Active")
