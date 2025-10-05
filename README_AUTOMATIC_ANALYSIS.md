# 🧠 Automatische Analyse nach Upload

## Workflow

1. **Upload** → Asset wird auf `processing` gesetzt
2. **Thumbnail Generation** → Thumbnails werden erstellt  
3. **Queue** → Asset wird auf `queued` gesetzt
4. **Analysis Service** holt Asset ab und analysiert es
5. **Completed** → Analyse fertig, Features in Datenbank

## 🎭 Neue Features: Scene Classification

### Automatische Szenenerkennung mit CLIP
- **Generische Kategorien**: Personen, Tiere, Fahrzeuge, Gebäude, Natur, etc.
- **Spezifische Szenen**: Hochzeit, Geburtstag, Auto fahren, Landschaft, etc.
- **Automatische Tags**: Extrahiert relevante Schlagwörter aus der Klassifizierung
- **Flexibel**: Keine vordefinierten Prompts - funktioniert mit allen Bildinhalten

### Beispiel-Ergebnisse:
```json
{
  "type": "scene_classification",
  "domain": "semantic", 
  "confidence": 0.086,
  "data": {
    "primary_scene": {
      "type": "generic",
      "scene": "a person or people",
      "confidence": 0.086
    },
    "scene_tags": ["sports", "people"],
    "generic_scenes": [
      {"scene": "a person or people", "confidence": 0.086},
      {"scene": "a sport or activity", "confidence": 0.084}
    ],
    "specific_scenes": [
      {"scene": "sports game or match", "confidence": 0.051}
    ]
  }
}
```

## Problemlösung

### Problem: Assets wurden direkt auf `completed` gesetzt

**Ursache:** Der Ingestion Service versuchte selbst die Analyse durchzuführen (`start_analysis_for_asset`), was nicht funktionierte.

**Lösung:** Der Upload-Prozess setzt das Asset jetzt auf `queued`, damit der dedizierte **Analysis Service** es abholt.

### Geänderte Funktion

`services/ingestion-service/src/main_simple.py`:

```python
async def process_asset_automatically(asset_id: str, file_path: str, mime_type: str):
    """Automatically process an asset after upload - set to queued for Analysis Service"""
    try:
        # Generate thumbnails
        if mime_type.startswith('image/'):
            await generate_multiple_thumbnails(file_path, "/tmp/dataflux_thumbnails", asset_id)
        
        # Set status to 'queued' so Analysis Service can pick it up
        await db.execute("""
            UPDATE assets 
            SET processing_status = 'queued'
            WHERE id = $1
        """, asset_id)
```

## Vorteile

✅ **Separation of Concerns** - Jeder Service macht sein Job
✅ **Skalierbar** - Analysis Service kann unabhängig skalieren
✅ **GPU-Optimiert** - Analysis Service nutzt M4 GPU optimal
✅ **Robust** - Bei Fehlern kann Analyse neu gestartet werden

## Monitoring

```bash
# Prüfe Queue
curl "http://localhost:2013/api/v1/assets" | jq '[.assets[] | select(.processing_status == "queued")]'

# Prüfe Processing
curl "http://localhost:2013/api/v1/assets" | jq '[.assets[] | select(.processing_status == "processing")]'

# Prüfe Analysis Service Logs
tail -f /tmp/analysis_service.log | grep "Processing"

# Prüfe Scene Classification Logs
tail -f /tmp/analysis_service.log | grep "Scene classification"
```

## 🎭 Scene Classification Testen

```bash
# Teste Scene Classification direkt
python3 test_scene_classification.py

# Teste mit spezifischem Bild
python3 -c "
import asyncio
import sys
from pathlib import Path
sys.path.append('services/analysis-service')
from analyzers.scene_classifier import SceneClassifier

async def test():
    classifier = SceneClassifier()
    if classifier.available:
        results = await classifier.classify_scene('test-image.jpg')
        if results.get('available'):
            print(f'Primary Scene: {results[\"primary_scene\"][\"scene\"]}')
            print(f'Tags: {\", \".join(results[\"scene_tags\"])}')

asyncio.run(test())
"
```

## 📊 Features abrufen

### Alle Features eines Assets:
```bash
# Alle Features abrufen
curl "http://localhost:2013/api/v1/assets/{asset_id}/features"

# Nur Scene Classification Features
curl "http://localhost:2013/api/v1/assets/{asset_id}/features?feature_type=scene_classification"

# Nur semantic Features (Scene Classification, etc.)
curl "http://localhost:2013/api/v1/assets/{asset_id}/features?domain=semantic"
```

### Beispiel-Response:
```json
{
  "asset_id": "uuid-here",
  "features": [
    {
      "id": "feature-uuid",
      "type": "scene_classification",
      "domain": "semantic",
      "confidence": 0.086,
      "data": {
        "primary_scene": {
          "type": "generic",
          "scene": "a person or people",
          "confidence": 0.086
        },
        "scene_tags": ["sports", "people"],
        "generic_scenes": [...],
        "specific_scenes": [...]
      },
      "metadata": {"analyzer": "clip_scene_classifier"},
      "created_at": "2025-10-05T12:45:03.252Z"
    }
  ],
  "total": 1,
  "filters": {"feature_type": "scene_classification", "domain": null}
}
```

## Manuelle Analyse auslösen

Falls ein Asset nicht automatisch analysiert wird:

```bash
# Asset auf queued setzen
curl -X PUT "http://localhost:2013/api/v1/assets/{asset_id}/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "queued"}'
```

Der Analysis Service holt es im nächsten Zyklus ab (alle 15 Sekunden).
