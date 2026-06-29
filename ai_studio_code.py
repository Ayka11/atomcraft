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
    st.title("🔬 AtomCraft v2.4")
    user_input = st.text_input("Formula", value="NaCl")
    iso_val = st.slider("Electron Cloud Density", 0.01, 0.50, 0.15)
    st.info("System Status: Bootstrapping WebGL Visualizer...")

# --- 3. PROCESSING ---
comp = smart_parse(user_input)

if comp:
    total = sum(v['n'] for v in comp.values())
    chis = [v['d']['chi'] for v in comp.values()]
    delta_chi = max(chis) - min(chis)
    avg_chi = sum(v['d']['chi'] * v['n'] for v in comp.values()) / total
    
    if delta_chi > 1.7: b_type, b_col = "Ionic", "#ff4b4b"
    elif avg_chi < 1.9 and delta_chi < 0.8: b_type, b_col = "Metallic", "#58a6ff"
    else: b_type, b_col = "Covalent", "#3fb950"

    col_v, col_m = st.columns([2, 1])

    with col_v:
        st.subheader(f"Structure: {user_input}")
        
        # Build Lattice Data
        atoms_js = []
        els = list(comp.keys())
        for i in [0, 5]:
            for j in [0, 5]:
                for k in [0, 5]:
                    sym = els[(i+j+k)//5 % len(els)]
                    atoms_js.append(f"{{x:{i}, y:{j}, z:{k}, color:'{comp[sym]['d']['col']}'}}")
        
        # --- BULLETPROOF HTML ---
        html_3d = f"""
        <div id="loading" style="color: #58a6ff; font-family: sans-serif; padding: 20px;">Initializing WebGL...</div>
        <div id="container" style="height: 500px; width: 100%; position: relative; display:none;"></div>
        
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://unpkg.com/3dmol@2.0.1/build/3Dmol-min.js"></script>
        
        <script>
        $(document).ready(function() {{
            let checkExist = setInterval(function() {{
                if (typeof $3Dmol !== 'undefined' && $('#container').width() > 0) {{
                    clearInterval(checkExist);
                    renderModel();
                }}
            }}, 100);

            function renderModel() {{
                $('#loading').hide();
                $('#container').show();
                
                try {{
                    let element = $('#container');
                    let viewer = $3Dmol.createViewer(element, {{ backgroundColor: '#0b0e14' }});
                    let atoms = {atoms_js};
                    
                    atoms.forEach(a => {{
                        viewer.addSphere({{center:{{x:a.x, y:a.y, z:a.z}}, radius:1.5, color:a.color}});
                    }});
                    
                    viewer.addIsosurface(null, {{
                        isoval: {iso_val}, 
                        color: '{b_col}', 
                        opacity: 0.35
                    }});
                    
                    viewer.zoomTo();
                    viewer.render();
                    
                    // Trigger a second render after 500ms to ensure correct sizing
                    setTimeout(() => {{ viewer.resize(); viewer.render(); }}, 500);
                }} catch (err) {{
                    $('#loading').show().text("Error: " + err.message);
                }}
            }}
        }});
        </script>
        """
        components.html(html_3d, height=520)

    with col_m:
        st.subheader("Metrics")
        st.write(f"**Bonding:** <span style='color:{b_col}; font-weight:bold; font-size:24px;'>{b_type}</span>", unsafe_allow_html=True)
        
        bg = max(0, (delta_chi * 2.1) - 0.4) if b_type != "Metallic" else 0
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = bg,
            title = {'text': "Band Gap (eV)"},
            gauge = {'axis': {'range': [0, 10]}, 'bar': {'color': b_col}}
        ))
        fig.update_layout(height=250, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(l=30,r=30,t=40,b=20))
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(pd.DataFrame([{"Element": k, "χ (Pauling)": v['d']['chi']} for k, v in comp.items()]), hide_index=True)

else:
    st.error("Invalid formula. Please use standard notation like NaCl, h2o, or TiO2.")
