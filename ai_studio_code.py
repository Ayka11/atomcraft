import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit.components.v1 as components
import re
from mendeleev import element

# ==========================================
# 1. SMART CHEMICAL ENGINE
# ==========================================

@st.cache_data
def get_element_info(symbol):
    """Fetches data with a hardcoded fallback for common elements."""
    # Fallback dictionary for stability
    FALLBACK = {
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
        "As": [2.18, 1.19, "#BD80E3"], "Au": [2.54, 1.44, "#FFD123"]
    }
    
    try:
        # Try Mendeleev first
        el = element(symbol)
        return {
            "chi": el.electronegativity('pauling') or 2.0,
            "radius": el.atomic_radius or 1.0,
            "color": f"#{el.cpk_color}" if el.cpk_color else "#757575"
        }
    except:
        # Use Fallback if Mendeleev fails
        if symbol in FALLBACK:
            return {
                "chi": FALLBACK[symbol][0],
                "radius": FALLBACK[symbol][1],
                "color": FALLBACK[symbol][2]
            }
    return None

def smart_parse(formula):
    """
    Handles NaCl, nacl, Na2O, h2o, Ti6Al4V.
    """
    # Fix common mistake: user types all lowercase
    if formula.islower():
        # Capitalize first letter of every element pattern (simplistic)
        formula = re.sub(r'([a-z])([a-z]?)', lambda x: x.group(0).capitalize(), formula)

    # Improved Regex: Finds Element + optional Count
    matches = re.findall(r'([A-Z][a-z]?)(\d*)', formula)
    
    parsed = {}
    for sym, count in matches:
        data = get_element_info(sym)
        if data:
            parsed[sym] = {
                "count": int(count) if count else 1,
                "data": data
            }
    return parsed

# ==========================================
# 2. UI SETUP
# ==========================================
st.set_page_config(page_title="AtomCraft Pro", layout="wide")

st.markdown("""
    <style>
    .main { background: #0d1117; color: white; }
    .stTextInput input { background-color: #161b22; color: white; border: 1px solid #30363d; }
    [data-testid="stMetricValue"] { color: #58a6ff; }
    </style>
""", unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.title("🔬 AtomCraft Designer")
    user_input = st.text_input("Enter Formula", value="NaCl", placeholder="e.g. TiO2, nacl, Al2O3")
    iso_val = st.slider("Bond Cloud Density", 0.01, 0.50, 0.15)
    st.info("Tip: You can now type in lowercase (nacl, h2o)!")

# ==========================================
# 3. PROCESSING
# ==========================================
comp = smart_parse(user_input)

if not comp:
    st.error(f"Could not identify elements in '{user_input}'. Please use standard symbols like NaCl, h2o, or TiO2.")
    st.stop()

# Calculations
total_atoms = sum(v['count'] for v in comp.values())
avg_chi = sum(v['data']['chi'] * v['count'] for v in comp.values()) / total_atoms
all_chis = [v['data']['chi'] for v in comp.values()]
delta_chi = max(all_chis) - min(all_chis)
avg_rad = sum(v['data']['radius'] * v['count'] for v in comp.values()) / total_atoms

# Classification Logic
if delta_chi > 1.7: 
    bond_type, b_color = "Ionic", "#ff4b4b"
elif avg_chi < 1.9 and delta_chi < 0.8: 
    bond_type, b_color = "Metallic", "#58a6ff"
else: 
    bond_type, b_color = "Covalent", "#3fb950"

# ==========================================
# 4. DASHBOARD
# ==========================================
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader(f"Atomistic Preview: {user_input}")
    
    # Generate 3Dmol JS
    atoms_js = ""
    elements = list(comp.keys())
    for x in [0, 4]:
        for y in [0, 4]:
            for z in [0, 4]:
                el_sym = elements[(x+y+z)//4 % len(elements)]
                color = comp[el_sym]['data']['color']
                atoms_js += f"viewer.addSphere({{center:{{x:{x},y:{y},z:{z}}}, radius:1.2, color:'{color}'}});\n"

    html_3d = f"""
    <div id="v" style="height: 450px; width: 100%; background: #0d1117; border-radius:10px;"></div>
    <script src="https://3dmol.org/build/3Dmol-min.js"></script>
    <script>
        let viewer = $3Dmol.createViewer('v');
        {atoms_js}
        viewer.addIsosurface(null, {{isoval: {iso_val}, color: '{b_color}', opacity: 0.4}});
        viewer.zoomTo(); viewer.render();
    </script> """
    components.html(html_3d, height=470)

with c2:
    st.subheader("Predicted Metrics")
    st.metric("Bonding Type", bond_type)
    
    # Band Gap Plotly Gauge
    bg = max(0, (delta_chi * 2.1) - 0.4) if bond_type != "Metallic" else 0
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = bg,
        title = {'text': "Band Gap (eV)"},
        gauge = {'axis': {'range': [0, 10]}, 'bar': {'color': b_color}}
    ))
    fig.update_layout(height=250, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
    st.plotly_chart(fig, use_container_width=True)

    # Property Table
    st.write("**Element Composition**")
    st.table(pd.DataFrame([
        {"Element": k, "Count": v['count'], "Electronegativity": v['data']['chi']} 
        for k, v in comp.items()
    ]))

st.success(f"Analysis Complete for {user_input}")
