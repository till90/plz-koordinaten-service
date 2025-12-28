#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API:
- GET /api?plz=<postleitzahl>&coordsys=<system> -> Gibt die Koordinaten für eine bestimmte Postleitzahl in einem bestimmten Koordinatensystem zurück
"""

import os
import re
import logging
from functools import lru_cache
from typing import Optional, Tuple

from flask import Flask, jsonify, render_template_string, request
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable
from pyproj import Proj, transform, exceptions

# ---------------------------------------------------------
# Coordinate Systems (edit here)
# ---------------------------------------------------------
COORDINATE_SYSTEMS = {
    "latlon": {"name": "Lat/Lon (WGS84)", "epsg": "EPSG:4326"},
    "utm32": {"name": "UTM Zone 32N (ETRS89)", "epsg": "EPSG:25832"},
    "utm33": {"name": "UTM Zone 33N (ETRS89)", "epsg": "EPSG:25833"},
    "gk4": {"name": "Gauß-Krüger Zone 4", "epsg": "EPSG:31468"},
}

# ---------------------------------------------------------
# Service Meta / Navigation (edit here)
# ---------------------------------------------------------
LANDING_URL = "https://data-tales.dev/"
COOKBOOK_URL = "https://data-tales.dev/cookbook/"

SERVICES = [
    ("PLZ → Koordinaten", "https://plz.data-tales.dev/"),
    # Add more services here as (name, url) tuples.
]

SERVICE_META = {
    "service_name_slug": "plz",
    "page_title": "PLZ → Koordinaten – data-tales.dev",
    "page_h1": "PLZ → Koordinaten",
    "page_subtitle": "Ermittle Breiten- und Längengrad zu einer deutschen Postleitzahl.",
}


# ---------------------------------------------------------
# Flask App
# ---------------------------------------------------------
app = Flask(__name__)
app.logger.setLevel(logging.INFO)

PLZ_RE = re.compile(r"^\d{5}$")


def _env_float(name: str, default: float, min_v: float, max_v: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        v = float(raw)
        return max(min_v, min(max_v, v))
    except Exception:
        return default


def _env_str(name: str, default: str, max_len: int = 200) -> str:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return raw[:max_len]


NOMINATIM_USER_AGENT = _env_str(
    "NOMINATIM_USER_AGENT",
    "data-tales-plz/1.0 (+https://data-tales.dev/)",
    max_len=200,
)
NOMINATIM_TIMEOUT_SECONDS = _env_float("NOMINATIM_TIMEOUT_SECONDS", 4.0, 1.0, 20.0)
NOMINATIM_COUNTRY_CODES = _env_str("NOMINATIM_COUNTRY_CODES", "de", max_len=50)

_geolocator = Nominatim(user_agent=NOMINATIM_USER_AGENT, timeout=NOMINATIM_TIMEOUT_SECONDS)


def normalize_plz(plz_raw: Optional[str]) -> str:
    if plz_raw is None:
        raise ValueError("Bitte eine Postleitzahl (PLZ) angeben.")
    plz = plz_raw.strip()
    if not plz:
        raise ValueError("Bitte eine Postleitzahl (PLZ) angeben.")
    if len(plz) > 20:
        raise ValueError("Eingabe zu lang. Bitte genau 5 Ziffern eingeben.")
    if not PLZ_RE.fullmatch(plz):
        raise ValueError("Ungültige PLZ. Bitte genau 5 Ziffern eingeben (z. B. 64283).")
    return plz


@lru_cache(maxsize=2048)
def lookup_coordinates_for_plz(plz: str) -> Optional[Tuple[float, float]]:
    """
    Returns (latitude, longitude) or None if not found.
    Raises RuntimeError on service issues.
    """
    try:
        loc = _geolocator.geocode(query=plz, country_codes=NOMINATIM_COUNTRY_CODES)
        if not loc:
            return None
        return (float(loc.latitude), float(loc.longitude))
    except (GeocoderTimedOut, GeocoderUnavailable):
        raise RuntimeError("Der Geocoding-Dienst hat nicht rechtzeitig geantwortet. Bitte später erneut versuchen.")
    except GeocoderServiceError:
        raise RuntimeError("Der Geocoding-Dienst ist aktuell nicht verfügbar. Bitte später erneut versuchen.")
    except Exception:
        app.logger.exception("Unexpected error during geocoding")
        raise RuntimeError("Unerwarteter Fehler beim Geocoding. Bitte später erneut versuchen.")


def transform_coordinates(
    latitude: float, longitude: float, target_epsg: str
) -> Tuple[float, float]:
    """
    Transforms coordinates from WGS84 to the target EPSG.
    Raises ValueError on issues.
    """
    try:
        in_proj = Proj("EPSG:4326")  # WGS84
        out_proj = Proj(target_epsg)
        x, y = transform(in_proj, out_proj, longitude, latitude, always_xy=True)
        return x, y
    except exceptions.ProjError as e:
        raise ValueError(f"Fehler bei der Koordinatentransformation: {e}")


def build_nav_items(current_base_url: str):
    """
    Ensures we do not output placeholder links. Keeps first 6 service links if list grows.
    """
    clean = []
    for name, url in SERVICES:
        if not name or not url:
            continue
        if "<" in url or ">" in url:
            continue
        if url.startswith("http://") or url.startswith("https://"):
            clean.append((name, url))
    if len(clean) > 6:
        clean = clean[:6] + [("Mehr…", f"{LANDING_URL}#projects")]

    out = []
    for name, url in clean:
        is_current = current_base_url.rstrip("/") == url.rstrip("/")
        out.append({"name": name, "url": url, "is_current": is_current})
    return out


HTML_TEMPLATE = r"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="{{ meta.page_subtitle }}" />
  <meta name="theme-color" content="#0b0f19" />
  <title>{{ meta.page_title }}</title>

  <script>
  // Theme bootstrapping (avoid flash): matches landing behavior (data-theme="light" + localStorage key "theme")
  (function(){
    try{
      var t = localStorage.getItem('theme');
      if(t === 'light'){ document.documentElement.setAttribute('data-theme','light'); }
    }catch(e){}
  })();
  </script>

  <style>
  :root{
    --bg: #0b0f19;
    --bg2:#0f172a;
    --card:#111a2e;
    --text:#e6eaf2;
    --muted:#a8b3cf;
    --border: rgba(255,255,255,.10);
    --shadow: 0 18px 60px rgba(0,0,0,.35);
    --primary:#6ea8fe;
    --primary2:#8bd4ff;
    --focus: rgba(110,168,254,.45);

    --radius: 18px;
    --container: 1100px;
    --gap: 18px;

    --font: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
  }

  [data-theme="light"]{
    --bg:#f6f7fb;
    --bg2:#ffffff;
    --card:#ffffff;
    --text:#111827;
    --muted:#4b5563;
    --border: rgba(17,24,39,.12);
    --shadow: 0 18px 60px rgba(17,24,39,.10);
    --primary:#2563eb;
    --primary2:#0ea5e9;
    --focus: rgba(37,99,235,.25);
  }

  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    margin:0;
    font-family:var(--font);
    background: radial-gradient(1200px 800px at 20% -10%, rgba(110,168,254,.25), transparent 55%),
                radial-gradient(1000px 700px at 110% 10%, rgba(139,212,255,.20), transparent 55%),
                linear-gradient(180deg, var(--bg), var(--bg2));
    color:var(--text);
  }

  .container{
    max-width:var(--container);
    margin:0 auto;
    padding:0 18px;
  }

  .skip-link{
    position:absolute; left:-999px; top:10px;
    background:var(--card); color:var(--text);
    padding:10px 12px; border-radius:10px;
    border:1px solid var(--border);
  }
  .skip-link:focus{left:10px; outline:2px solid var(--focus)}

  .site-header{
    position:sticky; top:0; z-index:20;
    backdrop-filter: blur(10px);
    background: rgba(10, 14, 24, .55);
    border-bottom:1px solid var(--border);
  }
  [data-theme="light"] .site-header{ background: rgba(246,247,251,.75); }

  .header-inner{
    display:flex; align-items:center; justify-content:space-between;
    padding:14px 0;
    gap:14px;
  }
  .brand{display:flex; align-items:center; gap:10px; text-decoration:none; color:var(--text); font-weight:700}
  .brand-mark{
    width:14px; height:14px; border-radius:6px;
    background: linear-gradient(135deg, var(--primary), var(--primary2));
    box-shadow: 0 10px 25px rgba(110,168,254,.25);
  }
  .nav{display:flex; gap:16px; flex-wrap:wrap}
  .nav a{color:var(--muted); text-decoration:none; font-weight:600}
  .nav a:hover{color:var(--text)}
  .nav a[aria-current="page"]{color:var(--text)}

  .header-actions{display:flex; gap:10px; align-items:center}
  .header-note{
    display:flex;
    align-items:center;
    gap:8px;
    padding:8px 10px;
    border-radius:12px;
    border:1px solid var(--border);
    background: rgba(255,255,255,.04);
    color: var(--muted);
    font-weight: 750;
    font-size: 12px;
    line-height: 1;
    white-space: nowrap;
  }

  [data-theme="light"] .header-note{
    background: rgba(17,24,39,.03);
  }

  .header-note__label{
    letter-spacing: .06em;
    text-transform: uppercase;
    font-weight: 900;
    color: var(--muted);
  }

  .header-note__mail{
    color: var(--text);
    text-decoration: none;
    font-weight: 850;
  }

  .header-note__mail:hover{
    text-decoration: underline;
  }

  /* Mobile: Label ausblenden, nur Mail zeigen */
  @media (max-width: 720px){
    .header-note__label{ display:none; }
  }
  .btn{
    display:inline-flex; align-items:center; justify-content:center;
    gap:8px;
    padding:10px 14px;
    border-radius:12px;
    border:1px solid var(--border);
    text-decoration:none;
    font-weight:700;
    color:var(--text);
    background: transparent;
    cursor:pointer;
  }
  .btn:focus{outline:2px solid var(--focus); outline-offset:2px}
  .btn-primary{
    border-color: transparent;
    background: linear-gradient(135deg, var(--primary), var(--primary2));
    color: #0b0f19;
  }
  [data-theme="light"] .btn-primary{ color:#ffffff; }
  .btn-ghost{ background: transparent; }
  .btn:hover{transform: translateY(-1px)}
  .btn:active{transform:none}

  .sr-only{
    position:absolute; width:1px; height:1px; padding:0; margin:-1px;
    overflow:hidden; clip:rect(0,0,0,0); border:0;
  }

  .hero{padding:42px 0 18px}
  .kicker{
    margin:0 0 10px;
    display:inline-block;
    font-weight:800;
    letter-spacing:.08em;
    text-transform:uppercase;
    color:var(--muted);
    font-size:12px;
  }
  h1{margin:0 0 12px; font-size:42px; line-height:1.1}
  @media (max-width: 520px){ h1{font-size:34px} }
  .lead{margin:0 0 18px; color:var(--muted); font-size:16px; line-height:1.6}

  .toolbar{
    display:flex; gap:12px; flex-wrap:wrap;
    align-items:center;
    margin:18px 0 18px;
  }
  .search{flex:1; min-width:220px}
  .search input{
    width:100%;
    padding:12px 14px;
    border-radius:12px;
    border:1px solid var(--border);
    background: rgba(255,255,255,.04);
    color: var(--text);
    font-weight:650;
  }
  [data-theme="light"] .search input{ background: rgba(17,24,39,.03); }
  .search input:focus{ outline:2px solid var(--focus); outline-offset:2px }

  .card{
    border:1px solid var(--border);
    border-radius: var(--radius);
    background: rgba(255,255,255,.04);
    padding:16px;
    box-shadow: var(--shadow);
    transition: transform .12s ease, border-color .12s ease;
  }
  [data-theme="light"] .card{ background: rgba(255,255,255,.92); }
  .card:hover{ transform: translateY(-2px); border-color: rgba(110,168,254,.35); }

  .card-title{font-weight:900; font-size:16px; margin:0 0 8px}
  .card-desc{color:var(--muted); margin:0 0 12px; line-height:1.55}

  /* Minimal additions (no visual redesign) */
  .content{padding-bottom:42px}
  .result-grid{display:grid; grid-template-columns: 1fr; gap: var(--gap); }
  .kv{display:flex; gap:10px; flex-wrap:wrap; align-items:baseline}
  .kv strong{font-weight:900}
  .mono{font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono","Courier New", monospace;}
  .hint{font-size:12px; color:var(--muted); margin-top:10px}
  .card.error{border-color: rgba(255,255,255,.18)}

  .site-footer-notice {
    margin-top: 28px;
    padding-top: 18px;
    border-top: 1px solid var(--border);
    font-size: 12px;
    color: var(--muted);
    text-align: center;
  }
  .site-footer-notice a {
    color: var(--muted);
    font-weight: 600;
  }
  .site-footer-notice a:hover {
    color: var(--text);
  }
  </style>
</head>

<body>
  <a class="skip-link" href="#main">Zum Inhalt springen</a>

  <header class="site-header">
    <div class="container header-inner">
      <a class="brand" href="{{ landing_url }}" aria-label="Zur Landing Page">
        <span class="brand-mark" aria-hidden="true"></span>
        <span class="brand-text">data-tales.dev</span>
      </a>

      <div class="nav-dropdown" data-dropdown>
          <button class="btn btn-ghost nav-dropbtn"
                  type="button"
                  aria-haspopup="true"
                  aria-expanded="false"
                  aria-controls="servicesMenu">
            Dienste <span class="nav-caret" aria-hidden="true">▾</span>
          </button>

          <div id="servicesMenu" class="card nav-menu" role="menu" hidden>
            <a role="menuitem" href="https://flybi-demo.data-tales.dev/">Flybi Dashboard Demo</a>
            <a role="menuitem" href="https://wms-wfs-sources.data-tales.dev/">WMS/WFS Server Viewer</a>
            <a role="menuitem" href="https://tree-locator.data-tales.dev/">Tree Locator</a>
            <a role="menuitem" href="https://plz.data-tales.dev/">PLZ → Koordinaten</a>
            <a role="menuitem" href="https://paw-wiki.data-tales.dev/">Paw Patrole Wiki</a>
            <a role="menuitem" href="https://paw-quiz.data-tales.dev/">Paw Patrole Quiz</a>
            <a role="menuitem" href="https://hp-quiz.data-tales.dev/">Harry Potter Quiz</a>
            <a role="menuitem" href="https://worm-attack-3000.data-tales.dev/">Wurm Attacke 3000</a>
          </div>
      </div>

      <div class="header-actions">
        <div class="header-note" aria-label="Feedback Kontakt">
          <span class="header-note__label">Änderung / Kritik:</span>
          <a class="header-note__mail" href="mailto:info@data-tales.dev">info@data-tales.dev</a>
        </div>

        
        <button class="btn btn-ghost" id="themeToggle" type="button" aria-label="Theme umschalten">
          <span aria-hidden="true" id="themeIcon">☾</span>
          <span class="sr-only">Theme umschalten</span>
        </button>
      </div>
    </div>
  </header>

  <main id="main">
    <section class="hero">
      <div class="container content">
        <p class="kicker">Tool</p>
        <h1>{{ meta.page_h1 }}</h1>
        <p class="lead">{{ meta.page_subtitle }}</p>

        <form method="get" action="/" novalidate>
          <div class="toolbar" role="region" aria-label="Eingabeformular">
            <div class="search">
              <label class="sr-only" for="plz">Deutsche PLZ (5-stellig)</label>
              <input
                id="plz"
                name="plz"
                type="text"
                inputmode="numeric"
                autocomplete="postal-code"
                placeholder="z. B. 64283"
                value="{{ plz|e }}"
                maxlength="5"
                pattern="\\d{5}"
                aria-describedby="plzHelp"
              />
              <div class="hint" id="plzHelp">Erlaubt sind genau 5 Ziffern. API: <span class="mono">/api?plz=64283</span></div>
            </div>
             <div class="search">
                 <label class="sr-only" for="coordsys">Koordinatensystem</label>
                 <select id="coordsys" name="coordsys" class="search input">
                     {% for key, value in coordinate_systems.items() %}
                         <option value="{{ key }}" {% if key == selected_coordsys %}selected{% endif %}>{{ value.name }}</option>
                     {% endfor %}
                 </select>
             </div>
            <button class="btn btn-primary" type="submit">Koordinaten holen</button>
          </div>
        </form>

        <div class="result-grid" aria-live="polite">
          {% if error %}
            <div class="card error" role="alert">
              <div class="card-title">Fehler</div>
              <p class="card-desc">{{ error }}</p>
            </div>
          {% elif result %}
            <div class="card">
               <div class="card-title">Ergebnis</div>
               <p class="card-desc">Quelle: Nominatim (OpenStreetMap) • System: {{ result.coordsys_name }}</p>
               <div class="kv"><strong>PLZ:</strong> <span class="mono">{{ result.plz }}</span></div>
               {% if result.x and result.y %}
                   <div class="kv"><strong>X:</strong> <span class="mono">{{ "%.3f"|format(result.x) }}</span></div>
                   <div class="kv"><strong>Y:</strong> <span class="mono">{{ "%.3f"|format(result.y) }}</span></div>
               {% else %}
                   <div class="kv"><strong>Breitengrad:</strong> <span class="mono">{{ "%.6f"|format(result.latitude) }}</span></div>
                   <div class="kv"><strong>Längengrad:</strong> <span class="mono">{{ "%.6f"|format(result.longitude) }}</span></div>
               {% endif %}
               <p class="hint">JSON: <a class="mono" href="/api?plz={{ result.plz|urlencode }}&coordsys={{ selected_coordsys }}">/api?plz={{ result.plz }}&coordsys={{ selected_coordsys }}</a></p>
            </div>
          {% else %}
            <div class="card">
              <div class="card-title">Bereit</div>
              <p class="card-desc">Gib eine PLZ ein, um die Koordinaten zu erhalten. Das Ergebnis ist auch als JSON über <span class="mono">/api</span> abrufbar.</p>
            </div>
          {% endif %}
        </div>

        <footer class="site-footer-notice">
          <p>
            Dieser Dienst nutzt Daten von <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>, die unter der <a href="https://opendatacommons.org/licenses/odbl/" target="_blank" rel="noopener">Open Data Commons Open Database Lizenz</a> (ODbL) verfügbar sind.
            Die Geokodierung erfolgt über <a href="https://nominatim.org/" target="_blank" rel="noopener">Nominatim</a>. Bitte beachten Sie die <a href="https://operations.osmfoundation.org/policies/nominatim/" target="_blank" rel="noopener">Nutzungsrichtlinie</a>.
          </p>
        </footer>
      </div>
    </section>
  </main>

  <script>
    (function(){
    const dd = document.querySelector('[data-dropdown]');
    if(!dd) return;

    const btn = dd.querySelector('.nav-dropbtn');
    const menu = dd.querySelector('.nav-menu');

    function setOpen(isOpen){
      btn.setAttribute('aria-expanded', String(isOpen));
      if(isOpen){
        menu.hidden = false;
        dd.classList.add('open');
      }else{
        menu.hidden = true;
        dd.classList.remove('open');
      }
    }

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const isOpen = btn.getAttribute('aria-expanded') === 'true';
      setOpen(!isOpen);
    });

    document.addEventListener('click', (e) => {
      if(!dd.contains(e.target)) setOpen(false);
    });

    document.addEventListener('keydown', (e) => {
      if(e.key === 'Escape') setOpen(false);
    });

    // Wenn per Tab aus dem Dropdown rausnavigiert wird: schließen
    dd.addEventListener('focusout', () => {
      requestAnimationFrame(() => {
        if(!dd.contains(document.activeElement)) setOpen(false);
      });
    });

    // Initial geschlossen
    setOpen(false);
  })();
  (function(){
    var btn = document.getElementById('themeToggle');
    var icon = document.getElementById('themeIcon');

    function applyIcon(){
      var isLight = document.documentElement.getAttribute('data-theme') === 'light';
      icon.textContent = isLight ? '☀' : '☾';
    }
    applyIcon();

    btn.addEventListener('click', function(){
      var isLight = document.documentElement.getAttribute('data-theme') === 'light';
      try{
        if(isLight){
          document.documentElement.removeAttribute('data-theme');
          localStorage.setItem('theme','dark');
        }else{
          document.documentElement.setAttribute('data-theme','light');
          localStorage.setItem('theme','light');
        }
      }catch(e){}
      applyIcon();
    });
  })();
  </script>
</body>
</html>
"""


@app.get("/")
def index():
    plz_raw = request.args.get("plz", "")
    plz = plz_raw.strip() if plz_raw else ""
    selected_coordsys = request.args.get("coordsys", "latlon")
    if selected_coordsys not in COORDINATE_SYSTEMS:
        selected_coordsys = "latlon"

    error = None
    result = None

    if plz:
        try:
            plz_norm = normalize_plz(plz)
            coords = lookup_coordinates_for_plz(plz_norm)
            if coords is None:
                error = f"Keine Koordinaten für PLZ {plz_norm} gefunden."
            else:
                lat, lon = coords
                result = {
                    "plz": plz_norm,
                    "latitude": lat,
                    "longitude": lon,
                    "coordsys_name": COORDINATE_SYSTEMS[selected_coordsys]["name"],
                    "x": None,
                    "y": None,
                }
                if selected_coordsys != "latlon":
                    epsg = COORDINATE_SYSTEMS[selected_coordsys]["epsg"]
                    x, y = transform_coordinates(lat, lon, epsg)
                    result["x"] = x
                    result["y"] = y

        except ValueError as ve:
            error = str(ve)
        except RuntimeError as rexc:
            error = str(rexc)

    current_base = request.url_root
    nav_items = build_nav_items(current_base_url=current_base)

    return render_template_string(
        HTML_TEMPLATE,
        meta=SERVICE_META,
        landing_url=LANDING_URL,
        cookbook_url=COOKBOOK_URL,
        nav_items=nav_items,
        plz=plz,
        error=error,
        result=result,
        coordinate_systems=COORDINATE_SYSTEMS,
        selected_coordsys=selected_coordsys,
    )


@app.get("/api")
def api():
    try:
        plz = normalize_plz(request.args.get("plz", None))
        selected_coordsys = request.args.get("coordsys", "latlon")
        if selected_coordsys not in COORDINATE_SYSTEMS:
            selected_coordsys = "latlon"
    except ValueError as ve:
        return jsonify(ok=False, error=str(ve)), 400

    try:
        coords = lookup_coordinates_for_plz(plz)
    except RuntimeError as rexc:
        return jsonify(ok=False, error=str(rexc)), 503

    if coords is None:
        return jsonify(ok=False, error=f"Keine Koordinaten für PLZ {plz} gefunden."), 404

    lat, lon = coords
    response_data = {
        "ok": True,
        "plz": plz,
        "latitude": lat,
        "longitude": lon,
        "coordsys": selected_coordsys,
        "coordsys_name": COORDINATE_SYSTEMS[selected_coordsys]["name"],
    }

    if selected_coordsys != "latlon":
        try:
            epsg = COORDINATE_SYSTEMS[selected_coordsys]["epsg"]
            x, y = transform_coordinates(lat, lon, epsg)
            response_data["x"] = x
            response_data["y"] = y
        except ValueError as ve:
            return jsonify(ok=False, error=str(ve)), 400

    return jsonify(response_data)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
