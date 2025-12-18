Du bist mein "Cloud-Run Service Generator" für data-tales.dev.

INPUT (von mir):
A) Ein einzelnes Python-Skript (unten), das aktuell nur lokal läuft (CLI oder Script).
B) Eine Liste vorhandener Services (Name + URL), plus Landing-URL.
C) Styling-Referenz: Meine Landing Page nutzt CSS-Variablen und Komponenten (siehe unten).

ZIEL:
Wandle das Skript in ein vollständiges, lauffähiges Mini-Webprojekt um, das auf Google Cloud Run deploybar ist (Source Deploy, ohne Dockerfile), mit:
- Flask Backend + Gunicorn Start (Cloud Run kompatibel, PORT via env)
- einer HTML Oberfläche für den User
- einem einheitlichen Header (sticky, blur, gleiche Variablen/Buttons wie Landing Page)
- Theme Toggle (dark/light) mit localStorage, identisch zum Landing Verhalten
- Navigation: Links zur Landing Page + Links zu den anderen Services
- sauberer Validierung/Fehleranzeige im UI
- optional: /api Endpunkt als JSON (für spätere Integration)

AUSGABEFORMAT (sehr wichtig):
Gib AUSSCHLIESSLICH die folgenden Dateien aus, jeweils in einem eigenen Codeblock mit Dateiname als Überschrift:

1) `requirements.txt`
2) `main.py`
3) `README.md`

Keine weiteren Erklärtexte außerhalb der Dateien.

ARCHITEKTUR-VORGABEN:
- Datei heißt `main.py` und exportiert `app` (Flask instance), damit Cloud Run standardmäßig `gunicorn -b :$PORT main:app` nutzen kann.
- Keine externen Templates-Dateien; nutze `render_template_string`, damit es bei 3 Dateien bleibt.
- Kein Docker Compose, kein Dockerfile.
- Im UI: Nutze exakt die CSS Variablen aus der Landing Page als :root und [data-theme="light"].
- Header-Komponenten sollen semantisch an die Landing Page angelehnt sein:
  - `.site-header`, `.container`, `.header-inner`, `.brand`, `.brand-mark`, `.nav`, `.header-actions`, `.btn`, `.btn-primary`, `.btn-ghost`
- Links im Header:
  - Brand klickt auf LANDING_URL
  - Nav enthält: "Landing", "Cookbook", plus 3–8 Service Links aus SERVICES-LISTE
  - Rechtes Ende: Theme Toggle Button (☾/☀) + optional ein Primary Button, der zur Landing-Kontaktsektion verlinkt
- Theme Toggle Implementation:
  - setzt `data-theme="light"` auf `document.documentElement` (oder entfernt es) genau wie auf der Landing Page
  - speichert `theme` in localStorage
- UI Layout:
  - Inhalt zentriert in `.container`
  - nutze Cards (`.card`) für Ergebnis/Fehler
- API:
  - `GET /api` mit query param(s) passend zum Skript
  - gibt JSON { ok: true, ... } oder { ok: false, error: "..."} zurück
- Security/Robustness:
  - validate user input strikt (Regex etc.)
  - timeouts bei externen Calls setzen
  - klare Fehlermeldungen, keine Stacktraces im UI
  - caching (z.B. lru_cache) falls sinnvoll

README-VORGABEN:
- Kurzer Zweck (1–2 Sätze)
- Lokales Starten:
  - `python -m venv .venv`
  - pip install
  - `python main.py`
  - URL nennen
- Cloud Run Deploy (Source):
  - `gcloud run deploy <service-name> --source . --region europe-west1 --allow-unauthenticated`
- Hinweis auf env vars (falls genutzt), z.B. USER_AGENT oder API_KEY
- Optional: Domain mapping Hinweis "Subdomain -> Cloud Run"

INPUT-DATEN:
LANDING_URL = "https://data-tales.dev/"
COOKBOOK_URL = "https://data-tales.dev/cookbook/"

SERVICES (Name -> URL):
- "PLZ → Koordinaten" -> "https://plz.data-tales.dev/"
- "<Service 2 Name>" -> "<https://...>"
- "<Service 3 Name>" -> "<https://...>"

SERVICE_META:
- service_name_slug: "<kurz, z.B. plz>"
- page_title: "<Seitentitel>"
- page_h1: "<H1>"
- page_subtitle: "<1 Satz, sachlich>"

LANDING STYLE CSS (muss verwendet werden):
[Angehängt: die kompletten CSS-Variablen + die relevanten Klassen aus der Landing Page einbetten; nutze sie 1:1.
Du darfst zusätzlich minimal ergänzen (z.B. .content, .result), aber NICHT den Look ändern. Die Variablen die du nicht nutzt entferne sie]

PYTHON SCRIPT (zu transformieren):
Angehängt

ERWARTETES VERHALTEN IM BROWSER:
- Seite zeigt ein Eingabefeld + Button
- Nach Klick wird entweder Ergebnis angezeigt (Card) oder Fehler (Card)
- Ergebnis wird auch als JSON über /api abrufbar sein
- Header sieht aus wie Landing Page und verlinkt sinnvoll

WICHTIG:
- Schreibe keine generischen Platzhalter-Links. Nutze exakt die oben angegebenen URLs.
- Wenn Services-Liste > 6: gib nur die ersten 6 in den Header und ergänze einen "Mehr…" Link, der zur Landing Page #projects führt.
- Liefere lauffähigen Code ohne TODOs.