# DATAFLUX - Lokales Setup auf Mac Mini M4

## 🚀 Schnellstart

```bash
# Alle Services starten
./start-local.sh

# Services stoppen
./stop-local.sh
```

## 📊 Übersicht

DATAFLUX läuft vollständig lokal auf dem Mac Mini M4 mit Apple Silicon GPU-Beschleunigung!

### Laufende Services

| Service | Port | Beschreibung | Performance |
|---------|------|--------------|-------------|
| **Web-UI** | 3000 | Next.js Frontend | Lokal |
| **Ingestion** | 2013 | FastAPI Upload Service | Lokal |
| **Analysis** | 2014 | AI/ML Analyzer + Docling | M4 GPU |
| **Query** | 8003 | Go Search Service | Lokal |
| **PostgreSQL** | 2001 | Datenbank | Docker |
| **Redis** | 2002 | Cache | Docker |

### AI/ML Modelle auf M4

- ✅ **YOLO v8** - 66ms Inference (extrem schnell!)
- ✅ **DeepFace** - Gesichtserkennung (Alter, Geschlecht, Emotion)
- ✅ **FaceNet MTCNN** - Face Detection (CPU)
- ✅ **FaceNet Recognition** - 512D Face Embeddings
- ✅ **Docling** - Professionelle Dokumentenverarbeitung (PDF, Office, HTML)

## 🔧 Manuelle Verwaltung

### Services einzeln starten

```bash
# Ingestion Service
cd services/ingestion-service
DATABASE_URL="postgresql://dataflux_user:secure_password_here@localhost:2001/dataflux" \
REDIS_URL="redis://:secure_redis_password_here@localhost:2002" \
python3 src/main_simple.py

# Analysis Service  
cd services/analysis-service
DATABASE_URL="postgresql://dataflux_user:secure_password_here@localhost:2001/dataflux" \
CLAUDE_API_KEY="your_anthropic_api_key_here" \
INGESTION_SERVICE_URL="http://localhost:2013" \
PYTHONPATH=/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/services/analysis-service \
python3 src/api_processor.py

# Query Service
cd services/query-service
INGESTION_SERVICE_URL="http://localhost:2013" \
go run cmd/main_simple.go

# Web-UI
cd services/web-ui
npm run dev
```

### Docker Container

```bash
# Nur PostgreSQL und Redis starten
docker start dataflux-postgres dataflux-redis

# Container stoppen
docker stop dataflux-postgres dataflux-redis
```

## 📝 Logs

```bash
# Ingestion Service
tail -f /tmp/ingestion_service.log

# Analysis Service (AI/ML)
tail -f /tmp/analysis_service.log

# Query Service
tail -f /tmp/query_service.log

# Web-UI
tail -f /tmp/webui.log
```

## 🧪 Testen

```bash
# Health Checks
curl http://localhost:2013/health  # Ingestion
curl http://localhost:8003/health  # Query

# Upload Test
curl -X POST "http://localhost:2013/api/v1/assets" \
  -F "file=@test-image.jpg"

# Features abrufen
curl "http://localhost:2013/api/v1/assets/{asset_id}/analysis" | jq
```

## 🎯 Features

### Bildanalyse (47+ Features)

1. **Technical Properties** - Abmessungen, Format, Megapixel
2. **Technical Extended** - Helligkeit, Kontrast
3. **EXIF Comprehensive** - 48+ Metadaten-Tags
4. **Image Quality** - Schärfe, SNR, Quality Score
5. **Composition** - Symmetrie, Ausrichtung
6. **YOLO Object Detection** - Objekte erkennen
7. **DeepFace Analysis** - Gesichter, Alter, Geschlecht, Emotion
8. **FaceNet Detection** - Präzise Gesichtserkennung
9. **FaceNet Recognition** - Face Embeddings
10. **Face Quality** - Quality Assessment

### Dokumentenanalyse (Docling)

1. **PDF-Verarbeitung** - Layout-Analyse, OCR, Tabellenerkennung
2. **Office-Dokumente** - DOCX, PPTX, XLSX mit Formatierung
3. **HTML-Verarbeitung** - Web-Content-Extraktion
4. **Multimodale Unterstützung** - Bilder, Audio, VTT-Untertitel
5. **Intelligente Segmentierung** - Text, Tabellen, Figuren, Überschriften
6. **Metadaten-Extraktion** - Dokumenttyp, Sprache, Komplexität
7. **Performance-Optimierung** - LRU-Caching, Batch-Processing

## 🔥 Performance

- **YOLO**: 66ms pro Bild
- **DeepFace**: ~26s für 2 Gesichter
- **FaceNet**: ~4s pro Gesicht
- **Docling**: ~2-5s pro Dokument (je nach Größe und Komplexität)
- **Gesamt**: ~35s für 42MP Bild mit allen Features

## 🐛 Troubleshooting

### Service startet nicht

```bash
# Prüfe Logs
tail -50 /tmp/ingestion_service.log
tail -50 /tmp/analysis_service.log

# Prüfe Prozesse
ps aux | grep "main_simple"
```

### PostgreSQL Connection Error

```bash
# Starte PostgreSQL
docker start dataflux-postgres

# Prüfe Status
docker ps | grep postgres
```

### Port bereits belegt

```bash
# Finde Prozess
lsof -i :3000  # oder :2013, :8003

# Stoppe Services
./stop-local.sh
```

## 💡 Tipps

- **GPU nutzen**: FaceNet läuft auf CPU wegen MPS-Kompatibilität, YOLO nutzt den M4 optimal
- **Vollbilder**: System analysiert jetzt Vollauflösung (kein Resize mehr)
- **Features anzeigen**: Web-UI zeigt alle Features im Analysis Results Modal
- **Dokumente**: PDFs und Office-Dokumente werden automatisch mit Docling verarbeitet
- **Dateinamen**: Verwenden Sie ASCII-Zeichen für Dateinamen (keine Umlaute) um Encoding-Probleme zu vermeiden
- **Logs**: Immer zuerst die Logs prüfen bei Problemen

## 📚 Weiterführende Informationen

- YOLO: Ultra-schnelle Objekterkennung
- DeepFace: Gesichtsanalyse mit demographischen Daten
- FaceNet: Google's Face Recognition System
- Docling: IBM's professionelle Dokumentenverarbeitung
- PostgreSQL: Alle Features persistent gespeichert

## 🎉 Erfolg!

Wenn alles läuft, solltest du sehen:
- Web-UI: http://localhost:3000
- Assets hochladen und analysieren (Bilder + Dokumente)
- 47+ Features pro Bild
- Vollständige Dokumentenanalyse mit Docling
- Analyse-Ergebnisse in Echtzeit

**Viel Spaß mit DATAFLUX auf deinem Mac Mini M4!** 🚀
