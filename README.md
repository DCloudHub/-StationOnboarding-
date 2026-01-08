# st_geolocation Streamlit component

This is a minimal Streamlit component that fetches browser geolocation (lat, lon)
without reloading the page and returns it to the Python app.

Structure
- st_geolocation/               (python wrapper)
  - __init__.py                 (component wrapper)
  - frontend/                   (frontend source + build)
    - public/
      - index.html
    - src/
      - index.js
    - package.json

Development
1. Install Python deps: streamlit
2. In one terminal, start the frontend dev server:
   - cd st_geolocation/frontend
   - npm install
   - ST_GEOCOMP_DEV=1 npm start
3. In another terminal, run your Streamlit app (which imports st_geolocation):
   - export ST_GEOCOMP_DEV=1  # or set in your OS
   - streamlit run example_app.py

Production / Build
1. cd st_geolocation/frontend
2. npm install
3. npm run build
   - This produces a `build/` folder. The Python wrapper looks for this folder when ST_GEOCOMP_DEV is not set.
4. Deploy your Streamlit app normally.

Notes
- The frontend uses the `streamlit-component-lib` for communicating with Streamlit.
- The component returns an object to Python: either {lat, lon} or {error}.
