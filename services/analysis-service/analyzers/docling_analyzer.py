"""
Docling Document Analyzer for DataFlux Analysis Service
Advanced document processing using IBM's Docling toolkit
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Any
from PIL import Image
import io

# Docling imports
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

# PDF Thumbnail imports
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

from .base import BaseAnalyzer

# Import monitoring
try:
    from ..src.document_monitoring import record_document_processing
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

logger = logging.getLogger(__name__)


class DoclingAnalyzer(BaseAnalyzer):
    """
    Advanced document analyzer using IBM's Docling toolkit
    Provides comprehensive document processing with layout analysis, OCR, and structured extraction
    """
    
    def __init__(self):
        super().__init__()
        
        if not DOCLING_AVAILABLE:
            logger.warning("Docling not available. Install with: pip install docling")
            self.converter = None
        else:
            # Initialize Docling converter with optimized settings
            self.converter = DocumentConverter()
            
            # Configure PDF pipeline options for better performance
            pdf_options = PdfPipelineOptions()
            pdf_options.do_ocr = True
            pdf_options.do_table_structure = True
            # Note: do_cell_merging is not available in current Docling version
            
            self.converter.pipeline_options = {
                InputFormat.PDF: pdf_options
            }
            
            # Performance optimizations
            self._cache = {}  # Simple cache for repeated documents
            self._max_cache_size = 100
        
        # Supported formats by Docling
        self.supported_formats = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # DOCX
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # PPTX
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # XLSX
            'text/html',
            'text/plain',
            'image/png',
            'image/jpeg',
            'image/tiff',
            'application/vnd.ms-excel',  # XLS
            'application/msword',  # DOC
            'application/vnd.ms-powerpoint',  # PPT
        ]
    
    def get_supported_formats(self) -> List[str]:
        """Return list of supported MIME types"""
        return self.supported_formats
    
    async def analyze(self, file_path: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze document using Docling"""
        self.log_analysis_start(file_path, asset_data)
        
        try:
            if not self.validate_file(file_path):
                return self.create_error_result("Invalid file")
            
            if not DOCLING_AVAILABLE:
                return self.create_error_result("Docling not available")
            
            # Run Docling analysis tasks
            tasks = [
                self._convert_document(file_path),
                self._extract_metadata(file_path),
                self._analyze_structure(file_path)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            segments = []
            features = []
            embeddings = []
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Docling analysis task failed: {str(result)}")
                    continue
                
                if isinstance(result, dict):
                    segments.extend(result.get('segments', []))
                    features.extend(result.get('features', []))
                    embeddings.extend(result.get('embeddings', []))
            
            # Generate PDF thumbnails if it's a PDF
            thumbnail_info = {}
            if file_path.lower().endswith('.pdf') and PDF2IMAGE_AVAILABLE:
                try:
                    asset_id = asset_data.get('id', 'unknown')
                    thumbnail_base_dir = "/tmp/dataflux_thumbnails"
                    
                    thumbnail_result = self.generate_multiple_pdf_thumbnails(
                        file_path, 
                        thumbnail_base_dir, 
                        asset_id
                    )
                    
                    if thumbnail_result['success']:
                        thumbnail_info = {
                            'thumbnails_generated': True,
                            'thumbnail_count': thumbnail_result['generated_count'],
                            'thumbnails': thumbnail_result['thumbnails']
                        }
                        logger.info(f"✅ Generated {thumbnail_result['generated_count']} PDF thumbnails")
                    else:
                        logger.warning(f"⚠️ PDF thumbnail generation failed: {thumbnail_result.get('error', 'Unknown error')}")
                        thumbnail_info = {
                            'thumbnails_generated': False,
                            'error': thumbnail_result.get('error', 'Unknown error')
                        }
                        
                except Exception as e:
                    logger.error(f"❌ PDF thumbnail generation error: {e}")
                    thumbnail_info = {
                        'thumbnails_generated': False,
                        'error': str(e)
                    }
            elif file_path.lower().endswith('.pdf') and not PDF2IMAGE_AVAILABLE:
                logger.warning("⚠️ PDF thumbnail generation skipped: pdf2image not available")
                thumbnail_info = {
                    'thumbnails_generated': False,
                    'error': 'pdf2image not available'
                }
            
            result = self.create_success_result(
                segments=segments,
                features=features,
                embeddings=embeddings,
                metadata={
                    'docling_version': '1.0.0',
                    'document_info': await self._get_document_info(file_path),
                    'processing_method': 'docling',
                    'thumbnail_info': thumbnail_info
                }
            )
            
            self.log_analysis_end(file_path, result)
            return result
            
        except Exception as e:
            logger.error(f"Docling analysis failed: {str(e)}")
            return self.create_error_result(str(e))
    
    async def _convert_document(self, file_path: str) -> Dict[str, Any]:
        """Convert document using Docling and extract structured content"""
        try:
            # Check cache first for performance
            import hashlib
            file_hash = hashlib.md5(open(file_path, 'rb').read()).hexdigest()
            
            if file_hash in self._cache:
                logger.info(f"Using cached result for {file_path}")
                return self._cache[file_hash]
            
            # Convert document to Docling format
            result = self.converter.convert(file_path)
            
            segments = []
            features = []
            
            # Extract text segments from the document
            if hasattr(result, 'document') and result.document:
                doc = result.document
                
                # Extract text elements
                if hasattr(doc, 'texts') and doc.texts:
                    for i, text_elem in enumerate(doc.texts):
                        segment = {
                            'type': 'text',
                            'start_time': 0.0,
                            'end_time': 0.0,
                            'confidence': 0.9,
                            'metadata': {
                                'text': text_elem.text if hasattr(text_elem, 'text') else str(text_elem),
                                'element_type': 'text',
                                'index': i
                            }
                        }
                        segments.append(segment)
                
                # Extract tables
                if hasattr(doc, 'tables') and doc.tables:
                    for i, table in enumerate(doc.tables):
                        segment = {
                            'type': 'table',
                            'start_time': 0.0,
                            'end_time': 0.0,
                            'confidence': 0.9,
                            'metadata': {
                                'element_type': 'table',
                                'index': i,
                                'table_data': str(table)[:200] + '...' if len(str(table)) > 200 else str(table)
                            }
                        }
                        segments.append(segment)
                
                # Extract figures
                if hasattr(doc, 'figures') and doc.figures:
                    for i, figure in enumerate(doc.figures):
                        segment = {
                            'type': 'figure',
                            'start_time': 0.0,
                            'end_time': 0.0,
                            'confidence': 0.9,
                            'metadata': {
                                'element_type': 'figure',
                                'index': i,
                                'figure_info': str(figure)[:200] + '...' if len(str(figure)) > 200 else str(figure)
                            }
                        }
                        segments.append(segment)
            
            # Extract document-level features
            total_elements = len(segments)
            has_tables = any(s['type'] == 'table' for s in segments)
            has_images = any(s['type'] == 'figure' for s in segments)
            
            features.append({
                'type': 'document_structure',
                'domain': 'document',
                'confidence': 0.9,
                'data': {
                    'total_elements': total_elements,
                    'has_tables': has_tables,
                    'has_images': has_images,
                    'has_code': False,  # Could be enhanced
                    'has_formulas': False,  # Could be enhanced
                    'page_count': 1  # HTML is single page
                },
                'metadata': {'analyzer': 'docling_structure'}
            })
            
            # Extract text content for further analysis
            full_text = ' '.join([s['metadata']['text'] for s in segments if s['type'] == 'text' and 'text' in s['metadata']])
            
            # Enhanced text analysis
            text_features = self._analyze_text_content(full_text)
            
            features.append({
                'type': 'text_content',
                'domain': 'text',
                'confidence': 0.8,
                'data': {
                    'text_length': len(full_text),
                    'word_count': len(full_text.split()),
                    'has_text': len(full_text) > 0,
                    'language_detected': text_features.get('language', 'en'),
                    'sentiment_score': text_features.get('sentiment', 0.0),
                    'readability_score': text_features.get('readability', 0.0),
                    'topic_keywords': text_features.get('keywords', []),
                    'document_type': text_features.get('document_type', 'unknown')
                },
                'metadata': {'analyzer': 'docling_text'}
            })
            
            # Add document classification features
            features.append({
                'type': 'document_classification',
                'domain': 'semantic',
                'confidence': 0.7,
                'data': {
                    'is_technical_document': self._is_technical_document(full_text),
                    'is_financial_document': self._is_financial_document(full_text),
                    'is_legal_document': self._is_legal_document(full_text),
                    'is_academic_paper': self._is_academic_paper(full_text),
                    'complexity_level': self._calculate_complexity(full_text),
                    'formality_level': self._calculate_formality(full_text)
                },
                'metadata': {'analyzer': 'docling_classification'}
            })
            
            # Cache the result for future use
            if len(self._cache) >= self._max_cache_size:
                # Remove oldest entry (simple LRU)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            result_data = {
                'segments': segments,
                'features': features,
                'embeddings': []
            }
            
            self._cache[file_hash] = result_data
            return result_data
            
        except Exception as e:
            logger.error(f"Document conversion failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract document metadata"""
        try:
            import os
            from datetime import datetime
            
            stat = os.stat(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            features = [{
                'type': 'document_metadata',
                'domain': 'metadata',
                'confidence': 0.9,
                'data': {
                    'file_size': stat.st_size,
                    'file_extension': file_ext,
                    'creation_date': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modification_date': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'access_date': datetime.fromtimestamp(stat.st_atime).isoformat(),
                    'file_name': os.path.basename(file_path)
                },
                'metadata': {'analyzer': 'docling_metadata'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _analyze_structure(self, file_path: str) -> Dict[str, Any]:
        """Analyze document structure and layout"""
        try:
            # This would analyze the document structure in more detail
            # For now, we'll create a basic structure analysis
            
            features = [{
                'type': 'layout_analysis',
                'domain': 'structure',
                'confidence': 0.7,
                'data': {
                    'layout_type': 'unknown',  # Could be enhanced with layout detection
                    'has_headers': False,  # Could be detected from structure
                    'has_footers': False,
                    'has_columns': False,
                    'complexity_score': 0.5  # Could be calculated based on structure
                },
                'metadata': {'analyzer': 'docling_layout'}
            }]
            
            return {
                'segments': [],
                'features': features,
                'embeddings': []
            }
            
        except Exception as e:
            logger.error(f"Structure analysis failed: {str(e)}")
            return {'segments': [], 'features': [], 'embeddings': []}
    
    async def _get_document_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic document information"""
        try:
            import os
            stat = os.stat(file_path)
            
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'extension': os.path.splitext(file_path)[1],
                'analyzer_type': 'docling'
            }
        except Exception as e:
            logger.error(f"Failed to get document info: {str(e)}")
            return {}
    
    def validate_file(self, file_path: str) -> bool:
        """Validate that the file can be processed by Docling"""
        try:
            if not os.path.exists(file_path):
                return False
            
            # Check file size (reasonable limit)
            stat = os.stat(file_path)
            if stat.st_size > 100 * 1024 * 1024:  # 100MB limit
                logger.warning(f"File too large for processing: {stat.st_size} bytes")
                return False
            
            # Check file extension
            ext = os.path.splitext(file_path)[1].lower()
            supported_extensions = ['.pdf', '.docx', '.pptx', '.xlsx', '.html', '.txt', '.png', '.jpg', '.jpeg', '.tiff', '.xls', '.doc', '.ppt']
            
            return ext in supported_extensions
            
        except Exception as e:
            logger.error(f"File validation failed: {str(e)}")
            return False
    
    def clear_cache(self):
        """Clear the document processing cache"""
        self._cache.clear()
        logger.info("DoclingAnalyzer cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        return {
            'cache_size': len(self._cache),
            'max_cache_size': self._max_cache_size,
            'cache_utilization': len(self._cache) / self._max_cache_size
        }
    
    def _analyze_text_content(self, text: str) -> Dict[str, Any]:
        """Analyze text content for enhanced features"""
        try:
            if not text or len(text.strip()) == 0:
                return {'language': 'unknown', 'sentiment': 0.0, 'readability': 0.0, 'keywords': [], 'document_type': 'empty'}
            
            # Basic language detection (simplified)
            language = self._detect_language(text)
            
            # Basic sentiment analysis (simplified)
            sentiment = self._calculate_sentiment(text)
            
            # Basic readability score (simplified Flesch Reading Ease)
            readability = self._calculate_readability(text)
            
            # Extract keywords (simplified)
            keywords = self._extract_keywords(text)
            
            # Determine document type
            document_type = self._classify_document_type(text)
            
            return {
                'language': language,
                'sentiment': sentiment,
                'readability': readability,
                'keywords': keywords,
                'document_type': document_type
            }
            
        except Exception as e:
            logger.error(f"Text analysis failed: {str(e)}")
            return {'language': 'en', 'sentiment': 0.0, 'readability': 0.0, 'keywords': [], 'document_type': 'unknown'}
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection"""
        # Basic heuristics for common languages
        text_lower = text.lower()
        
        # German indicators
        german_words = ['der', 'die', 'das', 'und', 'ist', 'mit', 'für', 'von', 'auf', 'an']
        german_count = sum(1 for word in german_words if word in text_lower)
        
        # French indicators
        french_words = ['le', 'la', 'les', 'de', 'du', 'des', 'et', 'est', 'avec', 'pour']
        french_count = sum(1 for word in french_words if word in text_lower)
        
        # Spanish indicators
        spanish_words = ['el', 'la', 'los', 'las', 'de', 'del', 'y', 'es', 'con', 'para']
        spanish_count = sum(1 for word in spanish_words if word in text_lower)
        
        if german_count > max(french_count, spanish_count, 2):
            return 'de'
        elif french_count > max(spanish_count, 2):
            return 'fr'
        elif spanish_count > 2:
            return 'es'
        else:
            return 'en'  # Default to English
    
    def _calculate_sentiment(self, text: str) -> float:
        """Simple sentiment analysis"""
        try:
            # Basic sentiment analysis using word lists
            positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'positive', 'success', 'win', 'best']
            negative_words = ['bad', 'terrible', 'awful', 'horrible', 'negative', 'failure', 'lose', 'worst', 'problem', 'issue']
            
            text_lower = text.lower()
            words = text_lower.split()
            
            positive_count = sum(1 for word in words if word in positive_words)
            negative_count = sum(1 for word in words if word in negative_words)
            
            total_words = len(words)
            if total_words == 0:
                return 0.0
            
            # Normalize sentiment score between -1 and 1
            sentiment_score = (positive_count - negative_count) / total_words
            return max(-1.0, min(1.0, sentiment_score * 10))  # Scale and clamp
            
        except Exception:
            return 0.0
    
    def _calculate_readability(self, text: str) -> float:
        """Calculate readability score (simplified Flesch Reading Ease)"""
        try:
            sentences = text.split('.')
            words = text.split()
            
            if len(sentences) == 0 or len(words) == 0:
                return 0.0
            
            # Count syllables (simplified)
            syllables = 0
            for word in words:
                syllables += max(1, len([c for c in word.lower() if c in 'aeiou']))
            
            # Simplified Flesch Reading Ease formula
            avg_sentence_length = len(words) / len(sentences)
            avg_syllables_per_word = syllables / len(words)
            
            readability = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
            
            # Normalize to 0-1 scale
            return max(0.0, min(1.0, readability / 100.0))
            
        except Exception:
            return 0.5  # Default moderate readability
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text"""
        try:
            # Simple keyword extraction using word frequency
            words = text.lower().split()
            
            # Remove common stop words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
            
            filtered_words = [word for word in words if len(word) > 3 and word not in stop_words]
            
            # Count word frequency
            word_freq = {}
            for word in filtered_words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # Sort by frequency and return top keywords
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            return [word for word, freq in sorted_words[:max_keywords]]
            
        except Exception:
            return []
    
    def _classify_document_type(self, text: str) -> str:
        """Classify document type based on content"""
        try:
            text_lower = text.lower()
            
            # Technical document indicators
            tech_keywords = ['api', 'function', 'method', 'class', 'variable', 'algorithm', 'code', 'programming', 'software', 'system']
            tech_score = sum(1 for keyword in tech_keywords if keyword in text_lower)
            
            # Financial document indicators
            finance_keywords = ['revenue', 'profit', 'loss', 'budget', 'financial', 'accounting', 'balance', 'income', 'expense', 'investment']
            finance_score = sum(1 for keyword in finance_keywords if keyword in text_lower)
            
            # Legal document indicators
            legal_keywords = ['agreement', 'contract', 'terms', 'conditions', 'liability', 'legal', 'court', 'law', 'regulation', 'compliance']
            legal_score = sum(1 for keyword in legal_keywords if keyword in text_lower)
            
            # Academic paper indicators
            academic_keywords = ['research', 'study', 'analysis', 'hypothesis', 'methodology', 'conclusion', 'abstract', 'references', 'citation', 'university']
            academic_score = sum(1 for keyword in academic_keywords if keyword in text_lower)
            
            # Determine document type
            scores = {
                'technical': tech_score,
                'financial': finance_score,
                'legal': legal_score,
                'academic': academic_score
            }
            
            max_score = max(scores.values())
            if max_score > 2:
                return max(scores, key=scores.get)
            else:
                return 'general'
                
        except Exception:
            return 'unknown'
    
    def _is_technical_document(self, text: str) -> bool:
        """Check if document is technical"""
        return self._classify_document_type(text) == 'technical'
    
    def _is_financial_document(self, text: str) -> bool:
        """Check if document is financial"""
        return self._classify_document_type(text) == 'financial'
    
    def _is_legal_document(self, text: str) -> bool:
        """Check if document is legal"""
        return self._classify_document_type(text) == 'legal'
    
    def _is_academic_paper(self, text: str) -> bool:
        """Check if document is academic"""
        return self._classify_document_type(text) == 'academic'
    
    def _calculate_complexity(self, text: str) -> float:
        """Calculate document complexity (0-1 scale)"""
        try:
            # Factors: sentence length, word length, vocabulary diversity
            sentences = text.split('.')
            words = text.split()
            
            if len(sentences) == 0 or len(words) == 0:
                return 0.0
            
            # Average sentence length
            avg_sentence_length = len(words) / len(sentences)
            
            # Average word length
            avg_word_length = sum(len(word) for word in words) / len(words)
            
            # Vocabulary diversity (unique words / total words)
            vocabulary_diversity = len(set(words)) / len(words)
            
            # Combine factors (normalized)
            complexity = (
                min(avg_sentence_length / 20.0, 1.0) * 0.4 +  # Sentence length factor
                min(avg_word_length / 8.0, 1.0) * 0.3 +        # Word length factor
                vocabulary_diversity * 0.3                     # Vocabulary diversity factor
            )
            
            return max(0.0, min(1.0, complexity))
            
        except Exception:
            return 0.5
    
    def _calculate_formality(self, text: str) -> float:
        """Calculate formality level (0-1 scale)"""
        try:
            text_lower = text.lower()
            
            # Formal indicators
            formal_words = ['therefore', 'however', 'furthermore', 'moreover', 'consequently', 'nevertheless', 'accordingly', 'subsequently']
            formal_count = sum(1 for word in formal_words if word in text_lower)
            
            # Informal indicators
            informal_words = ['hey', 'yeah', 'okay', 'cool', 'awesome', 'gonna', 'wanna', 'gotta', 'kinda', 'sorta']
            informal_count = sum(1 for word in informal_words if word in text_lower)
            
            # Contractions
            contractions = ["don't", "won't", "can't", "isn't", "aren't", "wasn't", "weren't", "haven't", "hasn't", "hadn't"]
            contraction_count = sum(1 for contraction in contractions if contraction in text_lower)
            
            total_words = len(text.split())
            if total_words == 0:
                return 0.5
            
            # Calculate formality score
            formality_score = (
                (formal_count / total_words) * 0.5 +           # Formal words boost formality
                (informal_count / total_words) * -0.3 +        # Informal words reduce formality
                (contraction_count / total_words) * -0.2       # Contractions reduce formality
            )
            
            return max(0.0, min(1.0, 0.5 + formality_score))
            
        except Exception:
            return 0.5
    
    def generate_pdf_thumbnail(self, pdf_path: str, thumbnail_path: str, size: tuple = (300, 200)) -> Dict[str, Any]:
        """
        Generate thumbnail from PDF first page
        
        Args:
            pdf_path: Path to PDF file
            thumbnail_path: Path where thumbnail should be saved
            size: Thumbnail size (width, height)
            
        Returns:
            Dict with success status and metadata
        """
        try:
            if not PDF2IMAGE_AVAILABLE:
                logger.warning("pdf2image not available. Install with: pip install pdf2image")
                return {
                    'success': False,
                    'error': 'pdf2image not available',
                    'generated': False
                }
            
            logger.info(f"🖼️ Generating PDF thumbnail for {pdf_path}")
            
            # Convert first page of PDF to image
            images = convert_from_path(
                pdf_path,
                first_page=1,
                last_page=1,
                dpi=150,  # Good quality for thumbnails
                fmt='RGB'
            )
            
            if not images:
                logger.error(f"No images generated from PDF: {pdf_path}")
                return {
                    'success': False,
                    'error': 'No images generated from PDF',
                    'generated': False
                }
            
            # Get first page image
            pdf_image = images[0]
            
            # Convert to RGB if necessary
            if pdf_image.mode in ('RGBA', 'LA', 'P'):
                # Create a white background
                background = Image.new('RGB', pdf_image.size, (255, 255, 255))
                if pdf_image.mode == 'P':
                    pdf_image = pdf_image.convert('RGBA')
                background.paste(pdf_image, mask=pdf_image.split()[-1] if pdf_image.mode == 'RGBA' else None)
                pdf_image = background
            elif pdf_image.mode != 'RGB':
                pdf_image = pdf_image.convert('RGB')
            
            # Create thumbnail maintaining aspect ratio
            pdf_image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Ensure thumbnail directory exists
            os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
            
            # Save thumbnail
            pdf_image.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
            
            logger.info(f"✅ PDF thumbnail generated: {thumbnail_path} ({pdf_image.size})")
            
            return {
                'success': True,
                'thumbnail_path': thumbnail_path,
                'dimensions': pdf_image.size,
                'generated': True,
                'source': 'pdf_first_page'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate PDF thumbnail: {e}")
            return {
                'success': False,
                'error': str(e),
                'generated': False
            }
    
    def generate_multiple_pdf_thumbnails(self, pdf_path: str, base_directory: str, asset_id: str) -> Dict[str, Any]:
        """
        Generate multiple PDF thumbnail sizes for different use cases
        
        Args:
            pdf_path: Path to PDF file
            base_directory: Base directory for thumbnails
            asset_id: Asset ID for naming
            
        Returns:
            Dict with generated thumbnails info
        """
        
        # Define thumbnail sizes for different use cases
        thumbnail_sizes = {
            'small': (150, 100),    # Grid view thumbnails
            'medium': (400, 300),   # List view thumbnails  
            'large': (1200, 800)    # Modal background images
        }
        
        generated_thumbnails = {}
        
        try:
            os.makedirs(base_directory, exist_ok=True)
            
            for size_name, size in thumbnail_sizes.items():
                thumbnail_filename = f"{asset_id}_{size_name}_thumbnail.jpg"
                thumbnail_path = os.path.join(base_directory, thumbnail_filename)
                
                result = self.generate_pdf_thumbnail(pdf_path, thumbnail_path, size)
                
                if result['success']:
                    generated_thumbnails[size_name] = {
                        'path': thumbnail_path,
                        'size': size,
                        'dimensions': result['dimensions'],
                        'filename': thumbnail_filename
                    }
                    logger.info(f"✅ Generated {size_name} PDF thumbnail: {thumbnail_filename}")
                else:
                    logger.warning(f"⚠️ Failed to generate {size_name} PDF thumbnail: {result.get('error', 'Unknown error')}")
            
            return {
                'success': len(generated_thumbnails) > 0,
                'thumbnails': generated_thumbnails,
                'generated_count': len(generated_thumbnails),
                'total_requested': len(thumbnail_sizes)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate multiple PDF thumbnails: {e}")
            return {
                'success': False,
                'error': str(e),
                'thumbnails': {},
                'generated_count': 0,
                'total_requested': len(thumbnail_sizes)
            }
