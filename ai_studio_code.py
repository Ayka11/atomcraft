import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit.components.v1 as components
import re
from mendeleev import element
from mp_api.client import MPRester

# ==========================================
# 1. SCIENTIFIC UTILITIES
# ==========================================

@st.cache_data
def get_element_data(symbol):
    """Fetches high-fidelity data from Mendeleev library."""
    try:
        el = element(symbol)
        return {
            "name": el.name,
            "chi": el.electronegativity('pauling') or 2.0,
            "radius": el.atomic_radius or 1.0,
            "color": f"#{el.cpk_color}" if el.cpk_color else "#757575",
            "val": el.valence or 1
        }
    except:
        return None

def parse_formula(formula):
    """Parses complex formulas e.g., Ti6Al4V or Al2O3."""
    matches = re.findall(r'([A-Z][a-z]*)(\d*)', formula)
    parsed = {}
    for el_sym, count in matches:
        data = get_element_data(el_sym)
        if data:
            parsed[el_sym] = {
                "count": int(count) if count else 1,
                "data": data
            }
    return parsed

# ==========================================
# 2. UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="AtomCraft Pro", layout="wide", page_icon="🔬")

st.markdown("""
    <style>
    .main { background: #0d1117; color: white; }
    [data-testid="stMetricValue"] { color: #58a6ff; font-size: 1.8rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    </style>
""", unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.title("🔬 AtomCraft v2.0")
    st.caption("Universal Material Designer")
    st.markdown("---")
    user_input = st.text_input("Chemical Formula", value="Al2O3", help="e.g. NaCl, MoS2, GaAs, Ti6Al4V")
    
    mode = st.radio("Intelligence Engine", ["Heuristic (Mendeleev)", "Live Quantum (MP-API)"])
    
    iso_val = st.slider("Electron Density Isosurface", 0.01, 0.50, 0.15)
    
    st.markdown("---")
    if mode == "Live Quantum (MP-API)":
        if "MP_API_KEY" not in st.secrets:
            st.error("Secrets Error: MP_API_KEY not found in TOML.")
        else:
            st.success("MP-API Key Linked")

# ==========================================
# 3. COMPUTATION PIPELINE
# ==========================================
comp = parse_formula(user_input)

if not comp:
    st.warning("Enter a valid formula to begin analysis.")
    st.stop()

# Basic Chemistry Math
total_atoms = sum(v['count'] for v in comp.values())
avg_chi = sum(v['data']['chi'] * v['count'] for v in comp.values()) / total_atoms
all_chis = [v['data']['chi'] for v in comp.values()]
delta_chi = max(all_chis) - min(all_chis)
avg_rad = sum(v['data']['radius'] * v['count'] for v in comp.values()) / total_atoms

# Fallback Values
band_gap = 0.0
density = 0.0

# API Data Fetching
if mode == "Live Quantum (MP-API)" and "MP_API_KEY" in st.secrets:
    try:
        with MPRester(st.secrets["MP_API_KEY"]) as mpr:
            results = mpr.summary.search(formula=user_input, fields=["band_gap", "density"])
            if results:
                band_gap = results[0].band_gap
                density = results[0].density
    except Exception as e:
        st.error(f"API Fetch Failed: {e}")

# Heuristic Fallback for Band Gap (if API fails or not used)
if band_gap == 0.0 and delta_chi > 0.5:
    band_gap = (delta_chi * 2.0) - 0.4 # First principles approx

# Classification
if delta_chi > 1.7: bond_type, b_color = "Ionic", "#ff4b4b"
elif avg_chi < 1.9 and delta_chi < 0.8: bond_type, b_color = "Metallic", "#58a6ff"
elif avg_chi > 2.2 and delta_chi < 1.0: bond_type, b_color = "Covalent Network", "#3fb950"
else: bond_type, b_color = "Polar Covalent", "#d29922"

# ==========================================
# 4. DASHBOARD LAYOUT
# ==========================================

col_viz, col_metrics = st.columns([1.5, 1])

with col_viz:
    st.subheader(f"Atomistic Configuration: {user_input}")
    
    # Generate 3Dmol Visualization
    atoms_js = ""
    elements = list(comp.keys())
    for i in range(3):
        for j in range(3):
            for k in range(3):
                el_sym = elements[(i+j+k) % len(elements)]
                color = comp[el_sym]['data']['color']
                atoms_js += f"viewer.addSphere({{center:{{x:{i*4},y:{j*4},z:{k*4}}}, radius:1.2, color:'{color}'}});\n"

    html_3d = f"""
    <div id="container" style="height: 500px; width: 100%; border-radius:15px; background: #0b0e14;"></div>
    <script src="https://3dmol.org/build/3Dmol-min.js"></script>
    <script>
        let element = document.getElementById('container');
        let viewer = $3Dmol.createViewer(element, {{backgroundColor: '#0b0e14'}});
        {atoms_js}
        viewer.addIsosurface(null, {{isoval: {iso_val}, color: '{b_color}', opacity: 0.35, smoothness: 5}});
        viewer.zoomTo();
        viewer.render();
    </script>
    """
    components.html(html_3d, height=520)

with col_metrics:
    st.subheader("Nano-Scale Telemetry")
    
    m1, m2 = st.columns(2)
    m1.metric("Bonding Regime", bond_type)
    m2.metric("Band Gap", f"{band_gap:.2f} eV")
    
    # Engineering Radar Chart
    hardness = 90 if bond_type == "Covalent Network" else (50 if bond_type == "Ionic" else 20)
    ductility = 90 if bond_type == "Metallic" else 10
    thermal = 85 if bond_type in ["Ionic", "Covalent Network"] else 40
    
    radar_df = pd.DataFrame(dict(
        r=[hardness, ductility, thermal, (1 - (avg_rad/2.5))*100],
        theta=['Hardness', 'Ductility', 'Thermal Stability', 'Structural Density']
    ))
    
    fig_radar = px.line_polar(radar_df, r='r', theta='theta', line_close=True)
    fig_radar.update_traces(fill='toself', line_color=b_color)
    fig_radar.update_layout(
        polar=dict(bgcolor='#161b22', radialaxis=dict(visible=False, range=[0, 100])),
        showlegend=False, template="plotly_dark", height=320, margin=dict(t=30, b=30, l=30, r=30)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # Band Gap Gauge
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = band_gap,
        title = {'text': "Electrical Classification", 'font': {'size': 16}},
        gauge = {
            'axis': {'range': [0, 8]},
            'bar': {'color': b_color},
            'steps': [
                {'range': [0, 0.1], 'color': "#58a6ff"}, # Metal
                {'range': [0.1, 3.0], 'color': "#3fb950"}, # Semiconductor
                {'range': [3.0, 8], 'color': "#f85149"} # Insulator
            ]
        }
    ))
    fig_gauge.update_layout(height=250, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=50, b=0))
    st.plotly_chart(fig_gauge, use_container_width=True)

st.markdown("---")
st.info(f"**Chemical Insights:** {user_input} has an average electronegativity of **{avg_chi:.2f}**. This creates a **{bond_type.lower()}** environment.")
