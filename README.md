# DataFlux - Universal AI-native Database for Media Content

Ein umfassendes System für die Analyse, Speicherung und Verwaltung von Medieninhalten mit KI-gestützter Verarbeitung.

## 🏗️ Architektur

DataFlux besteht aus drei Hauptkomponenten:

### 1. Ingestion Service (Port 2013)
- **Zweck**: Upload, Speicherung und Verwaltung von Medien-Assets
- **Technologie**: FastAPI, PostgreSQL, Redis
- **Features**:
  - Streaming File Upload
  - Asset Management (Upload, Download, Delete)
  - Bulk Operations
  - Hash-basierte Duplikaterkennung
  - Foreign Key Constraint Management

### 2. Analysis Service (Port 2014)
- **Zweck**: KI-gestützte Analyse von Medieninhalten
- **Technologie**: FastAPI, Python, OpenCV, PIL, YOLO, SciPy
- **Features**:
  - **Umfassende EXIF-Extraktion**:
    - Standard EXIF-Tags
    - Bildinformationen (Format, Größe, Transparenz)
    - GPS-Daten und Standortinformationen
    - Kamera-Informationen (Make, Model, Software, Datum)
    - Belichtungseinstellungen (Verschlusszeit, Blende, ISO, Blitz)
  - **Bildqualitätsanalyse**:
    - Schärfe-Bewertung (Laplacian Variance)
    - Rausch-Analyse und -Bewertung
    - Unschärfe-Erkennung (Gradient Magnitude)
    - Kompressions-Artefakte
    - High-Frequency-Energie
    - Qualitäts-Score und Empfehlungen
  - **Beleuchtungsanalyse**:
    - Helligkeits-Verteilung (LAB-Farbraum)
    - Histogramm-Analyse mit Peak-Erkennung
    - Schatten- und Highlight-Analyse
    - Dynamikbereich-Bewertung
    - Belichtungs-Empfehlungen
  - **Authentizitäts-Analyse**:
    - Error Level Analysis (ELA)
    - Kompressions-Artefakte-Erkennung
    - Edge-Consistency-Analyse
    - Noise-Pattern-Analyse
    - Manipulations-Indikatoren
    - Authentizitäts-Score
  - **Erweiterte Features**:
    - Objekterkennung mit YOLO
    - Gesichtserkennung mit DeepFace
    - OCR-Text-Erkennung
    - Farbanalyse und Histogramme
    - Kompositionsanalyse (Rule of Thirds, Symmetrie)

### 3. Web UI (Port 3000)
- **Zweck**: Benutzeroberfläche für Asset-Management und Analyse-Ergebnisse
- **Technologie**: Next.js, React, TypeScript, Tailwind CSS
- **Features**:
  - Asset-Upload und -Verwaltung
  - Grid- und Listen-Ansicht
  - Bulk-Delete-Funktionalität
  - Analyse-Ergebnisse in strukturierter Tabelle
  - JSON-Parsing und -Darstellung
  - Responsive Design

## 🚀 Installation und Setup

### Voraussetzungen
- Python 3.9+
- Node.js 20.19.5
- PostgreSQL (Port 2001)
- Redis (Port 7003)

### Services starten

#### 1. Ingestion Service
```bash
cd services/ingestion-service
python3 src/main_simple.py
```

#### 2. Analysis Service
```bash
cd services/analysis-service
python3 -m uvicorn src.main_simple:app --host 0.0.0.0 --port 2014 --reload
```

#### 3. Web UI
```bash
cd services/web-ui
npm install
npm run build
npm start
```

## 📊 API Endpoints

### Ingestion Service (Port 2013)

#### Assets
- `GET /api/v1/assets` - Alle Assets abrufen
- `POST /api/v1/assets/upload` - Asset hochladen
- `GET /api/v1/assets/{asset_id}/download` - Asset herunterladen
- `DELETE /api/v1/assets/{asset_id}` - Einzelnes Asset löschen
- `POST /api/v1/assets/bulk-delete` - Mehrere Assets löschen

#### Health Check
- `GET /health` - Service-Status prüfen

### Analysis Service (Port 2014)

#### Analyse
- `POST /api/v1/analyze/image` - Bild analysieren
- `GET /health` - Service-Status prüfen

## 🔍 Umfassende Bildanalyse

Der Analysis Service bietet eine vollständige Bildanalyse mit mehreren KI-Modellen:

### EXIF-Daten-Extraktion
- **Standard EXIF**: Alle verfügbaren EXIF-Tags mit automatischer Tag-Namen-Zuordnung
- **Bildinformationen**: Format, Modus, Größe, Transparenz, Palette-Details
- **GPS-Daten**: Koordinaten, Standortinformationen, Fehlerbehandlung
- **Kamera-Informationen**: Make, Model, Software, Aufnahmedatum, Künstler, Copyright
- **Belichtungseinstellungen**: Verschlusszeit, Blende, ISO, Blitz, Brennweite, Weißabgleich

### Bildqualitätsanalyse
- **Schärfe-Bewertung**: Laplacian Variance für Schärfe-Messung
- **Rausch-Analyse**: Standardabweichung und Rausch-Bewertung
- **Unschärfe-Erkennung**: Gradient Magnitude für Unschärfe-Detection
- **Kompressions-Artefakte**: High-Frequency-Energie-Analyse
- **Qualitäts-Score**: Gesamtbewertung (excellent/good/fair/poor)
- **Empfehlungen**: Automatische Verbesserungsvorschläge

### Beleuchtungsanalyse
- **Helligkeits-Verteilung**: LAB-Farbraum-Analyse
- **Histogramm-Analyse**: Peak-Erkennung mit SciPy
- **Schatten- und Highlight-Analyse**: Pixel-Verteilung
- **Dynamikbereich**: Min/Max-Werte und Bereich
- **Belichtungs-Bewertung**: well_exposed/underexposed/overexposed
- **Empfehlungen**: Belichtungs-Verbesserungsvorschläge

### Authentizitäts-Analyse (Forensik)
- **Error Level Analysis (ELA)**: Kompressions-Artefakte-Erkennung
- **Edge-Consistency**: Kanten-Konsistenz zwischen Kompressionsstufen
- **Noise-Pattern-Analyse**: FFT-basierte Rauschmuster-Analyse
- **Manipulations-Indikatoren**: Automatische Erkennung von Bearbeitungen
- **Authentizitäts-Score**: 0-1 Bewertung (likely_authentic bis suspicious)

### Erweiterte KI-Features
- **Objekterkennung**: YOLO v8 für 80+ Objektklassen
- **Gesichtserkennung**: DeepFace für Gesichtsanalyse
- **OCR-Text-Erkennung**: EasyOCR für Text-Extraktion
- **Farbanalyse**: Dominante Farben, Histogramme, Farbharmonie
- **Kompositionsanalyse**: Rule of Thirds, Symmetrie, Balance

## 🎨 Web UI Features

### Asset-Management
- **Upload**: Drag & Drop oder Dateiauswahl
- **Ansichten**: Grid und Liste
- **Löschen**: Einzelne Assets oder Bulk-Delete
- **Bestätigung**: Sicherheitsabfrage vor Löschung

### Analyse-Ergebnisse
- **Strukturierte Darstellung**: JSON-Daten in übersichtlichen Tabellen
- **Automatisches Parsing**: JSON-Strings werden automatisch geparst
- **Kategorisierung**: Technische, visuelle und EXIF-Daten getrennt
- **Responsive Design**: Optimiert für verschiedene Bildschirmgrößen

### Technische Details
- **React Query**: Für API-Zugriffe und Caching
- **Hot Toast**: Benachrichtigungen für Aktionen
- **TypeScript**: Typsicherheit und bessere Entwicklungserfahrung
- **Tailwind CSS**: Moderne, responsive Styles

## 🛠️ Entwicklung

### Code-Struktur
```
services/
├── ingestion-service/
│   ├── src/main_simple.py      # FastAPI App
│   ├── requirements.txt        # Python Dependencies
│   └── Dockerfile             # Container Setup
├── analysis-service/
│   ├── src/main_simple.py     # FastAPI App
│   ├── analyzers/
│   │   └── image_analyzer.py  # EXIF & Image Analysis
│   ├── requirements.txt       # Python Dependencies
│   └── Dockerfile            # Container Setup
└── web-ui/
    ├── components/
    │   ├── Assets.tsx         # Asset Management
    │   └── AnalysisResults.tsx # Results Display
    ├── package.json          # Node.js Dependencies
    └── Dockerfile           # Container Setup
```

### Debugging
- **Logging**: Umfassende Logs in allen Services
- **Health Checks**: Status-Endpoints für Monitoring
- **Error Handling**: Graceful Error-Behandlung
- **CORS**: Cross-Origin-Requests konfiguriert

## 🔧 Konfiguration

### Ports
- **Ingestion Service**: 2013
- **Analysis Service**: 2014
- **Web UI**: 3000
- **PostgreSQL**: 2001
- **Redis**: 7003

### Umgebungsvariablen
- `PYTHONDONTWRITEBYTECODE=1` - Verhindert .pyc-Dateien
- `NODE_ENV=production` - Für optimierte Builds

## 📈 Performance

### Optimierungen
- **Streaming Uploads**: Effiziente Dateiübertragung
- **Hash-basierte Duplikate**: Schnelle Duplikaterkennung
- **Caching**: Redis für bessere Performance
- **Bulk Operations**: Effiziente Massenoperationen

### Skalierbarkeit
- **Container-ready**: Docker-Unterstützung
- **Microservices**: Getrennte, skalierbare Services
- **API-first**: RESTful APIs für Integration

## 🐛 Bekannte Probleme und Lösungen

### String-Splitting in Web UI
- **Problem**: JSON-Strings wurden zeichenweise gerendert
- **Lösung**: Automatisches JSON-Parsing in FeatureDataTable

### Foreign Key Constraints
- **Problem**: Löschreihenfolge bei Assets
- **Lösung**: Geordnete Löschung (features → segments → embeddings → assets → entities)

### Port-Konflikte
- **Problem**: Services starten nicht wegen belegter Ports
- **Lösung**: Prozess-Management und Port-Checks

## 🚀 Nächste Schritte

### Geplante Features
- **Video-Analyse**: Erweiterte Video-Verarbeitung
- **Audio-Analyse**: Audio-Content-Analyse
- **Dokument-Analyse**: OCR und Text-Extraktion
- **Weaviate-Integration**: Vector-Search für Embeddings
- **Docker-Compose**: Vollständige Container-Orchestrierung

### Verbesserungen
- **Caching**: Erweiterte Caching-Strategien
- **Monitoring**: Prometheus/Grafana-Integration
- **Security**: Authentication und Authorization
- **Testing**: Umfassende Test-Suite

## 📝 Changelog

### Version 1.1.0
- ✅ **Bildqualitätsanalyse**: Schärfe, Rausch, Unschärfe, Kompressions-Artefakte
- ✅ **Beleuchtungsanalyse**: Helligkeit, Histogramm, Schatten/Highlights, Dynamikbereich
- ✅ **Authentizitäts-Analyse**: ELA, Edge-Consistency, Noise-Pattern, Manipulations-Erkennung
- ✅ **SciPy-Integration**: Peak-Erkennung für Histogramm-Analyse
- ✅ **Erweiterte KI-Features**: YOLO, DeepFace, EasyOCR, Farbanalyse, Komposition
- ✅ **Umfassende EXIF-Extraktion**: Standard, GPS, Kamera, Belichtung
- ✅ **Web UI**: Strukturierte Datenanzeige, JSON-Parsing, Responsive Design
- ✅ **Asset-Management**: Upload, Delete, Bulk-Operations, Foreign Key Management

---

**DataFlux** - Ein leistungsstarkes System für die KI-gestützte Medienanalyse und -verwaltung.