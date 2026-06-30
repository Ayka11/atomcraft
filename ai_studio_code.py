"""
AtomCraft v4.1 — Streamlit UI entry point.

This is the file to point Streamlit Cloud (or `streamlit run`) at. All
chemistry logic, 3D geometry construction, and the PubChem live-lookup
integration live in atomcraft_engine.py, imported below — this file is
just page config, sidebar widgets, and layout.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from atomcraft_engine import (
    parse_formula, van_arkel_analysis, estimate_band_gap, estimate_mechanical,
    estimate_melting, is_molecule_heuristic, compute_ionic_fraction,
    build_geometry, build_radius_map, build_density_atoms, build_species_layout,
    render_3dmol_html, CATEGORY_COLORS,
    parse_equation, check_atom_balance, compute_reaction_thermo,
    combined_composition, bonding_color_for,
    estimate_side_solvation_energy,
    pubchem_lookup, geom_comp_from_atoms, get_el_data,
)

# 5. APP CONFIGURATION & THEME
# ==========================================
st.set_page_config(page_title="AtomCraft v4.1", layout="wide")
st.markdown("""
<style>
/* Base app background + default text color */
html, body, .main, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #0d1117 !important;
    color: #e6edf3 !important;
}
[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }

/* Headings / body text everywhere */
h1, h2, h3, h4, h5, h6 { color: #f0f6fc !important; }
.main p, .main span, .main label, .main li { color: #c9d1d9; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #11161d !important;
    border-right: 1px solid #21262d;
}
section[data-testid="stSidebar"] * { color: #e6edf3 !important; }
section[data-testid="stSidebar"] input {
    background-color: #0d1117 !important;
    color: #f0f6fc !important;
    border: 1px solid #30363d !important;
}

/* Captions */
[data-testid="stCaptionContainer"], .main small { color: #9aa4b2 !important; }

/* Widget labels */
[data-testid="stWidgetLabel"] p { color: #c9d1d9 !important; font-weight: 500; }

/* st.info / st.warning / st.error / st.success boxes */
[data-testid="stAlert"] * { color: #e6edf3 !important; }

/* Metric cards */
div[data-testid="stMetric"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 10px; padding: 12px;
}
[data-testid="stMetricLabel"] p { color: #8b949e !important; }
div[data-testid="stMetricValue"] {
    color: #f0f6fc !important;
    font-size: 1.25rem !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    line-height: 1.25 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] p { color: #8b949e !important; }
.stTabs [aria-selected="true"] p { color: #f0f6fc !important; }

/* Dataframe */
[data-testid="stDataFrame"] { color: #e6edf3 !important; }

/* Radio (mode toggle) styled closer to a segmented control */
div[role="radiogroup"] { gap: 4px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🔬 AtomCraft v4.1")
    st.caption("Universal Nano-Material Property Designer")
    mode = st.radio(
        "Mode",
        ["Material Property Inspector", "Reaction Design Dashboard"],
        help="Inspector analyzes one formula's bonding/structure. Dashboard "
             "analyzes a full reaction's thermodynamics and synthesis path."
    )
    st.markdown("---")

    if mode == "Material Property Inspector":
        user_input = st.text_input("Chemical Formula", value="AuCl")
        data_source = st.radio(
            "Data Source", ["Universal Heuristic", "Live Lookup (PubChem)"],
            help="Universal Heuristic: this app's own periodic-table-driven "
                 "engine — works for any formula, always available. Live "
                 "Lookup: fetches the real molecular structure (and MW, "
                 "SMILES, IUPAC name) from PubChem's free public database "
                 "for organic/molecular compounds. Bonding-character "
                 "analysis (χ, band gap, mechanical traits) still comes "
                 "from the heuristic engine either way — PubChem doesn't "
                 "supply that. Falls back to Universal Heuristic "
                 "automatically if the compound isn't found."
        )
    else:
        eqn_input = st.text_input(
            "Chemical Equation", value="Ti + O2 -> TiO2",
            help="Use '+' between species and '->' to separate reactants "
                 "from products, e.g. '2H2 + O2 -> 2H2O'. Coefficients are "
                 "used as typed — equations are not auto-balanced."
        )

    iso_val = st.slider(
        "Electron Cloud Density", 0.01, 0.50, 0.12,
        help="Isosurface threshold for a synthetic electron-density cloud "
             "built from each atom's valence-electron count and radius "
             "(no real DFT data in heuristic mode). Higher = surface "
             "contracts toward dense atom cores. Lower = surface expands "
             "into a larger diffuse cloud."
    )

    if mode == "Material Property Inspector":
        st.info("Universal Prediction Mode — heuristic van Arkel–Ketelaar engine\n\n(element-accurate sphere sizing)")
    else:
        st.info("Reaction Design Dashboard — heuristic ΔH/ΔS/ΔG engine\n\n(known-compound lookup + bonding-based fallback)")

# ==========================================
# 6A. MATERIAL PROPERTY INSPECTOR
# ==========================================
if mode == "Material Property Inspector":
    comp = parse_formula(user_input)

    if comp:
        v_list = list(comp.values())
        total_n = sum(v['n'] for v in v_list)
        all_chi = [v['chi'] for v in v_list]
        delta_chi = max(all_chi) - min(all_chi)
        avg_chi = sum(v['chi'] * v['n'] for v in v_list) / total_n
        avg_rad = sum(v['rad'] * v['n'] for v in v_list) / total_n

        analysis = van_arkel_analysis(avg_chi, delta_chi, symbols=list(comp.keys()))
        b_type = analysis["category"]
        b_col = CATEGORY_COLORS[b_type]

        bg = estimate_band_gap(b_type, delta_chi)
        mech = estimate_mechanical(analysis, avg_rad)
        is_molecule = is_molecule_heuristic(comp)
        melt_is_molecule = is_molecule and b_type == "Polar Covalent"
        melt_label, melt_desc = estimate_melting(b_type, melt_is_molecule)

        live_result = None
        if data_source == "Live Lookup (PubChem)":
            with st.spinner(f"Looking up '{user_input}' on PubChem..."):
                live_result = pubchem_lookup(user_input)
            if not live_result["success"]:
                st.warning(f"⚠️ Live lookup failed: {live_result['error']} Falling back to Universal Heuristic geometry for visualization.")

        live_atoms = None
        geom_source_note = None
        if live_result and live_result["success"]:
            if live_result["atoms_3d"]:
                live_atoms = live_result["atoms_3d"]
                geom_source_note = f"real PubChem 3D conformer, CID {live_result['cid']}"
            elif live_result["atoms_2d"]:
                live_atoms = live_result["atoms_2d"]
                geom_source_note = f"real PubChem 2D structure (no 3D conformer available), CID {live_result['cid']}"
            elif live_result["cid"]:
                st.info(f"PubChem matched CID {live_result['cid']} with no downloadable structure — using heuristic geometry, but real properties are shown below.")

        c1, c2 = st.columns([2, 1])

        with c1:
            st.subheader(f"Molecular Lattice: {user_input}")
            if live_atoms:
                atom_lines = [f"{sym} {x:.3f} {y:.3f} {z:.3f}" for sym, x, y, z in live_atoms]
                total_atoms = rendered_n = len(atom_lines)
                geom_comp = geom_comp_from_atoms(live_atoms)
                st.caption(f"✅ Using {geom_source_note}.")
            else:
                atom_lines, total_atoms, rendered_n, _ = build_geometry(comp)
                geom_comp = comp
                if rendered_n < total_atoms:
                    st.caption(f"⚠️ Rendering {rendered_n} of {total_atoms} atoms for performance/clarity.")
            xyz = f"{len(atom_lines)}\nAtomCraft v4.1\n" + "\n".join(atom_lines)
            radius_map = build_radius_map(geom_comp)
            density_atoms = build_density_atoms(atom_lines, geom_comp)
            html_3d = render_3dmol_html("viewerMain", xyz, radius_map, density_atoms, b_col, iso_val, height=520)
            st.iframe(html_3d, height=520)

        with c2:
            st.subheader("Analysis")
            m1, m2 = st.columns(2)
            m1.metric("Mean χ", f"{avg_chi:.2f}")
            m2.metric("Δχ", f"{delta_chi:.2f}")
            m3, m4 = st.columns(2)
            m3.metric("Avg Radius", f"{avg_rad:.2f} Å")
            m4.metric("Bond Type", b_type)

            tab_names = ["Bonding", "Band Structure", "Mechanical", "Composition"]
            if live_result and live_result["success"]:
                tab_names.append("Live Data")
            tabs = st.tabs(tab_names)
            tab_bond, tab_band, tab_mech, tab_comp = tabs[:4]
            tab_live = tabs[4] if len(tabs) > 4 else None

            with tab_bond:
                corners = analysis["corners"]
                xs = [corners["Metallic"][0], corners["Covalent"][0], corners["Ionic"][0], corners["Metallic"][0]]
                ys = [corners["Metallic"][1], corners["Covalent"][1], corners["Ionic"][1], corners["Metallic"][1]]
                fig_tri = go.Figure()
                fig_tri.add_trace(go.Scatter(x=xs, y=ys, mode="lines",
                                              line=dict(color="#444", width=1), showlegend=False))
                for label, (cx, cy) in corners.items():
                    fig_tri.add_trace(go.Scatter(x=[cx], y=[cy], mode="markers+text", text=[label],
                                                  textposition="bottom center", textfont=dict(color="#aab4c0"),
                                                  marker=dict(size=6, color="#666"), showlegend=False))
                fig_tri.add_trace(go.Scatter(x=[avg_chi], y=[delta_chi], mode="markers",
                                              marker=dict(size=16, color=b_col, line=dict(width=2, color="white")),
                                              showlegend=False))
                fig_tri.update_layout(
                    height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e6edf3"), margin=dict(t=20, b=20, l=20, r=20),
                    xaxis=dict(title="Mean χ", range=[0.5, 3.2], gridcolor="#21262d", tickfont=dict(color="#e6edf3")),
                    yaxis=dict(title="Δχ (ionic axis)", range=[-0.3, 3.6], gridcolor="#21262d", tickfont=dict(color="#e6edf3")),
                )
                st.plotly_chart(fig_tri, theme=None)
                st.caption(
                    f"Metallic {analysis['metallic_pct']:.0f}% · Covalent {analysis['covalent_pct']:.0f}% · "
                    f"Ionic {analysis['ionic_pct']:.0f}% (Pauling ionic character: {analysis['ionic_character']:.0f}%)"
                )
                st.markdown(f"**Estimated melting profile: {melt_label}**")
                st.caption(melt_desc)

            with tab_band:
                fig_band = go.Figure()
                if b_type == "Metallic" or bg <= 0.05:
                    fig_band.add_shape(type="rect", x0=0, x1=1, y0=-2, y1=1,
                                        fillcolor=b_col, opacity=0.5, line=dict(width=0))
                    fig_band.add_annotation(x=0.5, y=-0.5, text="Overlapping Bands<br>(Conductor)",
                                             showarrow=False, font=dict(color="white"))
                    y_range = [-2.5, 2]
                else:
                    fig_band.add_shape(type="rect", x0=0, x1=1, y0=-2, y1=0,
                                        fillcolor="#58a6ff", opacity=0.6, line=dict(width=0))
                    fig_band.add_shape(type="rect", x0=0, x1=1, y0=bg, y1=bg + 2,
                                        fillcolor="#ff8000", opacity=0.6, line=dict(width=0))
                    fig_band.add_annotation(x=0.5, y=-1, text="Valence Band", showarrow=False, font=dict(color="white"))
                    fig_band.add_annotation(x=0.5, y=bg + 1, text="Conduction Band", showarrow=False, font=dict(color="white"))
                    fig_band.add_annotation(x=1.25, y=bg / 2, text=f"Eg = {bg:.2f} eV",
                                             showarrow=False, font=dict(color=b_col, size=14))
                    y_range = [-2.5, max(bg + 2.5, 3)]
                fig_band.update_layout(
                    height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e6edf3"),
                    xaxis=dict(visible=False, range=[-0.3, 1.7]),
                    yaxis=dict(title="Energy (eV, relative)", range=y_range, gridcolor="#21262d",
                               color="#e6edf3", tickfont=dict(color="#e6edf3")),
                    margin=dict(t=20, b=20, l=10, r=10), showlegend=False,
                )
                st.plotly_chart(fig_band, theme=None)
                gap_label = ("Conductor" if (b_type == "Metallic" or bg <= 0.05)
                             else "Semiconductor" if bg <= 3.0 else "Insulator")
                st.caption(f"Classification: **{gap_label}** (Eg ≈ {bg:.2f} eV)")

            with tab_mech:
                cats = list(mech.keys())
                vals = list(mech.values())
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=vals + [vals[0]], theta=cats + [cats[0]], fill="toself",
                    line=dict(color=b_col), fillcolor=b_col, opacity=0.5,
                ))
                fig_radar.update_layout(
                    polar=dict(bgcolor="rgba(0,0,0,0)",
                               radialaxis=dict(visible=True, range=[0, 100], color="#e6edf3",
                                                gridcolor="#21262d", tickfont=dict(color="#e6edf3")),
                               angularaxis=dict(color="#e6edf3", tickfont=dict(color="#e6edf3"))),
                    showlegend=False, paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e6edf3"),
                    height=320, margin=dict(t=30, b=30, l=30, r=30),
                )
                st.plotly_chart(fig_radar, theme=None)
                st.caption("Heuristic engineering-trait estimate — not a substitute for measured elastic-tensor data.")

            with tab_comp:
                rows = []
                for k, v in comp.items():
                    rows.append({
                        "Sym": k, "n": v["n"], "χ": v["chi"], "Radius (Å)": v["rad"],
                        "Group": v["group"], "Block": v["block"], "Valence e⁻": v["valence"],
                    })
                st.dataframe(pd.DataFrame(rows), hide_index=True)

            if tab_live is not None:
                with tab_live:
                    lr = live_result
                    rows = [
                        {"Property": "PubChem CID", "Value": lr["cid"]},
                        {"Property": "Molecular Formula", "Value": lr["molecular_formula"]},
                        {"Property": "Molecular Weight", "Value": f"{lr['molecular_weight']} g/mol" if lr["molecular_weight"] else None},
                        {"Property": "Canonical SMILES", "Value": lr["canonical_smiles"]},
                        {"Property": "IUPAC Name", "Value": lr["iupac_name"]},
                        {"Property": "XLogP", "Value": lr["xlogp"]},
                        {"Property": "TPSA", "Value": f"{lr['tpsa']} Å²" if lr["tpsa"] else None},
                        {"Property": "Geometry source", "Value": geom_source_note or "none available (heuristic used)"},
                    ]
                    st.dataframe(pd.DataFrame(rows), hide_index=True)
                    if lr["cid"]:
                        st.caption(f"[View full PubChem record →](https://pubchem.ncbi.nlm.nih.gov/compound/{lr['cid']})")
                    st.caption(
                        "Real structure/identity data from PubChem PUG REST (free, no API key). "
                        "Bonding-character analysis (χ, band gap, mechanical traits) above still "
                        "comes from this app's own heuristic engine — PubChem doesn't supply that."
                    )
    else:
        st.error("Invalid Formula")

# ==========================================
# 6B. REACTION DESIGN DASHBOARD
# ==========================================
else:
    reactants, products, err = parse_equation(eqn_input)

    if reactants is None:
        st.error(f"{err} Use the format: '2H2 + O2 -> 2H2O'")
    else:
        if err:
            st.warning(err)
        rc, pc, balanced = check_atom_balance(reactants, products)
        if not balanced:
            st.warning(
                f"⚠️ Equation may not be atom-balanced — Reactant atoms: {dict(rc)} "
                f"vs Product atoms: {dict(pc)}. Calculations below still use the "
                f"coefficients exactly as typed."
            )

        # Computed once up front since both Controls (ΔG/solvation) and
        # Visualization (bonding-color tint) need the per-side composition.
        reactant_comp = combined_composition(reactants)
        product_comp = combined_composition(products)

        c_ctrl, c_viz, c_therm = st.columns([1, 1.6, 1.2])

        with c_ctrl:
            st.subheader("Reaction Controls")
            temp = st.slider("Temperature (K)", 100, 3000, 298,
                              help="Used in ΔG = ΔH - TΔS. Also visually blurs the "
                                   "electron-cloud isosurface in the 3D viewports — "
                                   "real atomic vibration amplitude grows with √T "
                                   "(the same effect behind crystallography's "
                                   "temperature-dependent B-factors). No change at "
                                   "298K (the default).")
            pressure = st.slider(
                "Pressure (atm)", 1, 500, 1,
                help="Changes ΔG when the reaction's gas-phase mole count differs "
                     "between products and reactants (Δn_gas ≠ 0), via "
                     "ΔG_pressure = Δn_gas · R · T · ln(P). Also visually compresses "
                     "the spacing BETWEEN separate species in the 3D viewports "
                     "(real gas compression, PV=nRT) — bond lengths within a single "
                     "species aren't compressed, since that effect is genuinely "
                     "imperceptible below GPa-scale pressures. No change at 1 atm."
            )

            st.markdown("**Reaction Environment**")
            epsilon = st.slider(
                "Solvent Polarity — Dielectric Constant (ε)", 1.0, 80.0, 1.0, step=1.0,
                help="Models ionization/dissociation via the Born solvation "
                     "equation: a polar medium stabilizes the more "
                     "ionic/charge-separated side of the reaction more than "
                     "the other, shifting ΔG accordingly. Reference points: "
                     "vacuum/gas-phase ε=1 (no effect, this is the default), "
                     "hexane ε≈2, ethanol ε≈24, water ε≈80."
            )
            catalyst = st.checkbox(
                "Catalyst Present", value=False,
                help="A catalyst lowers the activation-energy barrier "
                     "(reaction coordinate hump) WITHOUT changing ΔH, ΔS, "
                     "or ΔG — catalysts affect kinetics, not thermodynamics. "
                     "This only changes the Energy Profile chart, not the "
                     "ΔG/spontaneity verdict below."
            )

            thermo = compute_reaction_thermo(reactants, products, temp, pressure)
            solv_react = estimate_side_solvation_energy(reactants, epsilon)
            solv_prod = estimate_side_solvation_energy(products, epsilon)
            solv_correction = solv_prod - solv_react
            delta_g_total = thermo["delta_g"] + solv_correction
            spontaneous_total = delta_g_total < 0

            st.metric("ΔH (reaction)", f"{thermo['delta_h']:.1f} kJ/mol")
            st.metric("ΔS (reaction)", f"{thermo['delta_s_j']:.1f} J/mol·K")
            st.metric(f"ΔG @ {temp} K, {pressure} atm, ε={epsilon:.0f}", f"{delta_g_total:.1f} kJ/mol")
            if abs(solv_correction) > 0.5:
                st.caption(
                    f"ΔG breakdown: {thermo['delta_g']:.1f} (gas-phase) "
                    f"{'+' if solv_correction >= 0 else '−'} {abs(solv_correction):.1f} "
                    f"(solvation/ionization) = {delta_g_total:.1f} kJ/mol"
                )

            if spontaneous_total:
                st.success("✅ Spontaneous (ΔG < 0) at these conditions")
            else:
                st.error("❌ Non-spontaneous (ΔG > 0) at these conditions")

            reaction_type = "Exothermic (Heat Releasing)" if thermo["delta_h"] < 0 else "Endothermic (Requires Energy Input)"
            st.markdown(f"**{reaction_type}**")

            if abs(thermo["delta_n_gas"]) > 1e-9:
                direction = "raises" if thermo["pressure_term"] > 0 else "lowers"
                st.caption(
                    f"Δn(gas) = {thermo['delta_n_gas']:+.1f} mol → pressure {direction} "
                    f"ΔG by {abs(thermo['pressure_term']):.1f} kJ/mol at {pressure} atm."
                )
            else:
                st.caption("No net change in gas-phase moles — pressure has negligible effect on this reaction's ΔG.")

            with st.expander("Per-species thermodynamic data"):
                rows = []
                for r in reactants:
                    rows.append({"Role": "Reactant", "Species": f"{r['coeff']}{r['formula']}",
                                 "ΔHf (kJ/mol)": round(r["hf"], 1), "S° (J/mol·K)": round(r["s"], 1),
                                 "Phase (guess)": r["phase"], "Source": r["hf_source"]})
                for p in products:
                    rows.append({"Role": "Product", "Species": f"{p['coeff']}{p['formula']}",
                                 "ΔHf (kJ/mol)": round(p["hf"], 1), "S° (J/mol·K)": round(p["s"], 1),
                                 "Phase (guess)": p["phase"], "Source": p["hf_source"]})
                st.dataframe(pd.DataFrame(rows), hide_index=True)
                st.caption("ΔHf/S° are reference-table values where available, otherwise a transparent "
                           "bonding-character/phase heuristic — not DFT-grade thermochemistry. Solvation "
                           "uses a heuristic charge proxy, not real oxidation-state analysis.")

        with c_viz:
            st.subheader("Synthesis Pipeline")
            v1, v2 = st.columns(2)

            # BUG FIXED: previously both viewports rendered
            # combined_composition(...) — merging every species on a side
            # into one atom-count blob. For a balanced equation, reactant
            # and product atom counts are IDENTICAL by definition, so the
            # two viewports were mathematically guaranteed to look the
            # same. Each species is now laid out as its own separated
            # cluster (see build_species_layout), so 'Ti + O2' visibly
            # reads as two distinct unbonded species, while 'TiO2' visibly
            # reads as one bonded structure.
            r_col, r_analysis = bonding_color_for(reactant_comp)
            p_col, p_analysis = bonding_color_for(product_comp)

            with v1:
                st.caption("Reactant State — " + ", ".join(f"{r['coeff']}{r['formula']}" for r in reactants))
                (r_atom_lines, r_total, r_rendered, r_display_comp, r_trunc,
                 r_density_atoms) = build_species_layout(reactants, epsilon=epsilon, temp_k=temp, pressure_atm=pressure)
                if r_rendered < r_total:
                    st.caption(f"⚠️ Rendering {r_rendered} of {r_total} atoms.")
                if r_trunc:
                    st.caption("⚠️ Showing first 6 species only.")
                r_xyz = f"{len(r_atom_lines)}\nReactants\n" + "\n".join(r_atom_lines)
                r_radius_map = build_radius_map(r_display_comp)
                r_html = render_3dmol_html("viewerReact", r_xyz, r_radius_map, r_density_atoms, r_col, iso_val, height=320)
                st.iframe(r_html, height=320)

            with v2:
                st.caption("Product State — " + ", ".join(f"{p['coeff']}{p['formula']}" for p in products))
                (p_atom_lines, p_total, p_rendered, p_display_comp, p_trunc,
                 p_density_atoms) = build_species_layout(products, epsilon=epsilon, temp_k=temp, pressure_atm=pressure)
                if p_rendered < p_total:
                    st.caption(f"⚠️ Rendering {p_rendered} of {p_total} atoms.")
                if p_trunc:
                    st.caption("⚠️ Showing first 6 species only.")
                p_xyz = f"{len(p_atom_lines)}\nProducts\n" + "\n".join(p_atom_lines)
                p_radius_map = build_radius_map(p_display_comp)
                p_html = render_3dmol_html("viewerProd", p_xyz, p_radius_map, p_density_atoms, p_col, iso_val, height=320)
                st.iframe(p_html, height=320)

        with c_therm:
            st.subheader("Energy Profile")
            delta_h = thermo["delta_h"]
            # TS hump height is a qualitative heuristic (scales with |ΔH|,
            # never the actual computed activation barrier), but is now
            # GUARANTEED to sit above both endpoints regardless of how large
            # or positive delta_h is, fixing a case the original draft's
            # simpler 'act_energy = abs(delta_h)*0.3+100' formula could miss
            # for strongly endothermic reactions (TS could end up BELOW the
            # product energy, breaking the visual "hump"). A present
            # catalyst lowers this barrier (kinetics only) without touching
            # delta_h/delta_g, matching real catalyst behavior.
            act_energy_height = max(40.0, abs(delta_h) * 0.25)
            if catalyst:
                act_energy_height *= 0.35
            ts_y = max(0.0, delta_h) + act_energy_height
            x_vals = [0, 1, 2]
            y_vals = [0, ts_y, delta_h]
            curve_color = "#3fb950" if spontaneous_total else "#ff4b4b"

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_vals, y=y_vals, mode="lines+markers", line_shape="spline",
                line=dict(color=curve_color, width=4), marker=dict(size=8, color=curve_color),
            ))
            fig.update_layout(
                title=f"Reaction Coordinate — {reaction_type.split(' (')[0]}"
                      + (" (catalyzed)" if catalyst else ""),
                xaxis=dict(title="Reaction Progress", showticklabels=False, gridcolor="#21262d"),
                # BUG FIXED: axis was labeled "Free Energy" but the curve is
                # built from delta_h (an enthalpy diagram is also the
                # conventional choice for textbook reaction-coordinate
                # plots); ΔG/spontaneity is reported as a single number in
                # Reaction Controls instead, since it depends on T/P/solvent
                # in ways not meaningful to plot along a reaction-progress axis.
                yaxis=dict(title="Enthalpy (kJ/mol, relative to reactants)", gridcolor="#21262d",
                           tickfont=dict(color="#e6edf3")),
                height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e6edf3"),
                annotations=[
                    dict(x=0, y=0, text="Reactants", showarrow=True, arrowhead=1, font=dict(color="#e6edf3")),
                    dict(x=1, y=ts_y, text="Transition State", showarrow=True, font=dict(color="#e6edf3")),
                    dict(x=2, y=delta_h, text="Products", showarrow=True, font=dict(color="#e6edf3")),
                ],
            )
            st.plotly_chart(fig, theme=None)
            st.caption(
                "Activation-energy hump height is a qualitative heuristic "
                "(scales with |ΔH|, reduced ~65% when a catalyst is present), "
                "not a computed transition-state barrier — swap for a real "
                "NEB/DFT barrier calculation in production. Curve color "
                "reflects overall ΔG-based spontaneity (including solvation)."
            )

st.caption("AtomCraft v4.1 | Universal Nano-Material Property Designer & Reaction Thermodynamics Unit")
