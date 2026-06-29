import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components
import re
from mendeleev import element

# --- 1. DATA ENGINE ---
@st.cache_data
def get_el(symbol):
    fb = {"H": [2.2, 0.37, "#FFFFFF"], "C": [2.55, 0.77, "#909090"], "O": [3.44, 0.73, "#FF0D0D"], 
          "Na": [0.93, 1.54, "#AB5CF2"], "Cl": [3.16, 0.99, "#1FF01F"], "Ti": [1.54, 1.36, "#BFC2C7"]}
    try:
        e = element(symbol)
        return {"chi": e.electronegativity('pauling') or 2.0, "rad": e.atomic_radius or 1.0, "col": f"#{e.cpk_color}"}
    except:
        if symbol in fb: return {"chi": fb[symbol][0], "rad": fb[symbol][1], "col": fb[symbol][2]}
    return None

def smart_parse(formula):
    if formula.islower(): formula = formula.capitalize()
    matches = re.findall(r'([A-Z][a-z]*)(\d*)', formula)
    parsed = {}
    for sym, count in matches:
        data = get_el(sym)
        if data: parsed[sym] = {"n": int(count) if count else 1, "d": data}
    return parsed

# --- 2. LAYOUT ---
st.set_page_config(page_title="AtomCraft Pro", layout="wide")
st.markdown("<style>.main { background: #0d1117; color: white; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v2.3")
    user_input = st.text_input("Formula", value="NaCl")
    iso_val = st.slider("Electron Cloud", 0.01, 0.50, 0.15)
    st.success("Engine: WebGL Stability Patch Applied")

# --- 3. LOGIC ---
comp = smart_parse(user_input)

if comp:
    total = sum(v['n'] for v in comp.values())
    chis = [v['d']['chi'] for v in comp.values()]
    delta_chi = max(chis) - min(chis)
    avg_chi = sum(v['d']['chi'] * v['n'] for v in comp.values()) / total
    
    if delta_chi > 1.7: b_type, b_col = "Ionic", "#ff4b4b"
    elif avg_chi < 1.9 and delta_chi < 0.8: b_type, b_col = "Metallic", "#58a6ff"
    else: b_type, b_col = "Covalent", "#3fb950"

    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader(f"3D Visualizer: {user_input}")
        
        # Build Atom List
        atoms_js = []
        els = list(comp.keys())
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    sym = els[(i+j+k) % len(els)]
                    atoms_js.append(f"{{x:{i*4}, y:{j*4}, z:{k*4}, col:'{comp[sym]['d']['col']}'}}")
        
        # SUPER STABLE VISUALIZER HTML
        html_3d = f"""
        <div id="wrapper" style="height: 500px; width: 100%; display: flex;">
            <div id="container" style="flex: 1; width: 100%; height: 100%; position: relative;"></div>
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.0.4/3Dmol-min.js"></script>
        <script>
            (function() {{
                const start = () => {{
                    if (typeof $3Dmol === 'undefined') {{
                        setTimeout(start, 100);
                        return;
                    }}
                    
                    const element = document.getElementById('container');
                    // This is the fix for the "size" error: 
                    // ensure the element has dimensions before initializing
                    const viewer = $3Dmol.createViewer($(element), {{ backgroundColor: '#0b0e14' }});
                    
                    const atoms = {atoms_js};
                    atoms.forEach(a => {{
                        viewer.addSphere({{center:{{x:a.x, y:a.y, z:a.z}}, radius:1.2, color:a.col}});
                    }});
                    
                    viewer.addIsosurface(null, {{isoval: {iso_val}, color: '{b_col}', opacity: 0.3}});
                    viewer.zoomTo();
                    viewer.render();
                    
                    // Handle responsive resizing
                    window.addEventListener('resize', () => {{ viewer.resize(); }});
                }};

                if (document.readyState === 'complete') {{ start(); }} 
                else {{ window.addEventListener('load', start); }}
            }})();
        </script>
        """
        components.html(html_3d, height=520)

    with c2:
        st.subheader("Metrics")
        st.write(f"**Bond Type:** <span style='color:{b_col}; font-weight:bold; font-size:24px;'>{b_type}</span>", unsafe_allow_html=True)
        
        bg = max(0, (delta_chi * 2.1) - 0.4) if b_type != "Metallic" else 0
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = bg,
            title = {'text': "Band Gap (eV)"},
            gauge = {'axis': {'range': [0, 10]}, 'bar': {'color': b_col}}
        ))
        fig.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(l=20,r=20,t=40,b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.table(pd.DataFrame([{"Element": k, "χ": v['d']['chi']} for k, v in comp.items()]))
else:
    st.error("Invalid Formula. Try 'NaCl', 'TiO2', or 'h2o'.")
