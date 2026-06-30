Deploy checklist:
# AtomCraft — Before Every Deploy

1. `pip install -r requirements.txt`
2. `pytest test_atomcraft.py -v`
   - All tests must pass. If TestGeneratedJS is skipped, that's fine — it
     just means `node` isn't installed locally; it's not required for
     deployment, only useful as an extra check if available.
3. Deploy `atomcraft_app.py` as the Streamlit entry point (it imports
   everything it needs from `atomcraft_engine.py`, which must sit in the
   same directory/repo).
4. `atomcraft_fixed.py` (the old single-file version) is now superseded by
   the atomcraft_app.py + atomcraft_engine.py split — keep it around for
   reference if you like, but don't deploy it; it won't receive further
   fixes going forward.
