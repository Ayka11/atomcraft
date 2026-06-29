import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re
import streamlit.components.v1 as components

# ==========================================
# 1. ROBUST INTERNAL DATABASE
# ==========================================
@st.cache_data
def get_el_data(symbol):
    DB = {
        "H": [2.20, 0.37, "#FFFFFF"], "He": [0.00, 0.32, "#D9FFFF"],
        "Li": [0.98, 1.34, "#CC80FF"], "Be": [1.57, 0.90, "#C2FF00"],
        "B": [2.04, 0.82, "#FFB5B5"], "C": [2.55, 0.77, "#909090"],
        "N": [3.04, 0.75, "#3050F8"], "O": [3.44, 0.73, "#FF0D0D"],
        "F": [3.98, 0.71, "#90E050"], "Na": [0.93, 1.54, "#AB5CF2"],
        "Mg": [1.31, 1.30, "#8AFF00"], "Al": [1.61, 1.18, "#BFA6A6"],
        "Si": [1.90, 1.11, "#F0C8A0"], "P": [2.19, 1.06, "#FF8000"],
        "S": [2.58, 1.02, "#FFFF30"], "Cl": [3.16, 0.99, "#1FF01F"],
        "K": [0.82, 1.96, "#8F40D4"], "Ca": [1.00, 1.74, "#3DFF00"],
        "Ti": [1.54, 1.36, "#BFC2C7"], "Cr": [1.66, 1.28, "#8500FF"],
        "Fe": [1.83, 1.25, "#E06633"], "Ni": [1.91, 1.21, "#50D050"],
        "Cu": [1.90, 1.28, "#C88033"], "Zn": [1.65, 1.31, "#7D80B0"],
        "Ga": [1.81, 1.26, "#C38E8E"], "As": [2.18, 1.19, "#BD80E3"],
        "Ag": [1.93, 1.44, "#C0C0C0"], "Au": [2.54, 1.44, "#FFD123"]
    }
    symbol = symbol.capitalize()
    return DB.get(symbol, [2.0, 1.0, "#757575"])

def parse_formula(formula):
    if formula.islower():
        formula = re.sub(r'([a-z])([a-z]?)', lambda x: x.group(0).capitalize(), formula)
    matches = re.findall(r'([A-Z][a-z]*)(\d*)', formula)
    parsed = {}
    for sym, count in matches:
        d = get_el_data(sym)
        parsed[sym] = {"n": int(count) if count else 1, "chi": d[0], "rad": d[1], "col": d[2]}
    return parsed

# ==========================================
# 2. UI LAYOUT
# ==========================================
st.set_page_config(page_title="AtomCraft Pro v3.2", layout="wide")
st.markdown("<style>.main { background: #0d1117; color: white; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v3.2")
    user_input = st.text_input("Chemical Formula", value="NaCl")
    iso_val = st.slider("Electron Cloud Density", 0.01, 0.50, 0.15)
    st.info("Engine: WebGL Hyper-Stable Bootstrap")

# ==========================================
# 3. COMPUTATION
# ==========================================
comp = parse_formula(user_input)

if comp:
    v_list = list(comp.values())
    total_n = sum(v['n'] for v in v_list)
    all_chi = [v['chi'] for v in v_list]
    delta_chi = max(all_chi) - min(all_chi)
    avg_chi = sum(v['chi'] * v['n'] for v in v_list) / total_n
    
    # Classification
    if delta_chi > 1.7: b_type, b_col = "Ionic", "#ff4b4b"
    elif avg_chi < 1.9 and delta_chi < 1.0: b_type, b_col = "Metallic", "#58a6ff"
    else: b_type, b_col = "Covalent", "#3fb950"

    col_v, col_m = st.columns([2, 1])

    with col_v:
        st.subheader(f"3D Visualizer: {user_input}")
        
        # Build XYZ string
        els = list(comp.keys())
        xyz_lines = ["8", "AtomCraft_v3.2"]
        idx = 0
        for x in [0, 5]:
            for y in [0, 5]:
                for z in [0, 5]:
                    sym = els[idx % len(els)]
                    xyz_lines.append(f"{sym} {x} {y} {z}")
                    idx += 1
        xyz_string = "\\n".join(xyz_lines)
        
        # --- THE HYPER-STABLE BOOTSTRAP ---
        # 1. Load jQuery (Dependency for 3Dmol)
        # 2. Use `setInterval` with a counter to ensure width is detected
        html_3d = f"""
        <div id="container_3d" style="height: 500px; width: 100%; background-color: #0b0e14; border-radius: 10px;"></div>
        <script src="https://code.jquery.com/jquery-3.6.3.min.js"></script>
        <script src="https://unpkg.com/3dmol@2.0.1/build/3Dmol-min.js"></script>
        <script>
            let attempts = 0;
            function runViewer() {{
                const div = $('#container_3d');
                // Check if library is loaded and div has width
                if (typeof $3Dmol === 'undefined' || div.width() <= 0) {{
                    attempts++;
                    if(attempts < 50) setTimeout(runViewer, 100);
                    return;
                }}
                
                try {{
                    const viewer = $3Dmol.createViewer(div, {{ backgroundColor: '#0b0e14' }});
                    const data = `{xyz_string}`;
                    
                    viewer.addModel(data, "xyz");
                    viewer.setStyle({{}}, {{sphere: {{radius: 1.5}}}});
                    viewer.addIsosurface(null, {{
                        isoval: {iso_val},
                        color: '{b_col}',
                        opacity: 0.35
                    }});
                    
                    viewer.zoomTo();
                    viewer.render();
                    
                    // Force a resize check after a split second
                    setTimeout(() => {{ viewer.resize(); viewer.render(); }}, 200);
                }} catch (err) {{
                    div.html('<p style="color:red">Error: ' + err.message + '</p>');
                }}
            }}
            $(document).ready(runViewer);
        </script>
        """
        components.html(html_3d, height=520)

    with col_m:
        st.subheader("Analytics")
        st.metric("Bond Character", b_type)
        
        bg = max(0, (delta_chi * 2.1) - 0.4) if b_type != "Metallic" else 0
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = bg,
            title = {'text': "Band Gap (eV)"},
            gauge = {'axis': {'range': [0, 10]}, 'bar': {'color': b_col}}
        ))
        fig.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=50,b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        st.table(pd.DataFrame([{"Element": k, "χ": v['chi']} for k, v in comp.items()]))
else:
    st.error("Invalid formula.")
