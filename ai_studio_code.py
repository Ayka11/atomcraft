import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components
import re
from mendeleev import element

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

def smart_parse(formula):
    if formula.islower(): formula = formula.capitalize()
    matches = re.findall(r'([A-Z][a-z]*)(\d*)', formula)
    parsed = {}
    for sym, count in matches:
        data = get_el_data(sym)
        parsed[sym] = {"n": int(count) if count else 1, "d": data}
    return parsed

# --- 2. THEME ---
st.set_page_config(page_title="AtomCraft Pro", layout="wide")
st.markdown("<style>.main { background: #0d1117; color: white; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v2.6")
    user_input = st.text_input("Formula", value="NaCl")
    iso_val = st.slider("Electron Cloud Density", 0.01, 0.50, 0.12)
    st.success("Mode: Direct Injection (Force-Render)")

# --- 3. ANALYTICS ---
comp = smart_parse(user_input)
if comp:
    total = sum(v['n'] for v in comp.values())
    chis = [v['d']['chi'] for v in comp.values()]
    delta_chi = max(chis) - min(chis)
    avg_chi = sum(v['d']['chi'] * v['n'] for v in comp.items()) / total
    
    if delta_chi > 1.7: b_type, b_col = "Ionic", "#ff4b4b"
    elif avg_chi < 1.9 and delta_chi < 0.8: b_type, b_col = "Metallic", "#58a6ff"
    else: b_type, b_col = "Covalent", "#3fb950"

    c_viz, c_met = st.columns([2, 1])

    with c_viz:
        st.subheader(f"3D Lattice Visualization: {user_input}")
        
        # Build XYZ string (8 atoms in a cube)
        xyz = f"8\nAtomCraft Output\n"
        els = list(comp.keys())
        idx = 0
        for x in [0, 4]:
            for y in [0, 4]:
                for z in [0, 4]:
                    sym = els[idx % len(els)]
                    xyz += f"{sym} {x} {y} {z}\n"
                    idx += 1
        
        # --- THE FIX: DIRECT JQUERY INJECTION ---
        html_3d = f"""
        <div id="viz_container" style="height: 500px; width: 100%; background-color: #0b0e14; border-radius: 10px;"></div>
        
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://3dmol.org/build/3Dmol-min.js"></script>
        
        <script>
        $(document).ready(function() {{
            // 1. Initialize viewer
            let element = $('#viz_container');
            let viewer = $3Dmol.createViewer(element, {{ backgroundColor: '#0b0e14' }});
            
            // 2. Add the XYZ model
            let data = `{xyz}`;
            viewer.addModel(data, "xyz");
            
            // 3. Set visual styles
            viewer.setStyle({{}}, {{sphere: {{radius: 1.4}}}});
            
            // 4. Add the electron cloud
            viewer.addIsosurface(null, {{
                isoval: {iso_val},
                color: '{b_col}',
                opacity: 0.35
            }});
            
            // 5. Force Zoom and Multi-pass Render
            viewer.zoomTo();
            viewer.render();
            
            // Double-check resize after a brief moment (fixes the "black box" sizing issue)
            setTimeout(function() {{
                viewer.resize();
                viewer.zoomTo();
                viewer.render();
            }}, 200);
        }});
        </script>
        """
        components.html(html_3d, height=520)

    with c_met:
        st.subheader("Property Prediction")
        st.metric("Bond Character", b_type)
        
        bg = max(0, (delta_chi * 2.1) - 0.4) if b_type != "Metallic" else 0
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = bg,
            title = {'text': "Band Gap (eV)"},
            gauge = {'axis': {'range': [0, 10]}, 'bar': {'color': b_col}}
        ))
        fig.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(l=30,r=30,t=50,b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.write("**Local Atom Table**")
        st.dataframe(pd.DataFrame([{"Sym": k, "χ": v['d']['chi'], "Rad": v['d']['rad']} for k, v in comp.items()]), hide_index=True)

else:
    st.error("Invalid input. Please use symbols like 'NaCl', 'TiO2', or 'H2O'.")
