"""
AtomCraft pytest suite.

Run before every deploy:
    pytest test_atomcraft.py -v

Covers two layers:
  1. Pure engine logic (atomcraft_engine.py), imported directly — fast,
     no Streamlit runtime needed.
  2. Full-app smoke tests via Streamlit's AppTest harness, which catches
     the class of bug that pure unit tests CANNOT: every accidental
     function-deletion, every "works in isolation but breaks when wired
     into the UI" bug found during this app's development was only ever
     caught by actually running the full app, not by testing functions
     standalone. Both layers are required, not redundant.

Network note: tests involving PubChem deliberately mock the HTTP layer
(_pubchem_get) rather than hitting the real API — pytest runs should not
depend on network availability or PubChem's uptime. If you want to verify
the REAL live integration, do that manually after deploying.
"""
import importlib
import math
import shutil
import subprocess
import tempfile
import os

import pytest

import atomcraft_engine as eng


# ======================================================================
# 1. Periodic table / element data
# ======================================================================
class TestElementData:
    def test_known_elements_have_full_data(self):
        for sym in ["H", "C", "O", "Na", "Cl", "Ti", "Fe", "Au", "U"]:
            d = eng.get_el_data(sym)
            assert d["chi"] >= 0
            assert d["radius"] > 0
            assert d["color"].startswith("#")
            assert d["valence"] is not None

    def test_unknown_element_falls_back_gracefully(self):
        d = eng.get_el_data("Zz")
        assert d == eng._FALLBACK

    def test_case_insensitive_lookup(self):
        assert eng.get_el_data("na") == eng.get_el_data("Na") == eng.get_el_data("NA")


# ======================================================================
# 2. Formula parsing
# ======================================================================
class TestParseFormula:
    @pytest.mark.parametrize("formula,expected", [
        ("NaCl", {"Na": 1, "Cl": 1}),
        ("nacl", {"Na": 1, "Cl": 1}),
        ("NACL", {"Na": 1, "Cl": 1}),
        ("TiO2", {"Ti": 1, "O": 2}),
        ("H2O", {"H": 2, "O": 1}),
        ("Ca(OH)2", {"Ca": 1, "O": 2, "H": 2}),
        ("Fe2(SO4)3", {"Fe": 2, "S": 3, "O": 12}),
        ("Al2(SO4)3", {"Al": 2, "S": 3, "O": 12}),
        ("CuSO4.5H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}),
        ("CuSO4*5H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}),
        ("CO", {"C": 1, "O": 1}),       # must NOT be read as Cobalt
        ("HF", {"H": 1, "F": 1}),       # must NOT be read as Hafnium
        ("NO", {"N": 1, "O": 1}),       # must NOT be read as Nobelium
        ("Ti6Al4V", {"Ti": 6, "Al": 4, "V": 1}),
        ("GaAs", {"Ga": 1, "As": 1}),
        ("U3O8", {"U": 3, "O": 8}),
    ])
    def test_formula_parsing(self, formula, expected):
        comp = eng.parse_formula(formula)
        actual = {sym: v["n"] for sym, v in comp.items()}
        assert actual == expected, f"{formula} -> {actual}, expected {expected}"

    def test_empty_formula_returns_empty(self):
        assert eng.parse_formula("") == {}

    def test_invalid_chars_dont_crash(self):
        # should not raise, even on garbage input
        eng.parse_formula("!!!not_a_formula###")


# ======================================================================
# 3. Bonding classification (van Arkel–Ketelaar)
# ======================================================================
class TestBondingClassification:
    def _classify(self, formula):
        comp = eng.parse_formula(formula)
        v_list = list(comp.values())
        total_n = sum(v["n"] for v in v_list)
        all_chi = [v["chi"] for v in v_list]
        delta_chi = max(all_chi) - min(all_chi)
        avg_chi = sum(v["chi"] * v["n"] for v in v_list) / total_n
        return eng.van_arkel_analysis(avg_chi, delta_chi, symbols=list(comp.keys()))["category"]

    @pytest.mark.parametrize("formula,expected_category", [
        ("NaCl", "Ionic"),
        ("TiO2", "Ionic"),
        ("Cu", "Metallic"),
        ("Fe", "Metallic"),
        # High-chi metals (W=2.36, Pt=2.28, Au=2.54) must NOT be
        # misclassified as covalent just because raw chi is high —
        # this was a real bug caught during development.
        ("W", "Metallic"),
        ("Pt", "Metallic"),
        ("Au", "Metallic"),
        ("Ti6Al4V", "Metallic"),
    ])
    def test_classification(self, formula, expected_category):
        assert self._classify(formula) == expected_category


# ======================================================================
# 4. Geometry construction
# ======================================================================
class TestBuildGeometry:
    def test_atom_count_matches_formula(self):
        for formula, expected_total in [("H2O", 3), ("CO2", 3), ("NaCl", 2),
                                         ("Ti6Al4V", 11), ("H2CO4", 7)]:
            comp = eng.parse_formula(formula)
            atom_lines, total, rendered, _ = eng.build_geometry(comp)
            assert total == expected_total, f"{formula}: got {total}"
            assert rendered == len(atom_lines)

    def test_single_atom_species(self):
        comp = eng.parse_formula("Fe")
        atom_lines, total, rendered, _ = eng.build_geometry(comp)
        assert total == 1
        assert atom_lines == ["Fe 0.00 0.00 0.00"]

    def test_diatomic_species_realistic_bond_length(self):
        comp = eng.parse_formula("O2")
        atom_lines, total, rendered, is_mol = eng.build_geometry(comp)
        assert total == 2
        assert is_mol is True
        # bond length should be well under the old 2.5A lattice spacing
        xs = [float(l.split()[1]) for l in atom_lines]
        bond_len = max(xs) - min(xs)
        assert 0.5 < bond_len < 2.0

    def test_render_cap_respected(self):
        comp = eng.parse_formula("Ti6Al4V")
        atom_lines, total, rendered, _ = eng.build_geometry(comp, max_render_atoms=5)
        assert rendered == 5
        assert total == 11

    def test_epsilon_stretches_ionic_more_than_covalent(self):
        """The dielectric-constant slider must visibly affect ionic
        compounds' geometry far more than covalent/metallic ones — this
        was a real reported bug (epsilon had zero visual effect) until
        bond/lattice stretch was wired to each compound's own ionic
        character."""
        def bond_len(formula, eps):
            comp = eng.parse_formula(formula)
            lines, *_ = eng.build_geometry(comp, epsilon=eps)
            p0 = [float(x) for x in lines[0].split()[1:]]
            p1 = [float(x) for x in lines[1].split()[1:]]
            return math.dist(p0, p1)

        nacl_ratio = bond_len("NaCl", 80) / bond_len("NaCl", 1)
        gaas_ratio = bond_len("GaAs", 80) / bond_len("GaAs", 1)
        assert nacl_ratio > 1.5, "ionic NaCl should stretch substantially"
        assert gaas_ratio < 1.2, "covalent-network GaAs should barely move"
        assert nacl_ratio > gaas_ratio

    def test_epsilon_default_preserves_baseline(self):
        comp = eng.parse_formula("NaCl")
        lines_default, *_ = eng.build_geometry(comp)  # epsilon defaults to 1.0
        lines_explicit, *_ = eng.build_geometry(comp, epsilon=1.0)
        assert lines_default == lines_explicit


# ======================================================================
# 5. Density atoms — thermal motion & ionization blur
# ======================================================================
class TestDensityAtoms:
    def test_defaults_match_pre_change_baseline(self):
        comp = eng.parse_formula("H2O")
        atoms = eng.build_density_atoms(["O 0.00 0.00 0.00"], comp, temp_k=298.0, epsilon=1.0)
        expected_sigma = max(0.45, comp["O"]["rad"] * 0.55)
        assert atoms[0]["sigma"] == pytest.approx(expected_sigma)

    def test_thermal_blur_grows_with_temperature(self):
        comp = eng.parse_formula("NaCl")
        sigmas = []
        for T in [100, 298, 1000, 3000]:
            atoms = eng.build_density_atoms(["Na 0.00 0.00 0.00"], comp, temp_k=T, epsilon=1.0)
            sigmas.append(atoms[0]["sigma"])
        assert sigmas == sorted(sigmas), "sigma must monotonically increase with T"
        assert sigmas[1] == pytest.approx(max(0.45, comp["Na"]["rad"] * 0.55))  # T=298 baseline

    def test_solvation_blur_grows_with_epsilon_for_ionic_species(self):
        comp = eng.parse_formula("NaCl")
        sigmas = []
        for eps in [1, 2, 24, 80]:
            atoms = eng.build_density_atoms(["Cl 0.00 0.00 0.00"], comp, temp_k=298.0, epsilon=eps)
            sigmas.append(atoms[0]["sigma"])
        assert sigmas == sorted(sigmas)
        assert sigmas[-1] > sigmas[0] * 1.5


# ======================================================================
# 6. Species layout — reactant vs product must differ; pressure compression
# ======================================================================
class TestSpeciesLayout:
    def test_reactant_and_product_geometry_differ(self):
        """Regression test for the bug where combined_composition() merged
        all species into one atom-count blob, making reactant/product
        viewports mathematically guaranteed to look identical for any
        balanced equation."""
        reactants, products, err = eng.parse_equation("Ti + O2 -> TiO2")
        assert err is None
        r_lines, *_ = eng.build_species_layout(reactants)
        p_lines, *_ = eng.build_species_layout(products)
        assert r_lines != p_lines

    def test_pressure_compresses_inter_species_spacing(self):
        _, products, _ = eng.parse_equation("NaCl -> Na + Cl2")
        gaps = []
        for P in [1, 50, 200, 500]:
            lines, *_ = eng.build_species_layout(products, pressure_atm=P)
            xs = sorted(set(float(l.split()[1]) for l in lines))
            gaps.append(xs[-1] - xs[0])
        assert gaps == sorted(gaps, reverse=True), "spacing must shrink as pressure rises"

    def test_pressure_default_preserves_baseline(self):
        _, products, _ = eng.parse_equation("NaCl -> Na + Cl2")
        lines_default, *_ = eng.build_species_layout(products)
        lines_explicit, *_ = eng.build_species_layout(products, pressure_atm=1.0)
        assert lines_default == lines_explicit


# ======================================================================
# 7. Equation parsing
# ======================================================================
class TestParseEquation:
    @pytest.mark.parametrize("eqn", [
        "2H2 + O2 -> 2H2O",
        "2KClO3 -> 2KCl + 3O2",
        "Zn + 2HCl -> ZnCl2 + H2",
        "AgNO3 + NaCl -> AgCl + NaNO3",
        "C2H5OH + 3O2 -> 2CO2 + 3H2O",
        "Ti + O2 = TiO2",
        "4Fe + 3O2 -> 2Fe2O3",
    ])
    def test_valid_equations_parse_without_fatal_error(self, eqn):
        reactants, products, err = eng.parse_equation(eqn)
        assert reactants is not None
        assert products is not None

    def test_balanced_equations_pass_check(self):
        reactants, products, _ = eng.parse_equation("2H2 + O2 -> 2H2O")
        _, _, balanced = eng.check_atom_balance(reactants, products)
        assert balanced is True

    def test_unbalanced_equation_is_detected(self):
        reactants, products, _ = eng.parse_equation("H2 + O2 -> H2O")
        _, _, balanced = eng.check_atom_balance(reactants, products)
        assert balanced is False

    def test_state_symbols_stripped_and_used_as_phase(self):
        reactants, products, err = eng.parse_equation(
            "AgNO3(aq) + NaCl(aq) -> AgCl(s) + NaNO3(aq)")
        assert err is None
        assert reactants[0]["explicit_phase"] == "aqueous"
        assert products[0]["explicit_phase"] == "solid"
        # the (aq)/(s) tags must not leak into the formula/atom parsing
        _, _, balanced = eng.check_atom_balance(reactants, products)
        assert balanced is True

    @pytest.mark.parametrize("arrow", ["\u21cc", "<=>", "<->"])
    def test_equilibrium_arrows_normalize_correctly(self, arrow):
        eqn = f"N2 + 3H2 {arrow} 2NH3"
        reactants, products, err = eng.parse_equation(eqn)
        assert reactants is not None and products is not None
        _, _, balanced = eng.check_atom_balance(reactants, products)
        assert balanced is True

    def test_missing_separator_is_fatal_error(self):
        reactants, products, err = eng.parse_equation("just some text, no separator")
        assert reactants is None
        assert err is not None

    def test_ionic_charge_notation_triggers_warning_not_silent_failure(self):
        reactants, products, err = eng.parse_equation("Na+ + Cl- -> NaCl")
        # must not silently succeed with no warning, and must not crash
        assert reactants is not None  # best-effort parse still returned
        assert err is not None and "charge" in err.lower()


# ======================================================================
# 8. Reaction thermodynamics
# ======================================================================
class TestReactionThermo:
    @pytest.mark.parametrize("eqn,expected_dh", [
        ("Ti + O2 -> TiO2", -944.0),
        ("2H2 + O2 -> 2H2O", -571.6),
        ("C + O2 -> CO2", -393.5),
    ])
    def test_known_reference_enthalpies_match_literature(self, eqn, expected_dh):
        reactants, products, _ = eng.parse_equation(eqn)
        thermo = eng.compute_reaction_thermo(reactants, products, 298, 1)
        assert thermo["delta_h"] == pytest.approx(expected_dh, abs=0.1)

    def test_pure_elements_have_zero_formation_enthalpy(self):
        comp = eng.parse_formula("Fe")
        hf, source = eng.estimate_formation_enthalpy(comp)
        assert hf == 0.0
        assert "standard state" in source

    def test_haber_process_pressure_favors_ammonia(self):
        """Real Le Chatelier behavior: N2 + 3H2 -> 2NH3 has Δn_gas = -2,
        so higher pressure should make ΔG more negative (more favorable) —
        this is the actual industrial reason ammonia synthesis runs at
        high pressure."""
        reactants, products, _ = eng.parse_equation("N2 + 3H2 -> 2NH3")
        gs = []
        for P in [1, 50, 200, 500]:
            r2, p2, _ = eng.parse_equation("N2 + 3H2 -> 2NH3")  # fresh parse, dicts mutate in place
            thermo = eng.compute_reaction_thermo(r2, p2, 298, P)
            gs.append(thermo["delta_g"])
        assert gs == sorted(gs, reverse=True), "delta_g must decrease as pressure rises"

    def test_pressure_term_zero_when_no_gas_mole_change(self):
        reactants, products, _ = eng.parse_equation("AgNO3 + NaCl -> AgCl + NaNO3")
        thermo = eng.compute_reaction_thermo(reactants, products, 298, 500)
        assert thermo["pressure_term"] == pytest.approx(0.0, abs=1e-6)


# ======================================================================
# 9. Solvation / ionization energy
# ======================================================================
class TestSolvation:
    def test_zero_correction_at_vacuum_default(self):
        comp = eng.parse_formula("NaCl")
        assert eng.estimate_solvation_energy(comp, epsilon=1.0) == pytest.approx(0.0, abs=1e-6)

    def test_ionic_compound_stabilized_more_than_elements(self):
        """Regression test: solvation must be computed PER-SPECIES, not on
        combined_composition()'s merged blob — merging Na and Cl2 elements
        together previously made them look artificially ionic just from
        their electronegativity difference, even though neither elemental
        species is actually ionic on its own."""
        reactants, products, _ = eng.parse_equation("NaCl -> Na + Cl2")
        solv_react_low = eng.estimate_side_solvation_energy(reactants, 1.0)
        solv_react_high = eng.estimate_side_solvation_energy(reactants, 80.0)
        solv_prod_high = eng.estimate_side_solvation_energy(products, 80.0)
        assert solv_react_low == pytest.approx(0.0, abs=1.0)
        assert solv_react_high < -50, "ionic NaCl should be strongly stabilized at high epsilon"
        assert abs(solv_prod_high) < abs(solv_react_high), \
            "elemental Na+Cl2 should NOT be stabilized nearly as much as ionic NaCl"


# ======================================================================
# 10. SDF parsing (PubChem live-lookup geometry)
# ======================================================================
class TestSDFParsing:
    WATER_SDF = """962
  -OEChem-01012023003D

  3  2  0     0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.1173 O   0  0  0  0  0  0  0  0  0  0  0  0
    0.0000    0.7572   -0.4692 H   0  0  0  0  0  0  0  0  0  0  0  0
    0.0000   -0.7572   -0.4692 H   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0  0  0  0
  1  3  1  0  0  0  0
M  END
"""

    def test_valid_sdf_parses_correctly(self):
        atoms = eng.parse_sdf_atoms(self.WATER_SDF)
        assert atoms is not None
        assert len(atoms) == 3
        assert atoms[0][0] == "O"
        assert atoms[1][0] == "H"
        assert atoms[2][0] == "H"

    def test_malformed_sdf_returns_none_not_exception(self):
        assert eng.parse_sdf_atoms("garbage\nnot\na\nreal\nsdf") is None
        assert eng.parse_sdf_atoms("") is None

    def test_geom_comp_from_atoms_counts_correctly(self):
        atoms = eng.parse_sdf_atoms(self.WATER_SDF)
        comp = eng.geom_comp_from_atoms(atoms)
        assert comp["O"]["n"] == 1
        assert comp["H"]["n"] == 2


# ======================================================================
# 11. PubChem lookup — network mocked, never hits the real API
# ======================================================================
class TestPubchemLookup:
    def test_never_raises_on_network_failure(self, monkeypatch):
        monkeypatch.setattr(eng, "_pubchem_get", lambda url, timeout=6: (None, "network error (mocked)"))
        eng.pubchem_lookup.clear()  # bypass st.cache_data between test runs
        result = eng.pubchem_lookup("H2O", timeout=1)
        assert result["success"] is False
        assert result["error"] is not None
        assert "reach PubChem" in result["error"]

    def test_genuine_not_found_vs_network_failure_distinguished(self, monkeypatch):
        # Simulate a real 200-OK-but-empty response (genuine not-found)
        import json as _json
        def fake_get(url, timeout=6):
            return _json.dumps({"IdentifierList": {"CID": []}}), None
        monkeypatch.setattr(eng, "_pubchem_get", fake_get)
        eng.pubchem_lookup.clear()
        result = eng.pubchem_lookup("NotARealCompoundXYZ", timeout=1)
        assert result["success"] is False
        assert "No PubChem match found" in result["error"]

    def test_successful_lookup_parses_properties_and_geometry(self, monkeypatch):
        import json as _json
        WATER_SDF = TestSDFParsing.WATER_SDF

        def fake_get(url, timeout=6):
            if "cids/JSON" in url:
                return _json.dumps({"IdentifierList": {"CID": [962]}}), None
            if "/property/" in url:
                props = {"PropertyTable": {"Properties": [{
                    "MolecularFormula": "H2O", "MolecularWeight": "18.02",
                    "CanonicalSMILES": "O", "IUPACName": "oxidane",
                    "XLogP": -0.5, "TPSA": 20.2,
                }]}}
                return _json.dumps(props), None
            if "SDF" in url:
                return WATER_SDF, None
            return None, "unexpected URL in test"

        monkeypatch.setattr(eng, "_pubchem_get", fake_get)
        eng.pubchem_lookup.clear()
        result = eng.pubchem_lookup("H2O", timeout=1)
        assert result["success"] is True
        assert result["cid"] == 962
        assert result["molecular_formula"] == "H2O"
        assert result["atoms_3d"] is not None
        assert len(result["atoms_3d"]) == 3


# ======================================================================
# 12. Generated 3Dmol JavaScript must be syntactically valid
# ======================================================================
class TestGeneratedJS:
    @pytest.fixture(autouse=True)
    def require_node(self):
        if shutil.which("node") is None:
            pytest.skip("node not available in this environment")

    def test_render_html_produces_valid_js(self):
        comp = eng.parse_formula("AuCl")
        atom_lines, *_ = eng.build_geometry(comp)
        xyz = f"{len(atom_lines)}\nTest\n" + "\n".join(atom_lines)
        radius_map = eng.build_radius_map(comp)
        density_atoms = eng.build_density_atoms(atom_lines, comp)
        html = eng.render_3dmol_html("testviewer", xyz, radius_map, density_atoms, "#ff0000", 0.12)

        first_end = html.find("</script>")
        start = html.find("<script>", first_end + 1)
        end = html.find("</script>", start)
        js = html[start + len("<script>"): end]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(js)
            path = f.name
        try:
            result = subprocess.run(["node", "--check", path], capture_output=True, text=True)
            assert result.returncode == 0, f"Generated JS has a syntax error:\n{result.stderr}"
        finally:
            os.unlink(path)


# ======================================================================
# 13. Full-app smoke tests (Streamlit AppTest) — catches integration bugs
#     that pure unit tests structurally cannot, e.g. accidentally deleted
#     function signatures, broken wiring between modules, regex bugs that
#     only surface when real widget values flow through the UI.
# ======================================================================
class TestAppSmoke:
    def _app_path(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(here, "atomcraft_app.py")

    @pytest.mark.parametrize("formula", [
        "AuCl", "NaCl", "H2O", "Ti6Al4V", "Ca(OH)2", "GaAs", "O2", "Fe", "CuSO4.5H2O",
    ])
    def test_material_inspector_mode(self, formula):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(self._app_path())
        at.run(timeout=30)
        at.get("text_input")[0].set_value(formula).run(timeout=30)
        assert not at.exception, f"{formula} raised: {at.exception}"

    @pytest.mark.parametrize("eqn", [
        "Ti + O2 -> TiO2", "2H2 + O2 -> 2H2O", "N2 + 3H2 -> 2NH3",
        "C2H5OH + 3O2 -> 2CO2 + 3H2O", "NaCl(s) -> Na(g) + Cl2(g)",
        "N2 + 3H2 <=> 2NH3", "2Al + Fe2O3 -> Al2O3 + 2Fe",
    ])
    def test_reaction_dashboard_mode(self, eqn):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(self._app_path())
        at.run(timeout=30)
        at.get("radio")[0].set_value("Reaction Design Dashboard").run(timeout=30)
        at.get("text_input")[0].set_value(eqn).run(timeout=30)
        assert not at.exception, f"{eqn} raised: {at.exception}"

    def test_reaction_dashboard_extreme_slider_combination(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(self._app_path())
        at.run(timeout=30)
        at.get("radio")[0].set_value("Reaction Design Dashboard").run(timeout=30)
        at.get("text_input")[0].set_value("NaCl -> Na + Cl2").run(timeout=30)
        for s in at.get("slider"):
            if s.label.startswith("Temperature"):
                s.set_value(3000)
            elif s.label.startswith("Pressure"):
                s.set_value(500)
            elif "Dielectric" in s.label:
                s.set_value(80.0)
        for c in at.get("checkbox"):
            c.set_value(True)
        at.run(timeout=30)
        assert not at.exception

    def test_live_lookup_mode_falls_back_gracefully_without_network(self):
        """In this test environment PubChem is unreachable — the app must
        still render without exceptions, showing a fallback warning."""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(self._app_path())
        at.run(timeout=30)
        at.get("text_input")[0].set_value("H2O").run(timeout=30)
        for r in at.get("radio"):
            if "Data Source" in r.label:
                r.set_value("Live Lookup (PubChem)")
        at.run(timeout=45)
        assert not at.exception


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
