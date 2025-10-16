#!/usr/bin/env python3
"""
Video Summarization mit LLM (GPT-4o/Claude 3.5)
"""

import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class VideoSummary:
    """Video Summary Result"""
    brief_summary: str
    detailed_summary: str
    keywords: List[str]
    topics: List[str]
    sentiment: str
    confidence: float
    llm_used: str
    processing_time: float
    cost_estimate: Optional[float] = None

@dataclass
class SummarizationConfig:
    """Configuration for video summarization"""
    llm_provider: str = "openai"  # openai, anthropic, local
    model_name: str = "gpt-4o"
    max_tokens: int = 4000
    temperature: float = 0.7
    enable_cost_tracking: bool = True
    fallback_to_template: bool = True

class VideoSummarizer:
    """LLM-based Video Summarization"""
    
    def __init__(self, config: Optional[SummarizationConfig] = None):
        self.config = config or SummarizationConfig()
        self.api_keys = {}
        self.cost_tracker = {}
        
        logger.info(f"VideoSummarizer initialized with {self.config.llm_provider}")
    
    def set_api_key(self, provider: str, api_key: str):
        """Set API key for LLM provider"""
        self.api_keys[provider] = api_key
        logger.info(f"API key set for {provider}")
    
    async def generate_summary(self, 
                             video_analysis: Dict[str, Any],
                             config: Optional[SummarizationConfig] = None) -> VideoSummary:
        """
        Generate video summary from analysis results
        
        Args:
            video_analysis: Complete video analysis results
            config: Optional custom configuration
        
        Returns:
            VideoSummary object
        """
        config = config or self.config
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Prepare context for LLM
            context = self._prepare_context(video_analysis)
            
            # Generate prompt
            prompt = self._create_summarization_prompt(context)
            
            # Call LLM
            if config.llm_provider == "openai":
                result = await self._call_openai(prompt, config)
            elif config.llm_provider == "anthropic":
                result = await self._call_anthropic(prompt, config)
            elif config.llm_provider == "local":
                result = await self._call_local_llm(prompt, config)
            else:
                raise ValueError(f"Unknown LLM provider: {config.llm_provider}")
            
            # Parse LLM response
            summary = self._parse_llm_response(result, config)
            
            # Calculate processing time
            processing_time = asyncio.get_event_loop().time() - start_time
            summary.processing_time = processing_time
            
            logger.info(f"Video summary generated in {processing_time:.2f}s")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating video summary: {e}")
            
            # Fallback to template-based summary
            if config.fallback_to_template:
                logger.info("Falling back to template-based summary")
                return self._generate_template_summary(video_analysis, config)
            else:
                raise
    
    def _prepare_context(self, video_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context from video analysis"""
        context = {
            "duration": video_analysis.get("duration", 0),
            "total_scenes": len(video_analysis.get("scenes", [])),
            "total_frames": len(video_analysis.get("frame_analyses", [])),
            "features_count": len(video_analysis.get("features", [])),
            "embeddings_count": len(video_analysis.get("embeddings", []))
        }
        
        # Extract transcript if available
        transcript = self._extract_transcript(video_analysis)
        context["transcript"] = transcript
        
        # Extract visual content
        visual_content = self._extract_visual_content(video_analysis)
        context["visual_content"] = visual_content
        
        # Extract scene information
        scenes_info = self._extract_scenes_info(video_analysis)
        context["scenes"] = scenes_info
        
        # Extract detected objects
        objects_info = self._extract_objects_info(video_analysis)
        context["objects"] = objects_info
        
        # Extract faces
        faces_info = self._extract_faces_info(video_analysis)
        context["faces"] = faces_info
        
        # Extract actions if available
        actions_info = self._extract_actions_info(video_analysis)
        context["actions"] = actions_info
        
        return context
    
    def _extract_transcript(self, video_analysis: Dict[str, Any]) -> str:
        """Extract transcript from video analysis"""
        # Look for audio analysis results
        features = video_analysis.get("features", [])
        
        for feature in features:
            if feature.get("type") == "audio_analysis":
                audio_data = feature.get("data", {})
                transcript = audio_data.get("transcript", "")
                if transcript:
                    return transcript
        
        return "No transcript available"
    
    def _extract_visual_content(self, video_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract visual content information"""
        visual_content = {
            "objects": [],
            "faces": [],
            "text": [],
            "scenes": []
        }
        
        features = video_analysis.get("features", [])
        
        for feature in features:
            feature_type = feature.get("type", "")
            feature_data = feature.get("data", {})
            
            if "object_detection" in feature_type:
                objects = feature_data.get("objects", [])
                visual_content["objects"].extend(objects)
            
            elif "face_recognition" in feature_type:
                faces = feature_data.get("faces", [])
                visual_content["faces"].extend(faces)
            
            elif "ocr" in feature_type:
                text = feature_data.get("text", [])
                visual_content["text"].extend(text)
            
            elif "scene_classification" in feature_type:
                scene_info = feature_data.get("scene", "")
                if scene_info:
                    visual_content["scenes"].append(scene_info)
        
        return visual_content
    
    def _extract_scenes_info(self, video_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract scene information"""
        scenes = video_analysis.get("scenes", [])
        scenes_info = []
        
        for scene in scenes:
            scene_info = {
                "start_time": scene.get("start_time", 0),
                "end_time": scene.get("end_time", 0),
                "duration": scene.get("duration", 0),
                "features_count": len(scene.get("features", []))
            }
            scenes_info.append(scene_info)
        
        return scenes_info
    
    def _extract_objects_info(self, video_analysis: Dict[str, Any]) -> Dict[str, int]:
        """Extract object detection statistics"""
        object_counts = {}
        
        features = video_analysis.get("features", [])
        
        for feature in features:
            if "object_detection" in feature.get("type", ""):
                objects = feature.get("data", {}).get("objects", [])
                for obj in objects:
                    obj_class = obj.get("class", "unknown")
                    object_counts[obj_class] = object_counts.get(obj_class, 0) + 1
        
        return object_counts
    
    def _extract_faces_info(self, video_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract face recognition statistics"""
        face_stats = {
            "total_faces": 0,
            "unique_people": 0,
            "emotions": {},
            "age_groups": {}
        }
        
        features = video_analysis.get("features", [])
        
        for feature in features:
            if "face_recognition" in feature.get("type", ""):
                faces = feature.get("data", {}).get("faces", [])
                face_stats["total_faces"] += len(faces)
                
                for face in faces:
                    emotion = face.get("emotion", "unknown")
                    face_stats["emotions"][emotion] = face_stats["emotions"].get(emotion, 0) + 1
                    
                    age = face.get("age", 0)
                    if age > 0:
                        age_group = self._get_age_group(age)
                        face_stats["age_groups"][age_group] = face_stats["age_groups"].get(age_group, 0) + 1
        
        return face_stats
    
    def _extract_actions_info(self, video_analysis: Dict[str, Any]) -> Dict[str, int]:
        """Extract action recognition statistics"""
        action_counts = {}
        
        features = video_analysis.get("features", [])
        
        for feature in features:
            if "action_recognition" in feature.get("type", ""):
                actions = feature.get("data", {}).get("actions", [])
                for action in actions:
                    action_name = action.get("action_name", "unknown")
                    action_counts[action_name] = action_counts.get(action_name, 0) + 1
        
        return action_counts
    
    def _get_age_group(self, age: int) -> str:
        """Convert age to age group"""
        if age < 18:
            return "child"
        elif age < 30:
            return "young_adult"
        elif age < 50:
            return "adult"
        else:
            return "senior"
    
    def _create_summarization_prompt(self, context: Dict[str, Any]) -> str:
        """Create prompt for LLM summarization"""
        prompt = f"""
Analyze this video and provide a comprehensive summary.

Video Information:
- Duration: {context.get('duration', 0):.1f} seconds
- Total Scenes: {context.get('total_scenes', 0)}
- Total Frames Analyzed: {context.get('total_frames', 0)}

Transcript:
{context.get('transcript', 'No transcript available')}

Visual Content:
- Detected Objects: {context.get('objects', {})}
- Faces Detected: {context.get('faces', {})}
- Actions Performed: {context.get('actions', {})}
- Text Found: {len(context.get('visual_content', {}).get('text', []))} text elements

Scene Breakdown:
{self._format_scenes_info(context.get('scenes', []))}

Please provide:

1. Brief Summary (2-3 sentences): A concise overview of what happens in the video
2. Detailed Summary (1 paragraph): A comprehensive description of the video content
3. Keywords (10-15 tags): Important terms and concepts
4. Main Topics: The primary subjects or themes
5. Sentiment Analysis: Overall mood/tone (positive/negative/neutral)

Format your response as JSON:
{{
    "brief_summary": "...",
    "detailed_summary": "...",
    "keywords": ["keyword1", "keyword2", ...],
    "topics": ["topic1", "topic2", ...],
    "sentiment": "positive/negative/neutral"
}}
"""
        return prompt
    
    def _format_scenes_info(self, scenes: List[Dict[str, Any]]) -> str:
        """Format scenes information for prompt"""
        if not scenes:
            return "No scene information available"
        
        formatted_scenes = []
        for i, scene in enumerate(scenes[:5]):  # Limit to first 5 scenes
            formatted_scenes.append(
                f"Scene {i+1}: {scene.get('start_time', 0):.1f}s - {scene.get('end_time', 0):.1f}s "
                f"({scene.get('duration', 0):.1f}s duration)"
            )
        
        return "\n".join(formatted_scenes)
    
    async def _call_openai(self, prompt: str, config: SummarizationConfig) -> str:
        """Call OpenAI API"""
        if "openai" not in self.api_keys:
            raise ValueError("OpenAI API key not set")
        
        headers = {
            "Authorization": f"Bearer {self.api_keys['openai']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": config.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": config.max_tokens,
            "temperature": config.temperature
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error: {response.status} - {error_text}")
                
                result = await response.json()
                return result["choices"][0]["message"]["content"]
    
    async def _call_anthropic(self, prompt: str, config: SummarizationConfig) -> str:
        """Call Anthropic API"""
        if "anthropic" not in self.api_keys:
            raise ValueError("Anthropic API key not set")
        
        headers = {
            "x-api-key": self.api_keys["anthropic"],
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": config.model_name,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API error: {response.status} - {error_text}")
                
                result = await response.json()
                return result["content"][0]["text"]
    
    async def _call_local_llm(self, prompt: str, config: SummarizationConfig) -> str:
        """Call local LLM (placeholder)"""
        # This would integrate with local LLM like LLaMA, Qwen, etc.
        # For now, return a placeholder response
        logger.warning("Local LLM not implemented, using fallback")
        return json.dumps({
            "brief_summary": "Video analysis completed",
            "detailed_summary": "This video contains visual content that has been analyzed.",
            "keywords": ["video", "analysis", "content"],
            "topics": ["visual content"],
            "sentiment": "neutral"
        })
    
    def _parse_llm_response(self, response: str, config: SummarizationConfig) -> VideoSummary:
        """Parse LLM response into VideoSummary object"""
        try:
            # Try to parse as JSON
            data = json.loads(response)
            
            return VideoSummary(
                brief_summary=data.get("brief_summary", ""),
                detailed_summary=data.get("detailed_summary", ""),
                keywords=data.get("keywords", []),
                topics=data.get("topics", []),
                sentiment=data.get("sentiment", "neutral"),
                confidence=0.9,  # High confidence for LLM responses
                llm_used=config.model_name
            )
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON, using fallback")
            return self._create_fallback_summary(response, config)
    
    def _create_fallback_summary(self, response: str, config: SummarizationConfig) -> VideoSummary:
        """Create fallback summary from raw LLM response"""
        return VideoSummary(
            brief_summary=response[:200] + "..." if len(response) > 200 else response,
            detailed_summary=response,
            keywords=["video", "content", "analysis"],
            topics=["visual content"],
            sentiment="neutral",
            confidence=0.5,
            llm_used=config.model_name
        )
    
    def _generate_template_summary(self, 
                                 video_analysis: Dict[str, Any], 
                                 config: SummarizationConfig) -> VideoSummary:
        """Generate template-based summary as fallback"""
        duration = video_analysis.get("duration", 0)
        scenes_count = len(video_analysis.get("scenes", []))
        features_count = len(video_analysis.get("features", []))
        
        # Extract basic information
        objects = self._extract_objects_info(video_analysis)
        faces = self._extract_faces_info(video_analysis)
        
        # Generate template summary
        brief_summary = f"This {duration:.1f}-second video contains {scenes_count} scenes with {features_count} analyzed features."
        
        detailed_summary = f"""
This video has a duration of {duration:.1f} seconds and is divided into {scenes_count} scenes. 
The analysis detected {len(objects)} different types of objects and {faces.get('total_faces', 0)} faces.
The video contains rich visual content that has been processed through multiple analysis pipelines.
"""
        
        # Generate keywords from detected content
        keywords = list(objects.keys())[:10]  # Top 10 object types
        if faces.get('total_faces', 0) > 0:
            keywords.append("people")
        
        topics = ["visual content", "object detection"]
        if faces.get('total_faces', 0) > 0:
            topics.append("people")
        
        return VideoSummary(
            brief_summary=brief_summary,
            detailed_summary=detailed_summary,
            keywords=keywords,
            topics=topics,
            sentiment="neutral",
            confidence=0.6,
            llm_used="template_fallback",
            processing_time=0.1
        )
