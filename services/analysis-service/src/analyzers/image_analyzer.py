#!/usr/bin/env python3
"""
Image Analyzer - umfassende Bildanalyse mit YOLO, EXIF, Farben, Komposition
"""

import cv2
import numpy as np
from PIL import Image, ExifTags
import json
import logging
from pathlib import Path
import asyncio
from typing import Dict, List, Any
import colorsys
from collections import Counter
import math

logger = logging.getLogger(__name__)

class ImageAnalyzer:
    """Umfassender Bildanalysator"""
    
    def __init__(self):
        self.yolo_model = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialisiere ML-Modelle"""
        try:
            from ultralytics import YOLO
            self.yolo_model = YOLO('yolov8n.pt')
            logger.info("✅ YOLO model loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️ Could not load YOLO model: {e}")
            self.yolo_model = None
    
    async def analyze(self, image_path: str, asset: Dict) -> Dict:
        """Führe umfassende Bildanalyse durch"""
        try:
            logger.info(f"🔍 Starting comprehensive image analysis for {Path(image_path).name}")
            
            # Lade Bild
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            pil_image = Image.open(image_path)
            
            # Führe alle Analysen durch
            results = {
                'segments': [],
                'features': [],
                'embeddings': [],
                'metadata': {'analyzer': 'comprehensive_image_analyzer', 'version': '1.0'}
            }
            
            # 1. Technische Eigenschaften
            technical_features = await self._analyze_technical_properties(image, pil_image, asset)
            results['features'].extend(technical_features)
            
            # 2. EXIF-Daten
            exif_features = await self._analyze_exif_data(pil_image)
            results['features'].extend(exif_features)
            
            # 3. Farbanalyse
            color_features = await self._analyze_colors(image)
            results['features'].extend(color_features)
            
            # 4. Objekterkennung (YOLO)
            if self.yolo_model:
                object_features = await self._analyze_objects(image)
                results['features'].extend(object_features)
            
            # 5. Kompositionsanalyse
            composition_features = await self._analyze_composition(image)
            results['features'].extend(composition_features)
            
            # 6. Texturanalyse
            texture_features = await self._analyze_texture(image)
            results['features'].extend(texture_features)
            
            # 7. Helligkeits- und Kontrastanalyse
            brightness_features = await self._analyze_brightness_contrast(image)
            results['features'].extend(brightness_features)
            
            logger.info(f"✅ Analysis completed: {len(results['features'])} features generated")
            return results
            
        except Exception as e:
            logger.error(f"❌ Image analysis failed: {e}")
            return self._generate_fallback_results(asset)
    
    async def _analyze_technical_properties(self, image: np.ndarray, pil_image: Image.Image, asset: Dict) -> List[Dict]:
        """Analysiere technische Eigenschaften"""
        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) > 2 else 1
        
        return [{
            'type': 'technical_properties',
            'domain': 'technical',
            'confidence': 1.0,
            'data': {
                'width': width,
                'height': height,
                'channels': channels,
                'aspect_ratio': round(width / height, 3),
                'total_pixels': width * height,
                'file_size': asset.get('file_size', 0),
                'mime_type': asset.get('mime_type', 'unknown')
            },
            'metadata': {'analyzer': 'technical_analyzer'}
        }]
    
    async def _analyze_exif_data(self, pil_image: Image.Image) -> List[Dict]:
        """Analysiere EXIF-Daten"""
        features = []
        
        try:
            exif_data = pil_image._getexif()
            if exif_data:
                exif_dict = {}
                for tag_id, value in exif_data.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    exif_dict[tag] = str(value)
                
                # Wichtige EXIF-Daten extrahieren
                camera_make = exif_dict.get('Make', 'Unknown')
                camera_model = exif_dict.get('Model', 'Unknown')
                exposure_time = exif_dict.get('ExposureTime', 'Unknown')
                f_number = exif_dict.get('FNumber', 'Unknown')
                iso = exif_dict.get('ISOSpeedRatings', 'Unknown')
                focal_length = exif_dict.get('FocalLength', 'Unknown')
                date_taken = exif_dict.get('DateTime', 'Unknown')
                
                features.append({
                    'type': 'exif_metadata',
                    'domain': 'technical',
                    'confidence': 1.0,
                    'data': {
                        'camera_make': camera_make,
                        'camera_model': camera_model,
                        'exposure_time': exposure_time,
                        'f_number': f_number,
                        'iso': iso,
                        'focal_length': focal_length,
                        'date_taken': date_taken,
                        'has_exif': True
                    },
                    'metadata': {'analyzer': 'exif_analyzer'}
                })
            else:
                features.append({
                    'type': 'exif_metadata',
                    'domain': 'technical',
                    'confidence': 1.0,
                    'data': {
                        'has_exif': False
                    },
                    'metadata': {'analyzer': 'exif_analyzer'}
                })
        except Exception as e:
            logger.warning(f"EXIF analysis failed: {e}")
            features.append({
                'type': 'exif_metadata',
                'domain': 'technical',
                'confidence': 0.0,
                'data': {
                    'has_exif': False,
                    'error': str(e)
                },
                'metadata': {'analyzer': 'exif_analyzer'}
            })
        
        return features
    
    async def _analyze_colors(self, image: np.ndarray) -> List[Dict]:
        """Analysiere Farben im Bild"""
        features = []
        
        try:
            # Konvertiere zu RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Reshape für Farbanalyse
            pixels = rgb_image.reshape(-1, 3)
            
            # Dominante Farben finden
            dominant_colors = self._get_dominant_colors(pixels, k=5)
            
            # Farbstatistiken
            mean_color = np.mean(pixels, axis=0)
            std_color = np.std(pixels, axis=0)
            
            # Farbvielfalt berechnen
            color_diversity = len(set(map(tuple, (pixels // 10) * 10)))
            
            features.append({
                'type': 'color_analysis',
                'domain': 'visual',
                'confidence': 0.9,
                'data': {
                    'dominant_colors': dominant_colors,
                    'mean_color': mean_color.tolist(),
                    'color_std': std_color.tolist(),
                    'color_diversity': color_diversity,
                    'brightness': float(np.mean(mean_color)),
                    'saturation': self._calculate_saturation(mean_color)
                },
                'metadata': {'analyzer': 'color_analyzer'}
            })
            
        except Exception as e:
            logger.warning(f"Color analysis failed: {e}")
        
        return features
    
    def _get_dominant_colors(self, pixels: np.ndarray, k: int = 5) -> List[Dict]:
        """Finde dominante Farben mit K-Means"""
        try:
            from sklearn.cluster import KMeans
            
            # Sample für Performance
            if len(pixels) > 10000:
                sample_indices = np.random.choice(len(pixels), 10000, replace=False)
                sample_pixels = pixels[sample_indices]
            else:
                sample_pixels = pixels
            
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(sample_pixels)
            
            colors = kmeans.cluster_centers_.astype(int)
            labels = kmeans.labels_
            
            # Zähle Häufigkeit jeder Farbe
            color_counts = Counter(labels)
            total_pixels = len(labels)
            
            dominant_colors = []
            for i, color in enumerate(colors):
                percentage = (color_counts[i] / total_pixels) * 100
                dominant_colors.append({
                    'rgb': color.tolist(),
                    'percentage': round(percentage, 2)
                })
            
            return sorted(dominant_colors, key=lambda x: x['percentage'], reverse=True)
            
        except ImportError:
            # Fallback ohne sklearn
            return [{'rgb': [128, 128, 128], 'percentage': 100.0}]
        except Exception as e:
            logger.warning(f"Dominant colors analysis failed: {e}")
            return [{'rgb': [128, 128, 128], 'percentage': 100.0}]
    
    def _calculate_saturation(self, rgb_color: np.ndarray) -> float:
        """Berechne Sättigung einer RGB-Farbe"""
        try:
            r, g, b = rgb_color / 255.0
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            return float(s)
        except:
            return 0.0
    
    async def _analyze_objects(self, image: np.ndarray) -> List[Dict]:
        """Analysiere Objekte mit YOLO"""
        features = []
        
        if not self.yolo_model:
            return features
        
        try:
            results = self.yolo_model(image)
            
            objects = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Konfidenz und Klasse
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        class_name = self.yolo_model.names[cls]
                        
                        # Bounding Box
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        
                        objects.append({
                            'class': class_name,
                            'confidence': conf,
                            'bbox': [x1, y1, x2, y2],
                            'area': (x2 - x1) * (y2 - y1)
                        })
            
            if objects:
                features.append({
                    'type': 'object_detection',
                    'domain': 'visual',
                    'confidence': 0.8,
                    'data': {
                        'objects': objects,
                        'object_count': len(objects),
                        'detected_classes': list(set(obj['class'] for obj in objects))
                    },
                    'metadata': {'analyzer': 'yolo_analyzer', 'model': 'yolov8n'}
                })
            
        except Exception as e:
            logger.warning(f"Object detection failed: {e}")
        
        return features
    
    async def _analyze_composition(self, image: np.ndarray) -> List[Dict]:
        """Analysiere Bildkomposition"""
        features = []
        
        try:
            height, width = image.shape[:2]
            
            # Rule of Thirds Analyse
            third_w = width // 3
            third_h = height // 3
            
            # Konvertiere zu Graustufen für Edge-Detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Edge Detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Fokus-Punkte (Bereiche mit vielen Kanten)
            focus_points = self._find_focus_points(edges, third_w, third_h)
            
            # Symmetrie-Analyse
            symmetry_score = self._calculate_symmetry(gray)
            
            features.append({
                'type': 'composition_analysis',
                'domain': 'visual',
                'confidence': 0.7,
                'data': {
                    'rule_of_thirds_points': focus_points,
                    'symmetry_score': symmetry_score,
                    'edge_density': float(np.sum(edges > 0) / (width * height)),
                    'composition_balance': self._analyze_balance(gray)
                },
                'metadata': {'analyzer': 'composition_analyzer'}
            })
            
        except Exception as e:
            logger.warning(f"Composition analysis failed: {e}")
        
        return features
    
    def _find_focus_points(self, edges: np.ndarray, third_w: int, third_h: int) -> List[Dict]:
        """Finde Fokus-Punkte basierend auf Rule of Thirds"""
        focus_points = []
        
        # Rule of Thirds Gitterpunkte
        grid_points = [
            (third_w, third_h),           # Top-left
            (2 * third_w, third_h),       # Top-right
            (third_w, 2 * third_h),       # Bottom-left
            (2 * third_w, 2 * third_h)    # Bottom-right
        ]
        
        for x, y in grid_points:
            # Analysiere Bereich um den Gitterpunkt
            region_size = 50
            x1 = max(0, x - region_size)
            y1 = max(0, y - region_size)
            x2 = min(edges.shape[1], x + region_size)
            y2 = min(edges.shape[0], y + region_size)
            
            region = edges[y1:y2, x1:x2]
            edge_density = float(np.sum(region > 0) / (region_size * region_size * 4))
            
            focus_points.append({
                'x': x,
                'y': y,
                'edge_density': edge_density,
                'is_focus_point': edge_density > 0.1
            })
        
        return focus_points
    
    def _calculate_symmetry(self, gray_image: np.ndarray) -> float:
        """Berechne Symmetrie-Score"""
        try:
            height, width = gray_image.shape
            
            # Vertikale Symmetrie
            left_half = gray_image[:, :width//2]
            right_half = cv2.flip(gray_image[:, width//2:], 1)
            
            # Passe Größe an
            min_width = min(left_half.shape[1], right_half.shape[1])
            left_half = left_half[:, :min_width]
            right_half = right_half[:, :min_width]
            
            vertical_symmetry = 1.0 - np.mean(np.abs(left_half.astype(float) - right_half.astype(float))) / 255.0
            
            # Horizontale Symmetrie
            top_half = gray_image[:height//2, :]
            bottom_half = cv2.flip(gray_image[height//2:, :], 0)
            
            # Passe Größe an
            min_height = min(top_half.shape[0], bottom_half.shape[0])
            top_half = top_half[:min_height, :]
            bottom_half = bottom_half[:min_height, :]
            
            horizontal_symmetry = 1.0 - np.mean(np.abs(top_half.astype(float) - bottom_half.astype(float))) / 255.0
            
            return float((vertical_symmetry + horizontal_symmetry) / 2.0)
            
        except Exception as e:
            logger.warning(f"Symmetry calculation failed: {e}")
            return 0.0
    
    def _analyze_balance(self, gray_image: np.ndarray) -> Dict:
        """Analysiere visuelle Balance"""
        try:
            height, width = gray_image.shape
            
            # Teile Bild in Quadranten
            q1 = gray_image[:height//2, :width//2]  # Top-left
            q2 = gray_image[:height//2, width//2:]  # Top-right
            q3 = gray_image[height//2:, :width//2]  # Bottom-left
            q4 = gray_image[height//2:, width//2:]  # Bottom-right
            
            # Berechne Durchschnitts-Helligkeit für jeden Quadranten
            brightness = {
                'top_left': float(np.mean(q1)),
                'top_right': float(np.mean(q2)),
                'bottom_left': float(np.mean(q3)),
                'bottom_right': float(np.mean(q4))
            }
            
            # Balance-Score
            horizontal_balance = 1.0 - abs(brightness['top_left'] + brightness['bottom_left'] - 
                                         brightness['top_right'] - brightness['bottom_right']) / 255.0
            vertical_balance = 1.0 - abs(brightness['top_left'] + brightness['top_right'] - 
                                        brightness['bottom_left'] - brightness['bottom_right']) / 255.0
            
            return {
                'quadrant_brightness': brightness,
                'horizontal_balance': horizontal_balance,
                'vertical_balance': vertical_balance,
                'overall_balance': (horizontal_balance + vertical_balance) / 2.0
            }
            
        except Exception as e:
            logger.warning(f"Balance analysis failed: {e}")
            return {'overall_balance': 0.5}
    
    async def _analyze_texture(self, image: np.ndarray) -> List[Dict]:
        """Analysiere Textur-Eigenschaften"""
        features = []
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Local Binary Pattern (vereinfacht)
            texture_score = self._calculate_texture_score(gray)
            
            # Gradient-Analyse
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            features.append({
                'type': 'texture_analysis',
                'domain': 'visual',
                'confidence': 0.6,
                'data': {
                    'texture_score': texture_score,
                    'gradient_magnitude': float(np.mean(gradient_magnitude)),
                    'texture_complexity': float(np.std(gradient_magnitude))
                },
                'metadata': {'analyzer': 'texture_analyzer'}
            })
            
        except Exception as e:
            logger.warning(f"Texture analysis failed: {e}")
        
        return features
    
    def _calculate_texture_score(self, gray_image: np.ndarray) -> float:
        """Berechne Textur-Score"""
        try:
            # Vereinfachte Textur-Analyse basierend auf lokalen Variationen
            kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
            texture = cv2.filter2D(gray_image.astype(np.float32), -1, kernel)
            return float(np.std(texture))
        except:
            return 0.0
    
    async def _analyze_brightness_contrast(self, image: np.ndarray) -> List[Dict]:
        """Analysiere Helligkeit und Kontrast"""
        features = []
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Helligkeitsstatistiken
            brightness_mean = float(np.mean(gray))
            brightness_std = float(np.std(gray))
            
            # Kontrast (Standardabweichung der Helligkeit)
            contrast = brightness_std
            
            # Histogramm-Analyse
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = hist.flatten()
            
            # Dynamikbereich
            dynamic_range = float(np.max(gray) - np.min(gray))
            
            features.append({
                'type': 'brightness_contrast_analysis',
                'domain': 'visual',
                'confidence': 0.8,
                'data': {
                    'brightness_mean': brightness_mean,
                    'brightness_std': brightness_std,
                    'contrast': contrast,
                    'dynamic_range': dynamic_range,
                    'histogram_peaks': self._find_histogram_peaks(hist),
                    'exposure_assessment': self._assess_exposure(brightness_mean)
                },
                'metadata': {'analyzer': 'brightness_analyzer'}
            })
            
        except Exception as e:
            logger.warning(f"Brightness/contrast analysis failed: {e}")
        
        return features
    
    def _find_histogram_peaks(self, hist: np.ndarray) -> List[int]:
        """Finde Peaks im Histogramm"""
        try:
            # Einfache Peak-Erkennung
            peaks = []
            for i in range(1, len(hist) - 1):
                if hist[i] > hist[i-1] and hist[i] > hist[i+1] and hist[i] > np.max(hist) * 0.1:
                    peaks.append(int(i))
            return peaks[:5]  # Maximal 5 Peaks
        except:
            return []
    
    def _assess_exposure(self, brightness_mean: float) -> str:
        """Bewerte Belichtung basierend auf Durchschnitts-Helligkeit"""
        if brightness_mean < 50:
            return "under-exposed"
        elif brightness_mean > 200:
            return "over-exposed"
        else:
            return "well-exposed"
    
    def _generate_fallback_results(self, asset: Dict) -> Dict:
        """Generiere Fallback-Ergebnisse bei Fehlern"""
        return {
            'segments': [],
            'features': [{
                'type': 'image_analysis_fallback',
                'domain': 'visual',
                'confidence': 0.1,
                'data': {
                    'status': 'fallback',
                    'error': 'Analysis failed'
                },
                'metadata': {'analyzer': 'fallback'}
            }],
            'embeddings': [],
            'metadata': {'status': 'fallback', 'analyzer': 'fallback'}
        }
