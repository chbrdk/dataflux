# DataFlux - Universal AI-native Database for Media Content

Ein umfassendes System für die Analyse, Speicherung und Verwaltung von Medieninhalten mit KI-gestützter Verarbeitung.

## 🏗️ Architektur

DataFlux besteht aus drei Hauptkomponenten:

### 1. Ingestion Service (Port 2013)
- **Zweck**: Upload, Speicherung und Verwaltung von Medien-Assets
- **Technologie**: FastAPI, PostgreSQL, Redis, PIL/Pillow, aiohttp
- **Features**:
  - Streaming File Upload mit automatischer Verarbeitung
  - Asset Management (Upload, Download, Delete)
  - **Multi-Thumbnail-Generierung**: Automatische Erzeugung verschiedener Thumbnail-Größen
    - **Small**: 150×100px (Grid-Ansicht)
    - **Medium**: 400×300px (Standard)
    - **Large**: 1200×800px (Modal-Anzeige)
  - **Automatische Asset-Verarbeitung**:
    - Background-Processing nach Upload
    - Automatische Thumbnail-Generierung in 3 Größen
    - Automatische KI-Analyse (Integration mit Analysis Service)
    - Intelligente Timeout-Verwaltung (120s für große Dateien)
    - Status-Tracking (processing → completed/failed)
  - **Intelligente Duplikaterkennung**:
    - Hash-basierte Duplikat-Prüfung
    - Automatische Storage-Path-Aktualisierung bei Re-Upload
    - Trigger automatische Verarbeitung bei aktualisierten Duplikaten
  - Bulk Operations
  - Foreign Key Constraint Management
  - Umfassendes Logging mit Emoji-Status-Indikatoren
  - **Personen-API-Endpoints**:
    - `GET /api/v1/persons` - Alle erkannten Personen mit Avatars
    - `GET /api/v1/persons/{face_id}/images` - Alle Bilder einer Person

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
    - **Optimierte Objekterkennung mit YOLOv8n**: Fokussiert auf Objekte (Personen werden ignoriert)
    - **FaceNet-Gesichtserkennung**: Hochpräzise Gesichtserkennung und -identifikation
      - Eindeutige Face IDs mit persistenter Datenbank
      - Avatar-Erstellung aus erkannten Gesichtern (128x128px)
      - Erkennungsstatistiken (Auftrittsanzahl, erste/letzte Sichtung)
      - Face Quality Assessment (Größe, Winkel, Beleuchtung)
      - 512-dimensionale Face Embeddings für Vergleich
    - **DeepFace-Demographics**: Alters-, Geschlechts-, Rassen- und Emotionsanalyse
    - OCR-Text-Erkennung
    - Farbanalyse und Histogramme
    - Kompositionsanalyse (Rule of Thirds, Symmetrie)

### 3. Web UI (Port 3000)
- **Zweck**: Benutzeroberfläche für Asset-Management und Analyse-Ergebnisse
- **Technologie**: Next.js, React, TypeScript, Tailwind CSS
- **Features**:

#### Asset-Management
  - Asset-Upload und -Verwaltung
  - Grid- und Listen-Ansicht mit optimierten Thumbnails
  - Bulk-Delete-Funktionalität
  - Intelligente Thumbnail-Anzeige basierend auf Kontext

#### Analyse-Ergebnisse
  - **Automatische Analyse-Anzeige**: Echte KI-Analyse-Daten werden automatisch geladen
  - **Interaktives Modal**: Vollbild-Darstellung mit 95vh Mindesthöhe
    - 2/3 Layout: Zentriertes Bild (unterstützt Hoch- und Querformat)
    - 1/3 Layout: Feature-Panels mit Tabs
    - Einsatz hochauflösender Large-Thumbnails (1200×800px)
    - Intelligente Fallback-Mechanismen bei Bilder-Fehlern
  - **Klickbare Thumbnails**: Direkter Zugriff auf Analyse-Modal
  - **8 AI-Features automatisch verfügbar**:
    - Technical Properties (Dimensionen, Format, Megapixel)
    - Technical Extended (Aspect Ratio, Helligkeit, Kontrast)
    - EXIF Comprehensive (Kamera-Info, GPS, Belichtung)
    - Image Quality (Blur-Score, Noise, Signal-to-Noise Ratio)
    - Composition (Symmetrie, Rule of Thirds)
    - Object Detection (YOLOv8n - Objekte ohne Personen)
    - Face Demographics (DeepFace - Alter, Emotion, Geschlecht, Rasse)
    - Face Recognition (FaceNet - Personenerkennung mit Avatars)
  - Responsive Design mit Tailwind CSS

#### Personen-Management
  - **Personen-Seite**: Dedizierte Übersicht aller erkannten Personen
    - Avatar-Cards mit Gesichtsbildern (128x128px)
    - Personenerkennungsstatistiken (Auftrittsanzahl, Confidence)
    - Zeitstempel (erste/letzte Sichtung)
    - Sortierung nach Häufigkeit der Auftritte
  - **Person-Detailansicht**: 
    - Klickbare Avatar-Cards öffnen Person-Detailansicht
    - Anzeige aller Bilder, in denen die Person auftaucht
    - Bild-Metadaten (Qualität, Confidence, Upload-Datum)
    - Zurück-Navigation zur Personen-Übersicht
  - **Face Database System**:
    - Persistente Speicherung von Face IDs und Embeddings
    - Automatische Erkennung von bekannten vs. neuen Gesichtern
    - Face Quality Assessment für Erkennungsgenauigkeit

#### Navigation
  - **Sidebar-Navigation**: Linksseitige Navigation mit allen Hauptfunktionen
    - Dashboard (Übersicht)
    - Upload (Dateien hochladen)
    - Search (Suche)
    - Assets (Asset-Management)
    - Analytics (Statistiken)
    - **Personen** (Personen-Management) - Neu!
  - **Responsive Design**: Funktioniert auf Desktop, Tablet und Mobile

## 🚀 Installation und Setup

### Voraussetzungen
- Python 3.9+
- Node.js 20.19.5
- PostgreSQL (Port 2001)
- Redis (Port 7003)

### Lokale Ausführung (Empfohlen für Mac Mini M4)

#### Schnellstart
```bash
# Docker Container starten (PostgreSQL + Redis)
cd /Users/m4mini/Desktop/DOCKER-local/DATAFLUX
docker-compose -f docker-compose.services.yml up -d dataflux-postgres dataflux-redis

# Alle Services lokal starten
./start-local.sh
```

#### Einzelne Services starten

#### 1. Ingestion Service (Port 2013)
```bash
cd services/ingestion-service
DATABASE_URL="postgresql://dataflux_user:secure_password_here@localhost:2001/dataflux" \
REDIS_URL="redis://:secure_redis_password_here@localhost:2002" \
python3 src/main_simple.py
```

#### 2. Analysis Service (Port 8004)
```bash
cd services/analysis-service
PYTORCH_ENABLE_MPS_FALLBACK=1 \
DATABASE_URL="postgresql://dataflux_user:secure_password_here@localhost:2001/dataflux" \
REDIS_URL="redis://:secure_redis_password_here@localhost:2002" \
INGESTION_SERVICE_URL="http://localhost:2013" \
python3 src/api_processor.py
```

#### 3. Query Service (Port 8003)
```bash
cd services/query-service
go run cmd/main_simple.go
```

#### 4. Web UI (Port 3000)
```bash
cd services/web-ui
npm run dev
```

#### Services stoppen
```bash
./stop-local.sh
```

## 📊 API Endpoints

### Ingestion Service (Port 2013)

#### Assets
- `GET /api/v1/assets` - Alle Assets abrufen
- `POST /api/v1/assets/upload` - Asset hochladen (mit automatischer Multi-Thumbnail-Generierung)
- `GET /api/v1/assets/{asset_id}/download` - Asset herunterladen
- `DELETE /api/v1/assets/{asset_id}` - Einzelnes Asset löschen

#### Thumbnails
- `GET /api/v1/assets/{asset_id}/thumbnail` - Standard-Thumbnail (400×300)
- `GET /api/v1/assets/{asset_id}/thumbnail/{size}` - Spezifische Thumbnail-Größe
  - **Small**: `thumbnail/small` (150×100px)
  - **Medium**: `thumbnail/medium` (400×300px)  
  - **Large**: `thumbnail/large` (1200×800px)
- `POST /api/v1/assets/{asset_id}/generate-thumbnails-multiple` - Mehrere Thumbnail-Größen nachträglich generieren
- `POST /api/v1/assets/generate-thumbnails` - Bulk-Thumbnail-Generierung

#### Bulk Operations
- `POST /api/v1/assets/bulk-delete` - Mehrere Assets löschen

#### Personen-Management
- `GET /api/v1/persons` - Alle erkannten Personen mit Avatars abrufen
- `GET /api/v1/persons/{face_id}/images` - Alle Bilder einer Person abrufen

#### Health Check
- `GET /health` - Service-Status prüfen

### Analysis Service (Port 2014)

#### Analyse
- `POST /api/v1/analyze/image` - Bild analysieren
- `GET /health` - Service-Status prüfen

#### Face Database
- Face Database wird automatisch in `/tmp/dataflux_face_database.json` gespeichert
- Avatar-Bilder werden in `/tmp/dataflux_avatars/` gespeichert
- Persistente Face IDs mit Embeddings für Wiedererkennung

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

## 🖼️ Centralized Data Storage Management

### Multi-Thumbnail-System
DataFlux verfügt über ein intelligentes Thumbnail-System, das automatisch verschiedene Größen für verschiedene Anwendungsfälle generiert:

#### Automatische Generierung
- **Beim Upload**: Erzeugung aller drei Größen (small, medium, large)
- **Qualitätsoptimiert**: 
  - Large: 95% JPEG-Qualität für beste visuelle Darstellung
  - Medium: 85% für optimale Größe-Leistungsverhältnis
  - Small: 80% für schnelle Grid-Darstellung
- **Format-Standardisierung**: Alle Thumbnails als JPEG mit Whitepaper-Background für PNGs

#### Intelligente Verwendung
- **Grid-Ansicht**: Small-Thumbnails für Übersichtlichkeit
- **Detail-Ansicht**: Medium-Thumbnails für ausgewogene Qualität
- **Modal-Anzeige**: Large-Thumbnails als Vollbild-Hintergrund
- **Fallback-Mechanismus**: Automatisches Degradieren bei Fehlern

### Technische Implementierung
- **PIL/Pillow**: Professionelle Bildverarbeitung mit LANCZOS-Resampling
- **Aspect-Ratio-Preservation**: Intelligente Größenanpassung ohne Verzerrung
- **Storage-Optimierung**: Effiziente Speicherung in `/tmp(dataflux_thumbnails/`
- **Cache-Strategien**: 2-Stunden-Browser-Cache für optimal Performance

## 🎨 Web UI Features

### Asset-Management
- **Upload**: Drag & Drop oder Dateiauswahl mit automatischer Multi-Thumbnail-Generierung
- **Ansichten**: Grid und Liste mit kontextangepassten Thumbnail-Größen
- **Löschen**: Einzelne Assets oder Bulk-Delete
- **Bestätigung**: Sicherheitsabfrage vor Löschung

### Analyse-Ergebnisse

#### Modal-System
- **Glassmorphismus-Design**: Elegante Vollbild-Modal mit Transparenz-Effekten
- **95vh Mindesthöhe**: Immersive Erfahrung für maximale Bilddarstellung
- **Large-Thumbnail-Hintergrund**: Hochauflösende Bilder als Hintergrund mit eleganten Overlays
- **Intelligente Fallbacks**: Automatisches Degradieren zu kleineren Thumbnails bei Fehlern
- **Responsive Layout**: Optimal angepasst für verschiedene Bildschirmgrößen

#### Datenvisualisierung
- **Strukturierte Darstellung**: JSON-Daten in übersichtlichen Tabellen
- **Automatisches Parsing**: JSON-Strings werden automatisch geparst
- **Kategorisierung**: Technische, visuelle und EXIF-Daten getrennt
- **Overlay-Elemente**: Glassmorphism-Komponenten über Bildern
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

## 🎯 Use Cases

### Zentrale Datenverwaltung
DataFlux bietet nun ein vollständiges **Centralized Data Storage Management** mit intelligenten Thumbnail-Systemen:

#### Medienarchive
- **Multi-Thumbnail-Produktion**: Automatische Generierung verschiedener Größen für verschiedene Ansichten
- **Optimierte Speicherung**: Effiziente Verwaltung großer Bildsammlungen
- **Quick Preview**: Schnelle Grid-Darstellung mit Small-Thumbnails

#### Content-Management
- **Kontextabhängige Darstellung**: Intelligente Thumbnail-Größenwahl basierend auf Anwendungsfall
- **Vollbild-Erfahrung**: Glassmorphismus-Modal für immersive Bildbetrachtung
- **Performance-optimiert**: Separate Größen für verschiedene UI-Komponenten

#### Moderne Web-Anwendungen
- **Glassmorphism-UI**: Elegante, moderne Benutzeroberfläche mit Transparenz-Effekten
- **Responsive Design**: Optimal angepasst für verschiedene Bildschirmgrößen
- **High-Quality Imaging**: 95vh Vollbild-Modal mit hochauflösenden Hintergrundbildern

#### Forensik und Analyse
- **Authentizitäts-Analyse**: Für journalistische und rechtliche Zwecke
- **Qualitätskontrolle**: Automatische Bewertung der Bildqualität
- **Detailanalyse**: Strukturierte Darstellung komplexer Analysedaten im Modal

### Praxisbeispiele

#### Instagram-ähnliche Feed-Ansicht
```
Grid-Ansicht → Small Thumbnails (150×100px)
Ein Bild betrachten → Medium Thumbnails (400×300px)  
Vollbild-Modal → Large Thumbnails (1200×800px)
```

#### E-Commerce-Produktgalerie
```
Produktübersicht → Small für schnelle Ladung
Produktdetails → Medium für optimale Qualität
Produkt-Modal → Large für immersive Erfahrung
```

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

### Version 1.2.0 🎨
- ✅ **Multi-Thumbnail-System**: Automatische Generierung verschiedener Größen (small/medium/large)
- ✅ **Glassmorphismus-Modal**: Vollbild-Darstellung mit 95vh Mindesthöhe und Transparenz-Effekten
- ✅ **Intelligente Thumbnail-Verwendung**: Kontextabhängige Größenwahl für optimale Performance
- ✅ **Hochauflösende Modal-Hintergründe**: Large-Thumbnails (1200×800px) als Hintergrundbilder
- ✅ **Erweiterte API-Endpoints**: Spezifische Thumbnail-Größen und Bulk-Generierung
- ✅ **Optimierte Bildverarbeitung**: PIL/Pillow mit LANCZOS-Resampling und Qualitätsoptimierung
- ✅ **Fallback-Mechanismen**: Intelligente Degradation bei Bildfehlern

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