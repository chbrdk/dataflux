# 🧠 FaceNet Features Übersicht

## Was FaceNet alles analysieren kann

FaceNet kann **4 verschiedene Arten von Features** generieren:

### 1. 🎯 Face Detection (`face_detection`)
**Was:** Findet alle Gesichter im Bild mit MTCNN
```json
{
  "type": "face_detection",
  "domain": "visual", 
  "confidence": 0.95,
  "data": {
    "faces": [
      {
        "face_id": 0,
        "bbox": [x1, y1, x2, y2],
        "confidence": 0.98,
        "landmarks": {
          "left_eye": [x, y],
          "right_eye": [x, y], 
          "nose": [x, y],
          "mouth_left": [x, y],
          "mouth_right": [x, y]
        }
      }
    ],
    "total_faces": 1,
    "model": "MTCNN",
    "status": "completed"
  }
}
```

### 2. 🔍 Face Recognition (`face_recognition`)
**Was:** Erkennt bekannte Personen und generiert Face Embeddings
```json
{
  "type": "face_recognition",
  "domain": "visual",
  "confidence": 0.9,
  "data": {
    "recognized_faces": [
      {
        "face_id": 0,
        "embedding_dimensions": 512,
        "embedding_key": "face_0_abc123",
        "best_match": {
          "identity": "John Doe",
          "confidence": 0.85
        },
        "is_known_face": true,
        "face_quality": "excellent"
      }
    ],
    "total_faces": 1,
    "known_faces": 1,
    "unknown_faces": 0,
    "model": "FaceNet-InceptionResnetV1",
    "recognition_method": "FaceNet-Embeddings"
  }
}
```

### 3. 📊 Face Quality Assessment (`face_quality`)
**Was:** Bewertet die Qualität jedes erkannten Gesichts
```json
{
  "type": "face_quality",
  "domain": "visual",
  "confidence": 0.9,
  "data": {
    "quality_assessments": [
      {
        "face_id": 0,
        "detection_confidence": 0.98,
        "face_size_score": 0.85,
        "face_angle_score": 0.92,
        "face_illumination_score": 0.78,
        "overall_quality_score": 0.88,
        "quality_assessment": "excellent"
      }
    ],
    "total_faces": 1,
    "model": "MTCNN-Quality",
    "status": "completed"
  }
}
```

### 4. 🧮 Face Embeddings (`facenet_embedding`)
**Was:** 512-dimensionale Vektoren für jeden Face (für Vergleich/Ähnlichkeit)
```json
{
  "type": "facenet_embedding",
  "model": "FaceNet-InceptionResnetV1",
  "dimensions": 512,
  "embedding": [0.123, -0.456, 0.789, ...], // 512 Zahlen
  "face_id": 0,
  "metadata": {
    "analyzer": "facenet",
    "device": "cpu",
    "embedding_key": "face_0_abc123"
  }
}
```

## Quality Assessment Kategorien

- **excellent** (≥ 0.8): Perfekte Qualität für Erkennung
- **good** (≥ 0.6): Gute Qualität, zuverlässige Erkennung  
- **fair** (≥ 0.4): Mittlere Qualität, eingeschränkte Erkennung
- **poor** (< 0.4): Schlechte Qualität, unzuverlässige Erkennung

## Confidence Scores

- **Detection Confidence**: Wie sicher ist die Gesichtserkennung (0-1)
- **Recognition Confidence**: Wie sicher ist die Personen-Erkennung (0-1)  
- **Quality Score**: Gesamtqualität des Gesichts (0-1)

## Frontend Anzeige

Im **Metadata Tab** werden jetzt alle Features strukturiert angezeigt:

1. **Raw Analysis Data** - Komplette JSON-Daten
2. **FaceNet Analysis Details** - Alle Face-bezogenen Features
3. **Technical Analysis Details** - Technische Features (YOLO, etc.)

## Verwendung

```bash
# FaceNet Features für ein Asset abrufen
curl "http://localhost:2013/api/v1/assets/{asset_id}/analysis" | jq '.features[] | select(.type | contains("face"))'

# Nur Face Recognition Features
curl "http://localhost:2013/api/v1/assets/{asset_id}/analysis" | jq '.features[] | select(.type == "face_recognition")'

# Face Quality Assessment
curl "http://localhost:2013/api/v1/assets/{asset_id}/analysis" | jq '.features[] | select(.type == "face_quality")'
```

## Performance

- **MTCNN**: Schnelle Face Detection
- **FaceNet**: Präzise Face Recognition  
- **CPU**: Läuft stabil auf Mac Mini M4
- **Memory**: ~512 Zahlen pro Face für Embeddings
