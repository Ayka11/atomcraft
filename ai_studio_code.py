import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import re
from mendeleev import element
from stmol import showmol
import py3Dmol

# --- 1. RESEARCH-GRADE DATA ENGINE ---
@st.cache_data
def get_element_data(symbol):
    """Fetches high-fidelity data from Mendeleev with a local safety net."""
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
    # Auto-fix lowercase inputs
    if formula.islower():
        formula = re.sub(r'([a-z])([a-z]?)', lambda x: x.group(0).capitalize(), formula)
    matches = re.findall(r'([A-Z][a-z]*)(\d*)', formula)
    parsed = {}
    for sym, count in matches:
        data = get_element_data(sym)
        if data:
            parsed[sym] = {"n": int(count) if count else 1, "d": data}
    return parsed

# --- 2. THEME & UI ---
st.set_page_config(page_title="AtomCraft Pro", layout="wide", page_icon="🔬")
st.markdown("""
    <style>
    .main { background: #0d1117; color: white; }
    [data-testid="stMetricValue"] { color: #58a6ff; font-weight: bold; }
    div.stButton > button { background-color: #238636; color: white; border: none; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v3.0")
    st.caption("Universal Material Analytics")
    st.markdown("---")
    user_input = st.text_input("Chemical Formula", value="TiO2", help="e.g., GaAs, nacl, Al2O3")
    iso_val = st.slider("Electron Cloud Isosurface", 0.01, 0.50, 0.15)
    st.success("Visualizer: stmol-Engine (Stable)")

# --- 3. ANALYTICS ---
comp = parse_formula(user_input)

if comp:
    # Calculations
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

    # --- 4. THE ROBUST 3D VISUALIZER (Using stmol) ---
    with col_v:
        st.subheader(f"Structure Rendering: {user_input}")
        
        # Initialize the py3Dmol viewer
        xyzview = py3Dmol.view(width=800, height=500)
        xyzview.setBackgroundColor('#0b0e14')
        
        # Build an XYZ lattice approximation
        els = list(comp.keys())
        idx = 0
        xyz_string = f"{8}\nAtomCraft v3\n"
        for x in [0, 4]:
            for y in [0, 4]:
                for z in [0, 4]:
                    sym = els[idx % len(els)]
                    xyz_string += f"{sym} {x} {y} {z}\n"
                    idx += 1
        
        xyzview.addModel(xyz_string, "xyz")
        xyzview.setStyle({'sphere': {'radius': 1.4, 'colorscheme': 'Jmol'}})
        
        # Add the electron cloud
        xyzview.addIsosurface(None, {
            'isoval': iso_val,
            'color': b_col,
            'opacity': 0.35
        })
        
        xyzview.zoomTo()
        showmol(xyzview, height=500, width=800)

    # --- 5. PROPERTY ANALYTICS ---
    with col_m:
        st.subheader("Property Prediction")
        st.metric("Bonding Regime", b_type)
        
        # Band Gap Estimation
        bg = max(0, (delta_chi * 2.1) - 0.4) if b_type != "Metallic" else 0
        fig_bg = go.Figure(go.Indicator(
            mode = "gauge+number", value = bg,
            title = {'text': "Band Gap (eV)", 'font': {'size': 18}},
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
        fig_bg.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=60, b=0, l=20, r=20))
        st.plotly_chart(fig_bg, use_container_width=True)
        
        # Element Table
        st.write("**Stoichiometric Breakdown**")
        table_data = [{"Element": k, "Count": v['n'], "χ": v['d']['chi']} for k, v in comp.items()]
        st.table(pd.DataFrame(table_data))

else:
    st.error("Formula invalid. Please use standard symbols like NaCl, TiO2, or H2O.")

st.markdown("---")
st.caption("AtomCraft Professional Edition | v3.0 Stable | Materials Informatics Unit")
