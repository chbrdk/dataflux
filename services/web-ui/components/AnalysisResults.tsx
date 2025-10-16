import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Brain, Clock, CheckCircle, AlertCircle, XCircle, BarChart3, Target, Info, ChevronDown, ChevronUp, X, User, Users, Eye, Zap, Loader, Database, Settings, Image, Tag, Sparkles, Palette, Camera, Text, Globe, Heart, Wrench, Search } from 'lucide-react'

interface Feature {
  id: string
  type: string
  confidence: number
  domain: string
  data: Record<string, any>
  analyzer_version?: string
  created_at?: string
}

interface AnalysisData {
  asset_id: string
  filename: string
  mime_type: string
  file_size: number
  processing_status: string
  created_at: string
  features: Feature[]
  summary: {
    total_features: number
    processing_time: number | null
  }
  dimensions?: {
    width: number
    height: number
  }
  file_path?: string
}

interface AnalysisResultsProps {
  assetId: string
  onClose: () => void
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="w-4 h-4 text-green-400" />
    case 'processing':
      return <Clock className="w-4 h-4 text-yellow-400" />
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-400" />
    case 'pending':
      return <Clock className="w-4 h-4 text-blue-400" />
    default:
      return <AlertCircle className="w-4 h-4 text-gray-400" />
  }
}

const formatConfidence = (confidence: number) => {
  return `${Math.round(confidence * 100)}% conf`
}

const getFeatureIcon = (featureType: string) => {
  switch (featureType) {
    case 'claude_vision_analysis':
      return <Sparkles className="w-5 h-5 text-purple-600" />
    case 'scene_classification':
      return <Camera className="w-5 h-5 text-blue-600" />
    case 'faces':
      return <Users className="w-5 h-5 text-green-600" />
    case 'object_detection':
      return <Target className="w-5 h-5 text-orange-600" />
    case 'image_quality':
      return <Eye className="w-5 h-5 text-indigo-600" />
    case 'composition':
      return <BarChart3 className="w-5 h-5 text-pink-600" />
    case 'technical_properties':
      return <Wrench className="w-5 h-5 text-gray-600" />
    case 'exif_comprehensive':
      return <Database className="w-5 h-5 text-gray-600" />
    default:
      return <Brain className="w-5 h-5 text-gray-600" />
  }
}

const parseClaudeVisionData = (feature: Feature) => {
  try {
    if (feature.data.analysis && feature.data.analysis.analysis) {
      // Remove markdown code blocks if present
      const jsonStr = feature.data.analysis.analysis
        .replace(/```json\n/g, '')
        .replace(/```\n/g, '')
        .replace(/```/g, '');
      return JSON.parse(jsonStr);
    }
  } catch (e) {
    console.error('Failed to parse Claude Vision analysis:', e);
  }
  return null;
}

const ClaudeVisionAnalysisDisplay: React.FC<{ feature: Feature }> = ({ feature }) => {
  const analysisData = parseClaudeVisionData(feature);
  if (!analysisData) return <div className="text-gray-500">No analysis data available</div>;
  
  return (
    <div className="space-y-4">
      {analysisData.hauptinhalt && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
          <div className="flex items-center space-x-2 mb-2">
            <Sparkles className="w-4 h-4 text-purple-600" />
            <span className="font-medium text-purple-900">Hauptinhalt</span>
          </div>
          <div className="text-sm text-purple-700">
            {analysisData.hauptinhalt}
          </div>
        </div>
      )}
      
      {analysisData.szenenbeschreibung && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex items-center space-x-2 mb-2">
            <Camera className="w-4 h-4 text-blue-600" />
            <span className="font-medium text-blue-900">Szenenbeschreibung</span>
          </div>
          <div className="text-sm text-blue-700">
            {analysisData.szenenbeschreibung}
          </div>
        </div>
      )}
      
      {analysisData.stimmung && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <div className="flex items-center space-x-2 mb-2">
            <Heart className="w-4 h-4 text-yellow-600" />
            <span className="font-medium text-yellow-900">Stimmung</span>
          </div>
          <div className="text-sm text-yellow-700">
            {analysisData.stimmung}
          </div>
        </div>
      )}
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {analysisData.objekte && Array.isArray(analysisData.objekte) && analysisData.objekte.length > 0 && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Target className="w-4 h-4 text-orange-600" />
              <span className="font-medium text-orange-900">Objekte ({analysisData.objekte.length})</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {analysisData.objekte.map((obj: string, index: number) => (
                <span 
                  key={index}
                  className="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded-full"
                >
                  {obj}
                </span>
              ))}
            </div>
          </div>
        )}
        
        {analysisData.personen && typeof analysisData.personen === 'string' && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Users className="w-4 h-4 text-green-600" />
              <span className="font-medium text-green-900">Personen</span>
            </div>
            <div className="text-sm text-green-700">
              {analysisData.personen}
            </div>
          </div>
        )}
        
        {analysisData.farben && analysisData.farben.hauptfarben && Array.isArray(analysisData.farben.hauptfarben) && (
          <div className="bg-pink-50 border border-pink-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Palette className="w-4 h-4 text-pink-600" />
              <span className="font-medium text-pink-900">Farben ({analysisData.farben.hauptfarben.length})</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {analysisData.farben.hauptfarben.map((color: string, index: number) => (
                <span 
                  key={index}
                  className="px-2 py-1 bg-pink-100 text-pink-800 text-xs rounded-full"
                >
                  {color}
                </span>
              ))}
            </div>
            {analysisData.farben.farbharmonie && (
              <div className="text-xs text-pink-600 mt-2">
                {analysisData.farben.farbharmonie}
              </div>
            )}
          </div>
        )}
        
        {analysisData.tags && Array.isArray(analysisData.tags) && analysisData.tags.length > 0 && (
          <div className="bg-teal-50 border border-teal-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Tag className="w-4 h-4 text-teal-600" />
              <span className="font-medium text-teal-900">Tags ({analysisData.tags.length})</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {analysisData.tags.map((tag: string, index: number) => (
                <span 
                  key={index}
                  className="px-2 py-1 bg-teal-100 text-teal-800 text-xs rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      
      {analysisData.komposition && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
          <div className="flex items-center space-x-2 mb-2">
            <BarChart3 className="w-4 h-4 text-indigo-600" />
            <span className="font-medium text-indigo-900">Komposition</span>
          </div>
          <div className="text-sm text-indigo-700">
            {typeof analysisData.komposition === 'string' ? analysisData.komposition : JSON.stringify(analysisData.komposition)}
          </div>
        </div>
      )}
      
      {analysisData.technische_aspekte && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <div className="flex items-center space-x-2 mb-2">
            <Wrench className="w-4 h-4 text-gray-600" />
            <span className="font-medium text-gray-900">Technische Aspekte</span>
          </div>
          <div className="text-sm text-gray-700">
            {typeof analysisData.technische_aspekte === 'string' ? analysisData.technische_aspekte : JSON.stringify(analysisData.technische_aspekte)}
          </div>
        </div>
      )}
      
      {analysisData.text && analysisData.text !== "Kein Text im Bild vorhanden" && (
        <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-3">
          <div className="flex items-center space-x-2 mb-2">
            <Text className="w-4 h-4 text-cyan-600" />
            <span className="font-medium text-cyan-900">Erkannter Text</span>
          </div>
          <div className="text-sm text-cyan-700">
            {analysisData.text}
          </div>
        </div>
      )}
    </div>
  );
};

const FeatureDataTableGlassmorphism: React.FC<{ data: Record<string, any> }> = ({ data }) => {
  const renderValue = (value: any, depth = 0): React.ReactNode => {
    if (value === null || value === undefined) {
      return <span className="text-gray-400 italic">null</span>
    }

    if (typeof value === 'string') {
      // Check if it looks like JSON
      try {
        const parsed = JSON.parse(value)
        return <div className="ml-4">{renderValue(parsed, depth + 1)}</div>
      } catch {
        return (
          <span className="text-white">
            {value.length > 200 ? `${value.substring(0, 200)}...` : value}
          </span>
        )
      }
    }

    if (typeof value === 'number') {
      return <span className="text-blue-300">{value}</span>
    }

    if (typeof value === 'boolean') {
      return <span className="text-purple-300">{value.toString()}</span>
    }

    if (Array.isArray(value)) {
      return (
        <div className="ml-4 space-y-2">
          <div className="text-sm text-gray-300 mb-2">Array ({value.length} items)</div>
          {value.slice(0, 3).map((item, index) => (
            <div key={index} className="bg-black bg-opacity-20 rounded px-2 py-1">
              [{index}] {renderValue(item, depth + 1)}
            </div>
          ))}
          {value.length > 3 && (
            <div className="text-xs text-gray-400 px-2 py-1">
              ... and {value.length - 3} more items
            </div>
          )}
        </div>
      )
    }

    if (typeof value === 'object') {
      const entries = Object.entries(value)
      return (
        <div className="ml-4 space-y-2">
          {entries.map(([key, val]) => (
            <div key={key} className="bg-black bg-opacity-20 rounded px-2 py-1">
              <span className="text-yellow-300 font-medium">{key}:</span>{' '}
              {renderValue(val, depth + 1)}
            </div>
          ))}
        </div>
      )
    }

    return <span className="text-gray-400">{String(value)}</span>
  }

  return (
    <div className="space-y-4">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="bg-white bg-opacity-10 backdrop-blur-sm rounded-lg p-4 border border-white border-opacity-20">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-semibold text-white">{key}</h4>
            <span className="text-xs text-white text-opacity-60 bg-white bg-opacity-10 px-2 py-1 rounded">
              {typeof value}
            </span>
          </div>
          <div className="text-sm">
            {renderValue(value)}
          </div>
        </div>
      ))}
    </div>
  )
}

const FeatureAccordion: React.FC<{ feature: Feature }> = ({ feature }) => {
  const [isOpen, setIsOpen] = useState(false)

  const formatKey = (key: string) => {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const renderValue = (value: any, key?: string): React.ReactNode => {
    if (value === null || value === undefined) {
      return <span className="text-gray-400 italic">null</span>
    }

    if (typeof value === 'string') {
      return <span className="text-gray-700">{value}</span>
    }

    if (typeof value === 'number') {
      if (value < 1 && value > 0) {
        return <span className="text-blue-600 font-medium">{Math.round(value * 100)}%</span>
      }
      return <span className="text-blue-600 font-medium">{value}</span>
    }

    if (typeof value === 'boolean') {
      return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          value ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {value ? 'Yes' : 'No'}
        </span>
      )
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-gray-400 italic">Empty array</span>
      }
      
      // Special handling for unified faces (FaceNet + DeepFace combined)
      if (value.length > 0 && typeof value[0] === 'object' && value[0].face_id !== undefined) {
        return (
          <div className="space-y-2">
            {value.map((face: any, index: number) => (
              <div key={index} className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="flex items-center space-x-3 mb-2">
                  {face.avatar_base64 ? (
                    <img 
                      src={face.avatar_base64} 
                      alt={`Avatar of ${face.identity}`}
                      className="w-12 h-12 rounded-full object-cover border-2 border-blue-300"
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-full bg-blue-100 border-2 border-blue-300 flex items-center justify-center">
                      <User className="w-6 h-6 text-blue-600" />
                    </div>
                  )}
                  <div className="flex-1">
                    <span className="font-medium text-blue-900">
                      {face.identity || `Face ${face.face_id || index}`}
                    </span>
                    {face.is_known ? (
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full ml-2">
                        Known
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded-full ml-2">
                        New
                      </span>
                    )}
                    {face.face_id && (
                      <span className="text-xs text-gray-500 font-mono ml-2">
                        ID: {face.face_id}
                      </span>
                    )}
                  </div>
                </div>
                
                {face.confidence && (
                  <div className="text-sm text-gray-600 mb-1">
                    <span className="font-medium">Confidence:</span> {Math.round(face.confidence * 100)}%
                  </div>
                )}
                
                {face.face_quality && (
                  <div className="text-sm text-gray-600 mb-1">
                    <span className="font-medium">Quality:</span> 
                    {typeof face.face_quality === 'object' && face.face_quality.level ? (
                      <span className={`ml-1 px-2 py-1 rounded text-xs ${
                        face.face_quality.level === 'excellent' ? 'bg-green-100 text-green-800' :
                        face.face_quality.level === 'good' ? 'bg-blue-100 text-blue-800' :
                        face.face_quality.level === 'fair' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {face.face_quality.level} ({Math.round(face.face_quality.overall_score * 100)}%)
                      </span>
                    ) : typeof face.face_quality === 'string' ? (
                      <span className={`ml-1 px-2 py-1 rounded text-xs ${
                        face.face_quality === 'excellent' ? 'bg-green-100 text-green-800' :
                        face.face_quality === 'good' ? 'bg-blue-100 text-blue-800' :
                        face.face_quality === 'fair' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {face.face_quality}
                      </span>
                    ) : null}
                  </div>
                )}
                
                {face.demographics && (
                  <div className="text-sm text-gray-600 mb-1 bg-purple-50 border border-purple-200 rounded p-2 mt-2">
                    <div className="font-medium text-purple-900 mb-1">Demographics:</div>
                    <div className="grid grid-cols-2 gap-1 text-xs">
                      {face.demographics.age && (
                        <div><span className="text-purple-700">Age:</span> {face.demographics.age}</div>
                      )}
                      {face.demographics.gender && (
                        <div><span className="text-purple-700">Gender:</span> {face.demographics.gender}</div>
                      )}
                      {face.demographics.race && (
                        <div><span className="text-purple-700">Race:</span> {face.demographics.race}</div>
                      )}
                      {face.demographics.emotion && (
                        <div><span className="text-purple-700">Emotion:</span> {face.demographics.emotion}</div>
                      )}
                    </div>
                  </div>
                )}
                
                {face.appearance_count && face.appearance_count > 1 && (
                  <div className="text-sm text-gray-600 mb-1">
                    <span className="font-medium">Appearances:</span> {face.appearance_count} times
                  </div>
                )}
                
                {face.first_seen && (
                  <div className="text-sm text-gray-600 mb-1">
                    <span className="font-medium">First Seen:</span> {new Date(parseFloat(face.first_seen) * 1000).toLocaleString()}
                  </div>
                )}
                
                {face.last_seen && (
                  <div className="text-sm text-gray-600 mb-1">
                    <span className="font-medium">Last Seen:</span> {new Date(parseFloat(face.last_seen) * 1000).toLocaleString()}
                  </div>
                )}
                
                {face.best_match && (
                  <div className="text-sm text-gray-600">
                    <span className="font-medium">Best Match:</span> {face.best_match.identity}
                    {face.best_match.confidence && (
                      <span className="ml-1 text-xs">({Math.round(face.best_match.confidence * 100)}%)</span>
                    )}
                  </div>
                )}
                
                {face.bbox && (
                  <div className="text-xs text-gray-500 mt-2">
                    <span className="font-medium">Position:</span> [{face.bbox.map((v: number) => Math.round(v)).join(', ')}]
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      }
      
      // Special handling for FaceNet quality assessments
      if (value.length > 0 && typeof value[0] === 'object' && value[0].quality_assessment !== undefined) {
        return (
          <div className="space-y-2">
            {value.map((assessment: any, index: number) => (
              <div key={index} className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <div className="flex items-center space-x-2 mb-2">
                  <Eye className="w-4 h-4 text-purple-600" />
                  <span className="font-medium text-purple-900">Face {assessment.face_id || index}</span>
                  <span className={`px-2 py-1 rounded text-xs ${
                    assessment.quality_assessment === 'excellent' ? 'bg-green-100 text-green-800' :
                    assessment.quality_assessment === 'good' ? 'bg-blue-100 text-blue-800' :
                    assessment.quality_assessment === 'fair' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {assessment.quality_assessment}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {assessment.detection_confidence && (
                    <div>
                      <span className="font-medium">Detection:</span> {Math.round(assessment.detection_confidence * 100)}%
                    </div>
                  )}
                  {assessment.face_size_score && (
                    <div>
                      <span className="font-medium">Size:</span> {Math.round(assessment.face_size_score * 100)}%
                    </div>
                  )}
                  {assessment.face_angle_score && (
                    <div>
                      <span className="font-medium">Angle:</span> {Math.round(assessment.face_angle_score * 100)}%
                    </div>
                  )}
                  {assessment.face_illumination_score && (
                    <div>
                      <span className="font-medium">Light:</span> {Math.round(assessment.face_illumination_score * 100)}%
                    </div>
                  )}
                </div>
                
                {assessment.overall_quality_score && (
                  <div className="mt-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-medium">Overall Score:</span>
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${assessment.overall_quality_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono">{Math.round(assessment.overall_quality_score * 100)}%</span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      }
      
      return (
        <div className="ml-4 space-y-1">
          {value.map((item, index) => (
            <div key={index} className="text-sm text-gray-600">
              • {String(item)}
            </div>
          ))}
        </div>
      )
    }

    if (typeof value === 'object') {
      // Special handling for Claude Vision Analysis
      if (key === 'hauptinhalt' && typeof value === 'string') {
        return (
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Sparkles className="w-4 h-4 text-purple-600" />
              <span className="font-medium text-purple-900">Hauptinhalt</span>
            </div>
            <div className="text-sm text-purple-700">
              {value}
            </div>
          </div>
        )
      }
      
      if (key === 'szenenbeschreibung' && typeof value === 'string') {
        return (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Camera className="w-4 h-4 text-blue-600" />
              <span className="font-medium text-blue-900">Szenenbeschreibung</span>
            </div>
            <div className="text-sm text-blue-700">
              {value}
            </div>
          </div>
        )
      }
      
      if (key === 'objekte' && Array.isArray(value)) {
        return (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Target className="w-4 h-4 text-orange-600" />
              <span className="font-medium text-orange-900">Objekte ({value.length})</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {value.map((obj: string, index: number) => (
                <span 
                  key={index}
                  className="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded-full"
                >
                  {obj}
                </span>
              ))}
            </div>
          </div>
        )
      }
      
      if (key === 'personen' && Array.isArray(value)) {
        return (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Users className="w-4 h-4 text-green-600" />
              <span className="font-medium text-green-900">Personen ({value.length})</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {value.map((person: string, index: number) => (
                <span 
                  key={index}
                  className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full"
                >
                  {person}
                </span>
              ))}
            </div>
          </div>
        )
      }
      
      if (key === 'farben' && Array.isArray(value)) {
        return (
          <div className="bg-pink-50 border border-pink-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Palette className="w-4 h-4 text-pink-600" />
              <span className="font-medium text-pink-900">Farben ({value.length})</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {value.map((color: string, index: number) => (
                <span 
                  key={index}
                  className="px-2 py-1 bg-pink-100 text-pink-800 text-xs rounded-full"
                >
                  {color}
                </span>
              ))}
            </div>
          </div>
        )
      }
      
      if (key === 'komposition' && typeof value === 'string') {
        return (
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <BarChart3 className="w-4 h-4 text-indigo-600" />
              <span className="font-medium text-indigo-900">Komposition</span>
            </div>
            <div className="text-sm text-indigo-700">
              {value}
            </div>
          </div>
        )
      }
      
      if (key === 'stimmung' && typeof value === 'string') {
        return (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Heart className="w-4 h-4 text-yellow-600" />
              <span className="font-medium text-yellow-900">Stimmung</span>
            </div>
            <div className="text-sm text-yellow-700">
              {value}
            </div>
          </div>
        )
      }
      
      if (key === 'technische_aspekte' && typeof value === 'string') {
        return (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Wrench className="w-4 h-4 text-gray-600" />
              <span className="font-medium text-gray-900">Technische Aspekte</span>
            </div>
            <div className="text-sm text-gray-700">
              {value}
            </div>
          </div>
        )
      }
      
      if (key === 'text' && Array.isArray(value)) {
        return (
          <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Text className="w-4 h-4 text-cyan-600" />
              <span className="font-medium text-cyan-900">Erkannter Text ({value.length})</span>
            </div>
            <div className="space-y-1">
              {value.map((text: string, index: number) => (
                <div key={index} className="text-sm text-cyan-700 bg-white rounded p-2 border">
                  "{text}"
                </div>
              ))}
            </div>
          </div>
        )
      }
      
      if (key === 'tags' && Array.isArray(value)) {
        return (
          <div className="bg-teal-50 border border-teal-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Tag className="w-4 h-4 text-teal-600" />
              <span className="font-medium text-teal-900">Tags ({value.length})</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {value.map((tag: string, index: number) => (
                <span 
                  key={index}
                  className="px-2 py-1 bg-teal-100 text-teal-800 text-xs rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )
      }
      
      // Special handling for Scene Classification
      if (key === 'primary_scene' && value.scene && value.confidence !== undefined) {
        return (
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Image className="w-4 h-4 text-purple-600" />
              <span className="font-medium text-purple-900">Primary Scene</span>
              <span className={`px-2 py-1 rounded text-xs ${
                value.confidence >= 0.8 ? 'bg-green-100 text-green-800' :
                value.confidence >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {Math.round(value.confidence * 100)}%
              </span>
            </div>
            <div className="text-sm text-purple-700">
              {value.scene}
            </div>
          </div>
        )
      }
      
      // Special handling for Scene Tags
      if (key === 'scene_tags' && Array.isArray(value)) {
        return (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <Tag className="w-4 h-4 text-blue-600" />
              <span className="font-medium text-blue-900">Scene Tags</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {value.map((tag: string, index: number) => (
                <span 
                  key={index}
                  className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )
      }
      
      // Special handling for Scene Lists (generic_scenes, specific_scenes)
      if ((key === 'generic_scenes' || key === 'specific_scenes') && Array.isArray(value)) {
        return (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              <BarChart3 className="w-4 h-4 text-gray-600" />
              <span className="font-medium text-gray-900 capitalize">
                {key.replace(/_/g, ' ')} ({value.length})
              </span>
            </div>
            <div className="space-y-2">
              {value.slice(0, 5).map((scene: any, index: number) => (
                <div key={index} className="flex items-center justify-between bg-white rounded p-2 border">
                  <span className="text-sm text-gray-700 flex-1">
                    {scene.scene}
                  </span>
                  <span className="text-xs text-gray-500 ml-2">
                    {Math.round(scene.confidence * 100)}%
                  </span>
                </div>
              ))}
              {value.length > 5 && (
                <div className="text-xs text-gray-500 text-center">
                  ... and {value.length - 5} more scenes
                </div>
              )}
            </div>
          </div>
        )
      }
      
      // Special handling for FaceNet detection data
      if (value.faces && Array.isArray(value.faces)) {
        return (
          <div className="space-y-2">
            <div className="flex items-center space-x-2 mb-3">
              <Users className="w-4 h-4 text-blue-600" />
              <span className="font-medium text-gray-900">
                {value.total_faces} Face{value.total_faces !== 1 ? 's' : ''} Detected
              </span>
              {value.model && (
                <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                  {value.model}
                </span>
              )}
            </div>
            
            {value.faces.map((face: any, index: number) => (
              <div key={index} className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <User className="w-4 h-4 text-blue-600" />
                    <span className="font-medium text-blue-900">Face {face.face_id || index}</span>
                  </div>
                  <span className="text-sm font-mono text-blue-700">
                    {Math.round(face.confidence * 100)}%
                  </span>
                </div>
                
                {face.face_size && (
                  <div className="text-xs text-gray-600 mb-1">
                    <span className="font-medium">Size:</span> {Math.round(face.face_size.width)}×{Math.round(face.face_size.height)}px
                  </div>
                )}
                
                {face.landmarks && face.landmarks.length > 0 && (
                  <div className="text-xs text-gray-500">
                    <span className="font-medium">Landmarks:</span> {face.landmarks.length} points
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      }
      
      // Special handling for FaceNet recognition data
      if (value.recognized_faces && Array.isArray(value.recognized_faces)) {
        return (
          <div className="space-y-2">
            <div className="flex items-center space-x-2 mb-3">
              <Zap className="w-4 h-4 text-green-600" />
              <span className="font-medium text-gray-900">
                {value.total_faces} Face{value.total_faces !== 1 ? 's' : ''} Recognized
              </span>
              {value.model && (
                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                  {value.model}
                </span>
              )}
            </div>
            
            <div className="grid grid-cols-2 gap-2 text-xs mb-3">
              <div className="bg-green-50 border border-green-200 rounded p-2 text-center">
                <div className="font-medium text-green-800">{value.known_faces || 0}</div>
                <div className="text-green-600">Known</div>
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded p-2 text-center">
                <div className="font-medium text-gray-800">{value.unknown_faces || 0}</div>
                <div className="text-gray-600">Unknown</div>
              </div>
            </div>
            
            {value.recognized_faces.map((face: any, index: number) => (
              <div key={index} className="bg-green-50 border border-green-200 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <User className="w-4 h-4 text-green-600" />
                    <span className="font-medium text-green-900">Face {face.face_id || index}</span>
                    {face.is_known_face && (
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                        Known
                      </span>
                    )}
                  </div>
                  <span className="text-sm font-mono text-green-700">
                    {face.face_quality}
                  </span>
                </div>
                
                {face.best_match && (
                  <div className="text-xs text-gray-600 mb-1">
                    <span className="font-medium">Best Match:</span> {face.best_match.identity}
                    {face.best_match.confidence && (
                      <span className="ml-1">({Math.round(face.best_match.confidence * 100)}%)</span>
                    )}
                  </div>
                )}
                
                {face.embedding_dimensions && (
                  <div className="text-xs text-gray-500">
                    <span className="font-medium">Embedding:</span> {face.embedding_dimensions}D
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      }
      
      return (
        <div className="ml-4 space-y-1">
          {Object.entries(value).map(([key, val]) => (
            <div key={key} className="text-sm">
              <span className="text-gray-500 font-medium">{formatKey(key)}:</span>{' '}
              <span className="text-gray-700">{renderValue(val)}</span>
            </div>
          ))}
        </div>
      )
    }

    return <span className="text-gray-600">{String(value)}</span>
  }

  return (
    <div className="border border-gray-200 rounded-lg mb-2 overflow-hidden bg-white">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center space-x-3">
          {getFeatureIcon(feature.type)}
          <div className="text-left">
            <h4 className="font-semibold text-gray-900">{formatKey(feature.type)}</h4>
            <p className="text-xs text-gray-500">{Math.round(feature.confidence * 100)}% Confidence • {feature.domain}</p>
          </div>
        </div>
        {isOpen ? (
          <ChevronUp className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        )}
      </button>
      
      {isOpen && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <div className="mt-3 space-y-2">
            {Object.entries(feature.data).map(([key, value]) => (
              <div key={key} className="bg-gray-50 rounded p-3">
                <div className="font-medium text-gray-700 text-sm mb-1">{formatKey(key)}</div>
                <div className="text-sm">{renderValue(value, key)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

const AnalysisResults: React.FC<AnalysisResultsProps> = ({ assetId, onClose }) => {
  const [selectedTab, setSelectedTab] = useState<'features' | 'metadata' | 'summary'>('features')

  // Fetch analysis data from API - use the new features endpoint
  const { data: analysisData, isLoading, error } = useQuery<AnalysisData>({
    queryKey: ['analysis', assetId],
    queryFn: async () => {
      // First get asset details
      const assetResponse = await fetch(`http://localhost:2013/api/v1/assets/${assetId}`)
      if (!assetResponse.ok) {
        throw new Error('Failed to fetch asset')
      }
      const asset = await assetResponse.json()
      
      // Then get features
      const featuresResponse = await fetch(`http://localhost:2013/api/v1/assets/${assetId}/features`)
      if (!featuresResponse.ok) {
        throw new Error('Failed to fetch features')
      }
      const featuresData = await featuresResponse.json()
      
      // Combine into analysis format
      return {
        asset_id: assetId,
        filename: asset.filename,
        mime_type: asset.mime_type,
        file_size: asset.file_size,
        processing_status: asset.processing_status,
        created_at: asset.created_at,
        features: featuresData.features,
        summary: {
          total_features: featuresData.total,
          processing_time: null
        }
      }
    },
    refetchOnWindowFocus: false
  })

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 overflow-hidden">
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
        <div className="absolute inset-y-0 right-0 w-full max-w-4xl bg-gradient-to-br from-gray-900 via-purple-900 to-indigo-900 shadow-2xl">
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Loader className="w-12 h-12 text-white animate-spin mx-auto mb-4" />
              <p className="text-white text-lg">Lade Analyse-Daten...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !analysisData) {
    return (
      <div className="fixed inset-0 z-50 overflow-hidden">
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
        <div className="absolute inset-y-0 right-0 w-full max-w-4xl bg-gradient-to-br from-gray-900 via-purple-900 to-indigo-900 shadow-2xl">
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <p className="text-white text-lg">Fehler beim Laden der Analyse-Daten</p>
              <button 
                onClick={onClose}
                className="mt-4 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg"
              >
                Schließen
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="w-full max-w-7xl h-[95vh] min-h-[95vh] bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 border-b border-gray-200">
          <div className="flex items-center justify-between px-6 py-4">
            <div className="flex items-center space-x-3">
              <Brain className="w-8 h-8 text-white" />
              <div>
                <h2 className="text-2xl font-bold text-white">{analysisData.filename}</h2>
                <p className="text-blue-100">{analysisData.summary.total_features} Features • {analysisData.mime_type.split('/')[0]}</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={onClose}
                className="text-white hover:bg-white hover:bg-opacity-20 rounded-lg p-2 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>
        </div>
        
        {/* Main Content Area - 2/3 Image + 1/3 Features */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left Side - Image Display (2/3) */}
          <div className="w-2/3 flex items-center justify-center bg-gray-100">
            {analysisData.mime_type.startsWith('image/') ? (
              <div className="max-w-full max-h-full flex items-center justify-center p-8">
                <img 
                  src={`http://localhost:2013/api/v1/assets/${analysisData.asset_id}/thumbnail/large`}
                  alt={analysisData.filename}
                  className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
                  onError={(e) => {
                    const img = e.currentTarget as HTMLImageElement
                    if (!img.src.includes('/thumbnail/')) {
                      img.src = `http://localhost:2013/api/v1/assets/${analysisData.asset_id}/thumbnail/medium`
                    } else if (!img.src.includes('/medium')) {
                      img.src = `http://localhost:2013/api/v1/assets/${analysisData.asset_id}/thumbnail`
                    } else {
                      img.style.display = 'none'
                    }
                  }}
                />
              </div>
            ) : (
              <div className="text-center">
                <div className="text-gray-400 text-6xl mb-4">📄</div>
                <div className="text-gray-500">{analysisData.mime_type.split('/')[1]?.toUpperCase() || 'FILE'}</div>
              </div>
            )}
          </div>
          
          {/* Right Side - Features Panel (1/3) */}
          <div className="w-1/3 bg-white border-l border-gray-200 overflow-y-auto">
            <div className="p-6">
              {/* Tab Navigation */}
              <div className="mb-6">
                <div className="flex space-x-2 border-b border-gray-200">
                  <button
                    onClick={() => setSelectedTab('features')}
                    className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                      selectedTab === 'features'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Features ({analysisData.features.length})
                  </button>
                  <button
                    onClick={() => setSelectedTab('summary')}
                    className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                      selectedTab === 'summary'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Summary
                  </button>
                  <button
                    onClick={() => setSelectedTab('metadata')}
                    className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                      selectedTab === 'metadata'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Metadata
                  </button>
                </div>
              </div>

              {/* Tab Content */}
              <div className="mt-4">
                {selectedTab === 'features' && (
                  <div className="space-y-2">
                    {analysisData.features.map((feature: Feature) => (
                      <FeatureAccordion key={feature.id} feature={feature} />
                    ))}
                  </div>
                )}
                
                {selectedTab === 'summary' && (
                  <div className="space-y-4">
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <h4 className="font-semibold text-gray-900 mb-3">Asset Info</h4>
                      <div className="text-sm text-gray-600 space-y-2">
                        <p><span className="font-medium text-gray-700">Filename:</span> {analysisData.filename}</p>
                        <p><span className="font-medium text-gray-700">Size:</span> {(analysisData.file_size / (1024 * 1024)).toFixed(2)} MB</p>
                        <p><span className="font-medium text-gray-700">Type:</span> {analysisData.mime_type}</p>
                        {analysisData.dimensions && (
                          <p><span className="font-medium text-gray-700">Dimensions:</span> {analysisData.dimensions.width}×{analysisData.dimensions.height}</p>
                        )}
                        <p>
                          <span className="font-medium text-gray-700">Status:</span>{' '}
                          <span className="inline-flex items-center space-x-1">
                            {getStatusIcon(analysisData.processing_status)}
                            <span className="capitalize ml-1">{analysisData.processing_status}</span>
                          </span>
                        </p>
                        <p><span className="font-medium text-gray-700">Uploaded:</span> {new Date(analysisData.created_at).toLocaleString()}</p>
                      </div>
                    </div>
                    
                    <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                      <h4 className="font-semibold text-blue-900 mb-3">Analysis Summary</h4>
                      <div className="text-sm text-blue-700 space-y-2">
                        <p><span className="font-medium">Total Features:</span> {analysisData.summary.total_features}</p>
                        {analysisData.summary.processing_time && (
                          <p><span className="font-medium">Processing Time:</span> {analysisData.summary.processing_time}s</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
                
                {selectedTab === 'metadata' && (
                  <div className="space-y-4">
                    {/* Raw Analysis Data */}
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
                        <Database className="w-4 h-4 mr-2" />
                        Raw Analysis Data
                      </h4>
                      <pre className="text-xs text-gray-700 overflow-x-auto bg-white p-3 rounded border max-h-96">
                        {JSON.stringify(analysisData, null, 2)}
                      </pre>
                    </div>
                    
                    {/* FaceNet Specific Features */}
                    {analysisData.features.some((f: Feature) => f.type.includes('face')) && (
                      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                        <h4 className="font-semibold text-blue-900 mb-3 flex items-center">
                          <User className="w-4 h-4 mr-2" />
                          FaceNet Analysis Details
                        </h4>
                        <div className="space-y-3">
                          {analysisData.features
                            .filter((f: Feature) => f.type.includes('face'))
                            .map((feature: Feature) => (
                              <div key={feature.id} className="bg-white rounded border p-3">
                                <div className="flex items-center justify-between mb-2">
                                  <h5 className="font-medium text-gray-900 capitalize">
                                    {feature.type.replace(/_/g, ' ')}
                                  </h5>
                                  <span className="text-xs text-gray-500">
                                    Confidence: {Math.round((feature.confidence || 0) * 100)}%
                                  </span>
                                </div>
                                <pre className="text-xs text-gray-600 overflow-x-auto">
                                  {JSON.stringify(feature.data, null, 2)}
                                </pre>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Claude Vision Analysis Features */}
                    {analysisData.features.some((f: Feature) => f.type === 'claude_vision_analysis') && (
                      <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                        <h4 className="font-semibold text-purple-900 mb-3 flex items-center">
                          <Sparkles className="w-4 h-4 mr-2" />
                          Claude Vision Analysis
                        </h4>
                        <div className="space-y-3">
                          {analysisData.features
                            .filter((f: Feature) => f.type === 'claude_vision_analysis')
                            .map((feature: Feature) => (
                              <div key={feature.id} className="bg-white rounded border p-3">
                                <div className="flex items-center justify-between mb-4">
                                  <div className="flex items-center space-x-2">
                                    <Sparkles className="w-5 h-5 text-purple-600" />
                                    <h5 className="font-medium text-gray-900">Claude Vision Analysis</h5>
                                  </div>
                                  <span className="text-xs text-gray-500">
                                    Confidence: {Math.round((feature.confidence || 0) * 100)}%
                                  </span>
                                </div>
                                
                                <ClaudeVisionAnalysisDisplay feature={feature} />
                                
                                {/* Raw data */}
                                <details className="mt-4">
                                  <summary className="text-xs text-gray-500 cursor-pointer">Raw Data</summary>
                                  <pre className="text-xs text-gray-600 mt-2 overflow-x-auto bg-gray-50 p-2 rounded">
                                    {JSON.stringify(feature.data, null, 2)}
                                  </pre>
                                </details>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Scene Classification Features */}
                    {analysisData.features.some((f: Feature) => f.type === 'scene_classification') && (
                      <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                        <h4 className="font-semibold text-purple-900 mb-3 flex items-center">
                          <Image className="w-4 h-4 mr-2" />
                          Scene Classification Details
                        </h4>
                        <div className="space-y-3">
                          {analysisData.features
                            .filter((f: Feature) => f.type === 'scene_classification')
                            .map((feature: Feature) => (
                              <div key={feature.id} className="bg-white rounded border p-3">
                                <div className="flex items-center justify-between mb-2">
                                  <h5 className="font-medium text-gray-900 capitalize">
                                    {feature.type.replace(/_/g, ' ')}
                                  </h5>
                                  <span className="text-xs text-gray-500">
                                    Confidence: {Math.round((feature.confidence || 0) * 100)}%
                                  </span>
                                </div>
                                
                                {/* Scene Classification specific display */}
                                {feature.data.primary_scene && (
                                  <div className="mb-3">
                                    <div className="text-sm font-medium text-gray-700 mb-1">Primary Scene:</div>
                                    <div className="bg-purple-100 rounded p-2 text-sm">
                                      <div className="font-medium text-purple-900">
                                        {feature.data.primary_scene.scene}
                                      </div>
                                      <div className="text-xs text-purple-600">
                                        Confidence: {Math.round(feature.data.primary_scene.confidence * 100)}%
                                      </div>
                                    </div>
                                  </div>
                                )}
                                
                                {feature.data.scene_tags && feature.data.scene_tags.length > 0 && (
                                  <div className="mb-3">
                                    <div className="text-sm font-medium text-gray-700 mb-1">Tags:</div>
                                    <div className="flex flex-wrap gap-1">
                                      {feature.data.scene_tags.map((tag: string, index: number) => (
                                        <span 
                                          key={index}
                                          className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                                        >
                                          {tag}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                
                                <pre className="text-xs text-gray-600 overflow-x-auto bg-gray-50 p-2 rounded">
                                  {JSON.stringify(feature.data, null, 2)}
                                </pre>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Technical Features */}
                    {analysisData.features.some((f: Feature) => f.domain === 'technical') && (
                      <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                        <h4 className="font-semibold text-green-900 mb-3 flex items-center">
                          <Settings className="w-4 h-4 mr-2" />
                          Technical Analysis Details
                        </h4>
                        <div className="space-y-3">
                          {analysisData.features
                            .filter((f: Feature) => f.domain === 'technical')
                            .map((feature: Feature) => (
                              <div key={feature.id} className="bg-white rounded border p-3">
                                <div className="flex items-center justify-between mb-2">
                                  <h5 className="font-medium text-gray-900 capitalize">
                                    {feature.type.replace(/_/g, ' ')}
                                  </h5>
                                  <span className="text-xs text-gray-500">
                                    Confidence: {Math.round((feature.confidence || 0) * 100)}%
                                  </span>
                                </div>
                                <pre className="text-xs text-gray-600 overflow-x-auto">
                                  {JSON.stringify(feature.data, null, 2)}
                                </pre>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AnalysisResults