# PLZ → Koordinaten (Cloud Run Mini-Service)

Kleiner Flask-Service für data-tales.dev, der deutsche Postleitzahlen (PLZ) in Koordinaten (Breite/Länge) auflöst – inkl. UI und JSON-API.

## Lokal starten

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
python main.py
