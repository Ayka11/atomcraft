import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components
import re
from mendeleev import element

# --- 1. DATA ENGINE (Robust + Fallbacks) ---
@st.cache_data
def get_el_data(symbol):
    fb = {
        "H": [2.2, 0.37, "#FFFFFF"], "C": [2.55, 0.77, "#909090"], "O": [3.44, 0.73, "#FF0D0D"], 
        "Na": [0.93, 1.54, "#AB5CF2"], "Cl": [3.16, 0.99, "#1FF01F"], "Ti": [1.54, 1.36, "#BFC2C7"]
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

# --- 2. STREAMLIT UI ---
st.set_page_config(page_title="AtomCraft Pro", layout="wide")
st.markdown("<style>.main { background: #0d1117; color: white; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v2.8")
    user_input = st.text_input("Chemical Formula", value="NaCl")
    iso_val = st.slider("Electron Cloud Density", 0.01, 0.50, 0.15)
    st.markdown("---")
    st.info("Visualizer Status: Deep-Render Mode Active")

# --- 3. CORE COMPUTATION ---
comp = smart_parse(user_input)

if comp:
    total_count = sum(v['n'] for v in comp.values())
    all_chis = [v['d']['chi'] for v in comp.values()]
    delta_chi = max(all_chis) - min(all_chis)
    avg_chi = sum(v['d']['chi'] * v['n'] for v in comp.values()) / total_count
    
    if delta_chi > 1.7: b_type, b_col = "Ionic", "#ff4b4b"
    elif avg_chi < 1.9 and delta_chi < 0.8: b_type, b_col = "Metallic", "#58a6ff"
    else: b_type, b_col = "Covalent", "#3fb950"

    col_v, col_m = st.columns([2, 1])

    with col_v:
        st.subheader(f"3D Structure: {user_input}")
        
        # Build Atom List
        els = list(comp.keys())
        atoms_js = []
        for i in [0, 4]:
            for j in [0, 4]:
                for k in [0, 4]:
                    sym = els[(i+j+k)//4 % len(els)]
                    atoms_js.append(f"{{x:{i}, y:{j}, z:{k}, color:'{comp[sym]['d']['col']}'}}")
        
        # --- THE DEEP-RENDER FIX ---
        # 1. We define the height in the STYLE.
        # 2. We use a "setTimeout" loop to ensure the viewer starts only when the width is > 0.
        html_3d = f"""
        <div id="container_3d" style="height: 500px; width: 100%; min-width: 400px; background-color: #0b0e14; border: 1px solid #30363d; border-radius: 8px;"></div>
        
        <script src="https://3dmol.org/build/3Dmol-min.js"></script>
        
        <script>
            let viewer = null;
            function render() {{
                const element = document.getElementById('container_3d');
                
                // CRITICAL: Don't start if the window hasn't assigned pixels yet
                if (element.offsetWidth <= 0) {{
                    setTimeout(render, 100);
                    return;
                }}

                if (typeof $3Dmol === 'undefined') {{
                    setTimeout(render, 100);
                    return;
                }}

                // Force creation with physical dimensions
                viewer = $3Dmol.createViewer(element, {{ backgroundColor: '#0b0e14' }});
                
                const atoms = {atoms_js};
                atoms.forEach(a => {{
                    viewer.addSphere({{center:{{x:a.x, y:a.y, z:a.z}}, radius:1.4, color:a.color}});
                }});

                viewer.addIsosurface(null, {{
                    isoval: {iso_val},
                    color: '{b_col}',
                    opacity: 0.3
                }});

                viewer.zoomTo();
                viewer.render();
                
                // Second pass to ensure everything is centered
                setTimeout(() => {{ 
                    viewer.resize(); 
                    viewer.render(); 
                }}, 200);
            }}

            window.onload = render;
            // Fallback for Streamlit re-renders
            setTimeout(render, 500);
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
        
        st.dataframe(pd.DataFrame([{"Sym": k, "χ": v['d']['chi']} for k, v in comp.items()]), hide_index=True, use_container_width=True)

else:
    st.error("Invalid formula. Use standard symbols (e.g., TiO2, GaAs).")
