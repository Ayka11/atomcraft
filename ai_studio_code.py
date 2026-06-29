import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components
import re
from mendeleev import element

# --- 1. DATA ENGINE (With robust fallbacks) ---
@st.cache_data
def get_el_data(symbol):
    fb = {
        "H": [2.2, 0.37, "#FFFFFF"], "C": [2.55, 0.77, "#909090"], "O": [3.44, 0.73, "#FF0D0D"], 
        "Na": [0.93, 1.54, "#AB5CF2"], "Cl": [3.16, 0.99, "#1FF01F"], "Ti": [1.54, 1.36, "#BFC2C7"],
        "Al": [1.61, 1.18, "#BFA6A6"], "Si": [1.90, 1.11, "#F0C8A0"], "Fe": [1.83, 1.25, "#E06633"]
    }
    try:
        e = element(symbol)
        return {"chi": e.electronegativity('pauling') or 2.0, "rad": e.atomic_radius or 1.0, "col": f"#{e.cpk_color}"}
    except:
        if symbol in fb: return {"chi": fb[symbol][0], "rad": fb[symbol][1], "col": fb[symbol][2]}
        return {"chi": 2.0, "rad": 1.0, "col": "#757575"}

def smart_parse(formula):
    # Fix lowercase
    if formula.islower():
        formula = re.sub(r'([a-z])([a-z]?)', lambda x: x.group(0).capitalize(), formula)
    matches = re.findall(r'([A-Z][a-z]*)(\d*)', formula)
    parsed = {}
    for sym, count in matches:
        data = get_el_data(sym)
        parsed[sym] = {"n": int(count) if count else 1, "d": data}
    return parsed

# --- 2. THEME & UI ---
st.set_page_config(page_title="AtomCraft Pro", layout="wide")
st.markdown("<style>.main { background: #0d1117; color: white; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v2.5")
    user_input = st.text_input("Chemical Formula", value="NaCl")
    iso_val = st.slider("Electron Cloud Density", 0.01, 0.50, 0.15)
    st.markdown("---")
    st.success("Deployment: Auto-Initialization Mode")

# --- 3. ANALYTICS ---
comp = smart_parse(user_input)

if comp:
    total = sum(v['n'] for v in comp.values())
    chis = [v['d']['chi'] for v in comp.values()]
    delta_chi = max(chis) - min(chis)
    avg_chi = sum(v['d']['chi'] * v['n'] for v in comp.values()) / total
    
    if delta_chi > 1.7: b_type, b_col = "Ionic", "#ff4b4b"
    elif avg_chi < 1.9 and delta_chi < 0.8: b_type, b_col = "Metallic", "#58a6ff"
    else: b_type, b_col = "Covalent", "#3fb950"

    c_viz, c_met = st.columns([2, 1])

    with c_viz:
        st.subheader(f"Structure Visualization: {user_input}")
        
        # Build the Molecular Data String (SDF format is very stable for 3Dmol)
        sdf_data = "AtomCraft\n\n"
        sdf_data += f"{8:3d}{0:3d}  0  0  0  0  0  0  0  0999 V2000\n" # 8 atoms in a cube
        els = list(comp.keys())
        idx = 0
        for x in [0.0, 4.0]:
            for y in [0.0, 4.0]:
                for z in [0.0, 4.0]:
                    sym = els[idx % len(els)]
                    sdf_data += f"{x:10.4f}{y:10.4f}{z:10.4f} {sym:<3} 0  0  0  0  0  0  0  0  0  0  0  0\n"
                    idx += 1
        sdf_data += "M  END"

        # --- THE AUTO-INIT COMPONENT ---
        # We put the data in a hidden textarea and let 3Dmol find it.
        # This bypasses the 'size' error by letting the library initialize when it's ready.
        html_3d = f"""
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://3dmol.org/build/3Dmol-min.js"></script>
        
        <div id="container" 
             class='viewer_3Dmoljs' 
             data-backgroundcolor='#0b0e14' 
             data-stylespec='{{"sphere":{{"radius":1.5}}}}'
             style="height: 500px; width: 100%; position: relative;">
            <textarea id="data" style="display: none;">{sdf_data}</textarea>
        </div>

        <script>
        $(function() {{
            var v = $3Dmol.viewers['container'];
            // Add the isosurface once the viewer is ready
            var check = setInterval(function() {{
                if(v) {{
                    v.addIsosurface(null, {{isoval: {iso_val}, color: '{b_col}', opacity: 0.4}});
                    v.render();
                    clearInterval(check);
                }}
                v = $3Dmol.viewers['container'];
            }}, 100);
        }});
        </script>
        """
        components.html(html_3d, height=520)

    with c_met:
        st.subheader("Property Prediction")
        st.metric("Bond Type", b_type)
        
        bg = max(0, (delta_chi * 2.1) - 0.4) if b_type != "Metallic" else 0
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = bg,
            title = {'text': "Band Gap (eV)"},
            gauge = {'axis': {'range': [0, 10]}, 'bar': {'color': b_col}}
        ))
        fig.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(l=30,r=30,t=50,b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("**Element Data**")
        st.dataframe(pd.DataFrame([{"Symbol": k, "χ": v['d']['chi'], "Radius": v['d']['rad']} for k, v in comp.items()]), hide_index=True)

else:
    st.error("Formula could not be parsed.")
