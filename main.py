# -*- coding: utf-8 -*-
import os
import re
from functools import lru_cache

from flask import Flask, jsonify, request, render_template_string
from geopy.geocoders import Nominatim

app = Flask(__name__)

PLZ_RE = re.compile(r"^\d{5}$")

# Wichtig: identifizierbarer User-Agent (und idealerweise Kontakt)
UA = os.getenv("NOMINATIM_USER_AGENT", "plz-koordinaten-demo (contact: you@example.com)")
geolocator = Nominatim(user_agent=UA, timeout=10)

@lru_cache(maxsize=2048)
def lookup_plz(plz: str):
    # Präziser als nur "plz": Kontext hinzufügen
    loc = geolocator.geocode(query=f"{plz}, Deutschland", country_codes="de")
    if not loc:
        return None
    return {"plz": plz, "latitude": loc.latitude, "longitude": loc.longitude}

HTML = """<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>PLZ → Koordinaten</title>
  <style>
    body{font-family:system-ui,Segoe UI,Roboto,Arial;margin:40px;max-width:760px}
    input,button{font-size:16px;padding:10px}
    .row{display:flex;gap:10px;flex-wrap:wrap}
    .out{margin-top:18px;padding:14px;border:1px solid #ddd;border-radius:10px}
    .muted{color:#666}
    code{font-family:ui-monospace,Consolas,monospace}
  </style>
</head>
<body>
  <h1>PLZ → Koordinaten</h1>
  <p class="muted">Demo: Gibt Breitengrad/Längengrad für eine deutsche PLZ aus.</p>

  <div class="row">
    <input id="plz" inputmode="numeric" pattern="\\d{5}" maxlength="5" placeholder="z. B. 64283" />
    <button id="go">Suchen</button>
  </div>

  <div class="out" id="out">
    <div class="muted">Noch keine Anfrage.</div>
  </div>

  <p class="muted" style="margin-top:18px">
    Geocoding: Nominatim / OpenStreetMap. Bitte Usage Policy beachten.
  </p>

<script>
const out = document.getElementById("out");
document.getElementById("go").addEventListener("click", async () => {
  const plz = document.getElementById("plz").value.trim();
  out.textContent = "Lade...";
  try{
    const r = await fetch(`/api/coords?plz=${encodeURIComponent(plz)}`);
    const j = await r.json();
    if(!r.ok) throw new Error(j.error || "Fehler");
    out.innerHTML = `
      <div><b>PLZ:</b> ${j.plz}</div>
      <div><b>Breitengrad:</b> <code>${j.latitude}</code></div>
      <div><b>Längengrad:</b> <code>${j.longitude}</code></div>
    `;
  }catch(e){
    out.innerHTML = `<div><b>Fehler:</b> ${e.message}</div>`;
  }
});
</script>
</body>
</html>"""

@app.get("/")
def index():
    return render_template_string(HTML)

@app.get("/api/coords")
def api_coords():
    plz = (request.args.get("plz") or "").strip()
    if not PLZ_RE.match(plz):
        return jsonify({"error": "Ungültige PLZ. Erwartet: 5 Ziffern."}), 400

    data = lookup_plz(plz)
    if not data:
        return jsonify({"error": "PLZ nicht gefunden."}), 404

    return jsonify(data)

# Lokal startbar (Cloud Run nutzt standardmäßig gunicorn)
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
