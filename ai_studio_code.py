import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components
import re
from mendeleev import element

# --- 1. ROBUST DATA ENGINE ---
@st.cache_data
def get_el_data(symbol):
    # Expanded safety fallback
    fb = {
        "H": [2.2, 0.37, "#FFFFFF"], "C": [2.55, 0.77, "#909090"], "O": [3.44, 0.73, "#FF0D0D"], 
        "Na": [0.93, 1.54, "#AB5CF2"], "Cl": [3.16, 0.99, "#1FF01F"], "Ti": [1.54, 1.36, "#BFC2C7"],
        "Al": [1.61, 1.18, "#BFA6A6"], "Si": [1.90, 1.11, "#F0C8A0"], "Fe": [1.83, 1.25, "#E06633"],
        "Au": [2.54, 1.44, "#FFD123"], "Cu": [1.90, 1.28, "#C88033"], "N": [3.04, 0.75, "#3050F8"]
    }
    try:
        e = element(symbol)
        return {"chi": e.electronegativity('pauling') or 2.0, "rad": e.atomic_radius or 1.0, "col": f"#{e.cpk_color}"}
    except:
        if symbol in fb: return {"chi": fb[symbol][0], "rad": fb[symbol][1], "col": fb[symbol][2]}
        return {"chi": 2.0, "rad": 1.0, "col": "#757575"}

def smart_parse(formula):
    if formula.islower():
        formula = re.sub(r'([a-z])([a-z]?)', lambda x: x.group(0).capitalize(), formula)
    matches = re.findall(r'([A-Z][a-z]*)(\d*)', formula)
    parsed = {}
    for sym, count in matches:
        data = get_el_data(sym)
        if data:
            parsed[sym] = {"n": int(count) if count else 1, "d": data}
    return parsed

# --- 2. THEME & UI ---
st.set_page_config(page_title="AtomCraft Pro", layout="wide")
st.markdown("<style>.main { background: #0d1117; color: white; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v2.9")
    user_input = st.text_input("Chemical Formula", value="NaCl")
    iso_val = st.slider("Electron Cloud Density", 0.01, 0.50, 0.15)
    st.markdown("---")
    st.warning("Render Mode: Absolute-Stable (Auto-Lattice)")

# --- 3. ANALYTICS ---
comp = smart_parse(user_input)

if comp:
    # Calculations (Corrected iteration)
    v_list = list(comp.values())
    total_count = sum(v['n'] for v in v_list)
    all_chis = [v['d']['chi'] for v in v_list]
    delta_chi = max(all_chis) - min(all_chis)
    avg_chi = sum(v['d']['chi'] * v['n'] for v in v_list) / total_count
    
    # Classification
    if delta_chi > 1.7: b_type, b_col = "Ionic", "#ff4b4b"
    elif avg_chi < 1.9 and delta_chi < 0.8: b_type, b_col = "Metallic", "#58a6ff"
    else: b_type, b_col = "Covalent", "#3fb950"

    col_v, col_m = st.columns([2, 1])

    with col_v:
        st.subheader(f"3D Visualizer: {user_input}")
        
        # Build an SDF format string (Most compatible with 3Dmol auto-loader)
        els = list(comp.keys())
        sdf = f"{user_input}\\nAtomCraft\\n\\n 8 0 0 0 0 0 0 0 0 0999 V2000\\n"
        idx = 0
        for x in [0, 5]:
            for y in [0, 5]:
                for z in [0, 5]:
                    sym = els[idx % len(els)]
                    sdf += f"  {x:7.4f}  {y:7.4f}  {z:7.4f} {sym:<3} 0  0  0  0  0  0  0  0  0  0  0  0\\n"
                    idx += 1
        sdf += "M  END"

        # --- THE ABSOLUTE STABILITY INJECTION ---
        # 1. Load jQuery and 3Dmol in the head
        # 2. Use the 'viewer_3Dmoljs' class which is a self-bootstrapping method.
        # 3. Add a manual render trigger as a fallback.
        html_3d = f"""
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
        <script src="https://3dmol.org/build/3Dmol-min.js"></script>
        
        <div style="height: 500px; width: 100%; position: relative;" 
             class='viewer_3Dmoljs' 
             data-backgroundcolor='#0b0e14' 
             data-style='{{"sphere":{{"radius":1.5}}}}'>
            <textarea style="display:none;" id="sdf_data">{sdf}</textarea>
        </div>

        <script>
        $(document).ready(function() {{
            var viewer = $3Dmol.viewers[0] || $3Dmol.viewers[''];
            if(!viewer) {{
                // If auto-init fails, manual init after 200ms
                setTimeout(function() {{
                    var el = $('.viewer_3Dmoljs');
                    viewer = $3Dmol.createViewer(el, {{backgroundColor: '#0b0e14'}});
                    viewer.addModel($('#sdf_data').val(), "sdf");
                    viewer.setStyle({{}}, {{sphere: {{radius: 1.5}}}});
                    viewer.addIsosurface(null, {{isoval: {iso_val}, color: '{b_col}', opacity: 0.4}});
                    viewer.zoomTo();
                    viewer.render();
                }}, 300);
            }} else {{
                // Auto-init worked, just add isosurface
                viewer.addModel($('#sdf_data').val(), "sdf");
                viewer.addIsosurface(null, {{isoval: {iso_val}, color: '{b_col}', opacity: 0.4}});
                viewer.zoomTo();
                viewer.render();
            }}
        }});
        </script>
        """
        components.html(html_3d, height=520)

    with col_m:
        st.subheader("Analytics")
        st.metric("Bonding Type", b_type)
        
        bg = max(0, (delta_chi * 2.1) - 0.4) if b_type != "Metallic" else 0
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = bg,
            title = {'text': "Band Gap (eV)"},
            gauge = {'axis': {'range': [0, 10]}, 'bar': {'color': b_col}}
        ))
        fig.update_layout(height=260, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(l=30,r=30,t=50,b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        st.table(pd.DataFrame([{"Sym": k, "χ": v['d']['chi']} for k, v in comp.items()]))

else:
    st.error("Invalid formula. Please enter a valid chemical symbol (e.g., NaCl).")
