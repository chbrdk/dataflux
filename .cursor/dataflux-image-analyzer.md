# DataFlux - Complete Image Analyzer Specification

## Cursor Implementation Prompt

```
Create a comprehensive ImageAnalyzer plugin in services/analysis-service/src/analyzers/image.py that extracts EVERY possible feature from images using multiple AI models and computer vision techniques.

The analyzer must inherit from BaseAnalyzer and implement these methods:
- extract_segments(): For images, return single segment (whole image) or multiple regions if detected
- analyze_segment(): Extract ALL features listed below
- generate_embeddings(): Create multi-modal embeddings for similarity search

Use these AI models and libraries:
- OpenAI GPT-4 Vision for detailed descriptions
- CLIP for visual-semantic embeddings
- YOLO v8 for object detection
- DeepFace for face analysis
- TensorFlow/PyTorch for specialized models
- OpenCV for technical analysis
- Pillow for metadata extraction
```

## 1. Visual Content Analysis

### 1.1 Object Detection & Recognition
```
Extract using YOLO v8 and Detectron2:
- Primary objects (with bounding boxes and confidence scores)
- Secondary/background objects
- Object count per category
- Object relationships (spatial: above, below, next to, inside)
- Object interactions (holding, using, touching)
- Brand/logo detection (using custom trained model)
- Text/OCR in image (signs, labels, documents)
- QR codes and barcodes
- Vehicle identification (make, model, year if visible)
- Animal species and breeds
- Plant and vegetation types
- Food items and dishes
- Clothing items and fashion accessories
- Furniture and interior objects
- Tools and equipment
- Electronic devices
```

### 1.2 People Analysis
```
Extract using DeepFace and MediaPipe:
- Number of people
- Age estimation (ranges: child, teen, young adult, adult, senior)
- Gender presentation (male, female, non-binary appearance)
- Ethnicity estimation (with confidence scores, handle sensitively)
- Face landmarks (68 points)
- Face recognition (if reference database available)
- Emotional expressions (happy, sad, neutral, angry, surprised, disgusted, fearful)
- Eye gaze direction
- Head pose (pitch, yaw, roll)
- Body pose estimation (25 keypoints)
- Hand gestures and positions
- Clothing style and colors per person
- Accessories (glasses, hat, jewelry, watch)
- Hair color and style
- Facial hair presence and style
- Visible tattoos or distinctive marks
- Physical interactions between people
- Group dynamics (clusters, pairs, individuals)
```

### 1.3 Activity & Action Recognition
```
Extract using action recognition models:
- Primary action/activity (walking, sitting, running, dancing, working)
- Sports activities (specific sport type)
- Professional activities (cooking, construction, medical, teaching)
- Recreational activities (reading, gaming, relaxing)
- Social interactions (talking, hugging, handshaking)
- Movement blur indicating motion
- Gesture recognition (waving, pointing, thumbs up)
- Facial micro-expressions
- Body language interpretation
- Crowd behavior patterns
```

## 2. Scene Understanding

### 2.1 Location & Environment
```
Extract using Places365 and scene classification models:
- Scene category (indoor/outdoor)
- Specific location type (beach, office, kitchen, street, forest, etc.)
- Sub-location details (conference room vs open office)
- Geographic hints (architectural style, vegetation, landmarks)
- Weather conditions (sunny, cloudy, rainy, snowy, foggy)
- Time of day estimation (morning, afternoon, evening, night)
- Season estimation (spring, summer, fall, winter)
- Natural elements (sky, water, mountains, trees)
- Urban vs rural vs natural setting
- Indoor lighting type (natural, fluorescent, incandescent, mixed)
- Room function (bedroom, kitchen, bathroom, living room)
- Architectural style and period
- Cultural indicators
```

### 2.2 Spatial Analysis
```
Extract using depth estimation and 3D reconstruction:
- Depth map estimation
- Foreground/midground/background separation
- Spatial layout (open, cluttered, organized)
- Room dimensions estimation (if indoor)
- Object distances and relationships
- Vanishing points
- Horizon line position
- 3D scene reconstruction possibility
- Floor plan estimation (for interior shots)
- Furniture arrangement
```

## 3. Photographic & Artistic Analysis

### 3.1 Camera & Perspective
```
Extract using computer vision techniques:
- Shot type (close-up, medium shot, wide shot, extreme close-up)
- Camera angle (eye-level, low angle, high angle, bird's eye, worm's eye)
- Camera orientation (landscape, portrait, square)
- Perspective type (one-point, two-point, three-point)
- Field of view estimation
- Focal length estimation (wide angle, normal, telephoto)
- Depth of field (shallow, deep, bokeh effect)
- Motion blur presence and direction
- Lens distortion (barrel, pincushion, fisheye)
- Tilt-shift effect
- Dutch angle/rotation
```

### 3.2 Composition Analysis
```
Extract using composition analysis algorithms:
- Rule of thirds compliance
- Golden ratio/spiral presence
- Leading lines detection
- Symmetry (vertical, horizontal, radial)
- Balance (symmetric, asymmetric, radial)
- Framing elements
- Negative space usage
- Pattern and repetition
- Visual hierarchy
- Focus point detection
- Center of visual weight
- Diagonal composition
- Triangle composition
- Frame within frame
- Fill the frame technique
```

### 3.3 Artistic Style
```
Extract using style classification models:
- Photography style (portrait, landscape, street, documentary, fashion, etc.)
- Artistic movement (if applicable: impressionist, minimalist, surreal, etc.)
- Visual style (realistic, stylized, abstract)
- Mood/atmosphere (dramatic, peaceful, energetic, melancholic)
- Professional vs amateur assessment
- Instagram/social media style detection
- Film photography vs digital characteristics
- Vintage/retro effects
- HDR processing detection
- Black and white vs color
- Selective color effects
```

## 4. Color & Lighting Analysis

### 4.1 Color Analysis
```
Extract using color science algorithms:
- Dominant colors (top 5 with percentages)
- Complete color palette extraction
- Color harmony analysis (complementary, analogous, triadic)
- Color temperature (warm, cool, neutral in Kelvin)
- Color mood (vibrant, muted, pastel, dark, bright)
- Saturation levels
- Hue distribution histogram
- Color contrast ratio
- Monochromatic detection
- Color gradients
- Skin tone analysis
- Color space (sRGB, Adobe RGB, etc.)
- White balance assessment
```

### 4.2 Lighting Analysis
```
Extract using lighting analysis models:
- Lighting direction (front, back, side, top, bottom)
- Lighting type (natural, artificial, mixed)
- Light quality (hard, soft, diffused)
- Number of light sources
- Shadow analysis (direction, hardness, length)
- Highlight and shadow distribution
- Contrast levels (high, medium, low)
- Dynamic range assessment
- Exposure assessment (overexposed, underexposed, balanced)
- Golden hour/blue hour detection
- Flash usage detection
- Light color/temperature
- Rim lighting presence
- Silhouette detection
- Chiaroscuro effect
```

## 5. Technical Image Properties

### 5.1 Image Metrics
```
Extract using OpenCV and Pillow:
- Resolution (width x height)
- Aspect ratio
- File format (JPEG, PNG, RAW, etc.)
- Color mode (RGB, CMYK, Grayscale, etc.)
- Bit depth
- File size
- Compression quality estimation
- DPI/PPI
- Noise level estimation
- Sharpness measurement
- Chromatic aberration detection
- Vignetting detection
- Lens flare presence
- Grain/film grain detection
```

### 5.2 EXIF & Metadata
```
Extract all available EXIF data:
- Camera make and model
- Lens information
- Focal length
- Aperture (f-stop)
- Shutter speed
- ISO sensitivity
- Exposure compensation
- Metering mode
- White balance setting
- Flash information
- GPS coordinates (if available)
- Capture date and time
- Software used
- Copyright information
- Image orientation
- Color profile
```

### 5.3 Image Quality Assessment
```
Extract using IQA algorithms:
- Overall quality score (0-100)
- Blur detection and measurement
- Focus quality assessment
- JPEG artifact detection
- Compression artifact score
- Moiré pattern detection
- Banding detection
- Posterization detection
- Upscaling detection
- AI-generated image detection
- Manipulation/editing detection
- Authenticity verification
```

## 6. Semantic & Contextual Analysis

### 6.1 High-Level Description
```
Generate using GPT-4 Vision:
- Detailed natural language description (2-3 paragraphs)
- Brief one-line summary
- Keywords extraction (20-30 relevant tags)
- Title suggestion
- Caption generation (social media style)
- Alt-text for accessibility
- SEO-optimized description
- Story interpretation (what's happening)
- Context inference (before/after events)
- Emotional tone description
```

### 6.2 Conceptual Tags
```
Extract conceptual and thematic elements:
- Themes (love, nature, technology, family, work, etc.)
- Concepts (freedom, isolation, joy, struggle, success)
- Symbolism interpretation
- Metaphorical elements
- Cultural significance
- Historical context (if applicable)
- Event type (wedding, birthday, conference, protest)
- Holiday/celebration detection
- Professional context (business, medical, educational)
- Lifestyle indicators (luxury, casual, sporty, formal)
```

### 6.3 Sentiment & Emotion
```
Analyze emotional content:
- Overall sentiment (positive, negative, neutral with score)
- Emotional categories (joy, sadness, fear, anger, surprise, disgust)
- Emotional intensity (1-10 scale)
- Viewer emotion prediction (how it makes people feel)
- Tension level
- Energy level (calm to energetic)
- Formality level (casual to formal)
- Intimacy level (public to private)
```

## 7. Special Detections

### 7.1 Safety & Compliance
```
Detect sensitive content:
- NSFW content detection with categories
- Violence/gore detection
- Weapon presence
- Drug/alcohol references
- Child safety assessment
- Medical/graphic content
- Political symbols/figures
- Religious symbols/content
- Brand/trademark visibility
- License plate detection
- Personal information visibility (documents, screens)
```

### 7.2 Accessibility Features
```
Generate for accessibility:
- Detailed alt-text for screen readers
- Color blindness friendly assessment
- Contrast ratio for text overlays
- Important elements for low vision users
- Motion sensitivity warnings
- Flashing/strobing content detection
```

## 8. Embedding Generation

### 8.1 Multi-Modal Embeddings
```
Generate various embeddings:
- CLIP embedding (512 dimensions)
- ImageBind embedding (1024 dimensions)
- DINOv2 embedding (768 dimensions)
- Face embeddings (128 dimensions per face)
- Color histogram embedding
- Texture embedding
- Shape embedding
- Style embedding
- Combined multi-modal embedding
```

## 9. Output Format

### 9.1 Complete Feature Structure
```python
{
    "visual_features": {
        "objects": [...],
        "people": {...},
        "activities": [...],
        "text_ocr": [...]
    },
    "scene_features": {
        "location": {...},
        "environment": {...},
        "spatial": {...}
    },
    "photographic_features": {
        "camera": {...},
        "composition": {...},
        "style": {...}
    },
    "color_lighting_features": {
        "colors": {...},
        "lighting": {...}
    },
    "technical_features": {
        "metrics": {...},
        "exif": {...},
        "quality": {...}
    },
    "semantic_features": {
        "description": "...",
        "tags": [...],
        "concepts": [...],
        "sentiment": {...}
    },
    "safety_features": {
        "nsfw_score": 0.0,
        "safety_categories": {...}
    },
    "embeddings": {
        "clip": [...],
        "dino": [...],
        "imagebind": [...]
    },
    "confidence_scores": {
        "overall": 0.95,
        "per_feature": {...}
    }
}
```

## 10. Implementation Requirements

### 10.1 Processing Pipeline
```
1. Load image and extract basic metadata
2. Run safety checks first (fail fast if problematic)
3. Parallel processing:
   - Thread 1: Object detection and people analysis
   - Thread 2: Scene understanding and spatial analysis
   - Thread 3: Color and lighting analysis
   - Thread 4: Technical metrics and quality
4. Sequential processing:
   - GPT-4 Vision for descriptions (needs context from above)
   - Generate embeddings
   - Calculate confidence scores
5. Store all features in PostgreSQL
6. Store embeddings in Weaviate
7. Create relationships in Neo4j
```

### 10.2 Performance Optimizations
```
- Cache model predictions for similar images
- Use batch processing for multiple images
- Implement progressive analysis (basic → detailed)
- Skip detailed analysis for low-quality images
- Use GPU acceleration for all models
- Implement timeout mechanisms (max 30s per image)
- Queue management for large batches
```

### 10.3 Error Handling
```
- Graceful degradation if models fail
- Minimum viable analysis guarantee
- Retry logic for API-based models
- Fallback models for each feature
- Detailed error logging
- Partial result saving
```

## Cursor Implementation Instructions

```
Implement this complete image analyzer with:
1. All feature extractors listed above
2. Parallel processing for performance
3. Comprehensive error handling
4. Confidence scores for each feature
5. Support for all common image formats
6. GPU acceleration where applicable
7. Caching mechanisms
8. Progress callbacks for long operations
9. Ability to selectively enable/disable feature groups
10. Export results in JSON and PostgreSQL formats

Make the code modular so individual analyzers can be updated independently.
Use async/await for all I/O operations.
Include comprehensive logging for debugging.
Add unit tests for each feature extractor.
```