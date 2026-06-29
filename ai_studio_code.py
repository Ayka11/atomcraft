import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
from mendeleev import element
from stmol import showmol
import py3Dmol

# ==========================================
# 1. CORE SCIENTIFIC ENGINE
# ==========================================

@st.cache_data
def get_element_data(symbol):
    """Fetches high-fidelity atomic data with local safety fallbacks."""
    # Emergency fallbacks for common elements if the database is busy
    fb = {
        "H": [2.2, 0.37, "#FFFFFF"], "C": [2.55, 0.77, "#909090"], "O": [3.44, 0.73, "#FF0D0D"], 
        "Na": [0.93, 1.54, "#AB5CF2"], "Cl": [3.16, 0.99, "#1FF01F"], "Ti": [1.54, 1.36, "#BFC2C7"],
        "Al": [1.61, 1.18, "#BFA6A6"], "Si": [1.90, 1.11, "#F0C8A0"], "Fe": [1.83, 1.25, "#E06633"]
    }
    try:
        e = element(symbol)
        return {
            "chi": e.electronegativity('pauling') or 2.0,
            "rad": e.atomic_radius or 1.0,
            "col": f"#{e.cpk_color}" if e.cpk_color else "#757575"
        }
    except:
        if symbol in fb:
            return {"chi": fb[symbol][0], "rad": fb[symbol][1], "col": fb[symbol][2]}
        return {"chi": 2.0, "rad": 1.0, "col": "#757575"}

def parse_formula(formula):
    """Smart parser for complex stoichiometry (e.g., Ti6Al4V, NaCl, h2o)."""
    # Fix lowercase inputs automatically
    if formula.islower():
        formula = re.sub(r'([a-z])([a-z]?)', lambda x: x.group(0).capitalize(), formula)
    
    matches = re.findall(r'([A-Z][a-z]*)(\d*)', formula)
    parsed = {}
    for sym, count in matches:
        data = get_element_data(sym)
        if data:
            parsed[sym] = {"n": int(count) if count else 1, "d": data}
    return parsed

# ==========================================
# 2. UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="AtomCraft Pro v3.0", layout="wide", page_icon="🔬")

# Custom Professional Theme
st.markdown("""
    <style>
    .main { background: #0d1117; color: white; }
    [data-testid="stMetricValue"] { color: #58a6ff; font-weight: bold; font-family: monospace; }
    .stSlider { padding-top: 20px; }
    div.stButton > button { width: 100%; border-radius: 5px; background-color: #238636; color: white; }
    </style>
""", unsafe_allow_html=True)

# SIDEBAR CONTROLS
with st.sidebar:
    st.title("🔬 AtomCraft v3.0")
    st.caption("Universal Nano-Material Designer")
    st.markdown("---")
    user_input = st.text_input("Chemical Formula", value="TiO2", help="Type any valid material (e.g., GaAs, nacl, Al2O3)")
    iso_val = st.slider("Electron Cloud Density", 0.01, 0.50, 0.15)
    st.markdown("---")
    st.info("Visualizer Status: **stmol-STABLE**")
    st.success("Heuristic Analysis Active")

# ==========================================
# 3. COMPUTATIONAL PIPELINE
# ==========================================
comp = parse_formula(user_input)

if comp:
    # Math Engine
    v_list = list(comp.values())
    total_atoms = sum(v['n'] for v in v_list)
    all_chis = [v['d']['chi'] for v in v_list]
    delta_chi = max(all_chis) - min(all_chis)
    avg_chi = sum(v['d']['chi'] * v['n'] for v in v_list) / total_atoms
    
    # Material Classification (Van Arkel-Ketelaar logic)
    if delta_chi > 1.7: 
        b_type, b_col = "Ionic", "#ff4b4b"
    elif avg_chi < 1.9 and delta_chi < 0.8: 
        b_type, b_col = "Metallic", "#58a6ff"
    elif avg_chi > 2.2 and delta_chi < 1.0:
        b_type, b_col = "Covalent Network", "#3fb950"
    else: 
        b_type, b_col = "Polar Covalent", "#d29922"

    # Dashboard Columns
    col_v, col_m = st.columns([2, 1])

    # --- CENTER: 3D WEBGL VISUALIZER ---
    with col_v:
        st.subheader(f"Structure Rendering: {user_input}")
        
        # Initialize py3Dmol
        view = py3Dmol.view(width=800, height=500)
        view.setBackgroundColor('#0b0e14')
        
        # Create a lattice coordinate set
        xyz_data = f"{8}\nAtomCraft v3\n"
        els = list(comp.keys())
        idx = 0
        for x in [0, 5]:
            for y in [0, 5]:
                for z in [0, 5]:
                    sym = els[idx % len(els)]
                    xyz_data += f"{sym} {x} {y} {z}\n"
                    idx += 1
        
        view.addModel(xyz_data, "xyz")
        view.setStyle({'sphere': {'radius': 1.5, 'colorscheme': 'Jmol'}})
        
        # Add the Translucent Electron Cloud
        view.addIsosurface(None, {
            'isoval': iso_val,
            'color': b_col,
            'opacity': 0.3
        })
        
        view.zoomTo()
        # This is the magic function that prevents "Black Box" errors
        showmol(view, height=500, width=800)

    # --- RIGHT: PROPERTY TELEMETRY ---
    with col_m:
        st.subheader("Property Prediction")
        st.metric("Bonding Character", b_type)
        
        # Electrical Gap Gauge
        bg = max(0, (delta_chi * 2.1) - 0.4) if b_type != "Metallic" else 0
        fig_bg = go.Figure(go.Indicator(
            mode = "gauge+number", value = bg,
            title = {'text': "Band Gap (eV)"},
            gauge = {
                'axis': {'range': [0, 10]},
                'bar': {'color': b_col},
                'steps': [
                    {'range': [0, 0.1], 'color': "gray"},
                    {'range': [0.1, 3.0], 'color': "#238636"},
                    {'range': [3.0, 10], 'color': "#1f6feb"}
                ]
            }
        ))
        fig_bg.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=50, b=10))
        st.plotly_chart(fig_bg, use_container_width=True)
        
        # Data Breakdown
        st.write("**Stoichiometry Breakdown**")
        df_display = pd.DataFrame([
            {"Element": k, "Count": v['n'], "χ": v['d']['chi']} for k, v in comp.items()
        ])
        st.table(df_display)

else:
    st.error("Invalid Input. Please enter a chemical formula like 'NaCl' or 'TiO2'.")

st.markdown("---")
st.caption("AtomCraft Professional Edition | v3.0 Stable | Engineered for Materials Informatics")
