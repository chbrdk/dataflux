import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Brain,
  Clock,
  Target,
  BarChart3,
  Play,
  Pause,
  Volume2,
  Eye,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2
} from 'lucide-react'

interface AnalysisResultsProps {
  assetId: string
  onClose: () => void
}

interface Segment {
  id: string
  type: string
  sequence_number: number
  start_marker: Record<string, any>
  end_marker: Record<string, any>
  confidence?: number
  duration?: number
}

interface Feature {
  id: string
  type: string
  domain: string
  confidence?: number
  data: Record<string, any>
  analyzer_version: string
  created_at?: string
}

interface AnalysisData {
  asset_id: string
  filename: string
  mime_type: string
  processing_status: string
  segments: Segment[]
  features: Feature[]
  summary: {
    total_segments: number
    total_features: number
    analysis_completed: boolean
  }
}

const AnalysisResults: React.FC<AnalysisResultsProps> = ({ assetId, onClose }) => {
  const { data: analysisData, isLoading, error } = useQuery<AnalysisData>({
    queryKey: ['analysis', assetId],
    queryFn: async () => {
      const response = await fetch(`http://localhost:2013/api/v1/assets/${assetId}/analysis`)
      if (!response.ok) {
        throw new Error('Failed to fetch analysis results')
      }
      return response.json()
    },
    enabled: !!assetId
  })

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'processing':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />
      default:
        return <AlertCircle className="w-5 h-5 text-yellow-500" />
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'video':
        return <Play className="w-4 h-4" />
      case 'audio':
        return <Volume2 className="w-4 h-4" />
      case 'image':
        return <Eye className="w-4 h-4" />
      default:
        return <Target className="w-4 h-4" />
    }
  }

  const formatTime = (seconds?: number) => {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatConfidence = (confidence?: number) => {
    if (!confidence) return 'N/A'
    return `${Math.round(confidence * 100)}%`
  }

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            <span className="ml-2 text-gray-600">Lade Analyse-Ergebnisse...</span>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-gray-900">Analyse-Ergebnisse</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
          <div className="text-center py-8">
            <XCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-gray-600">Fehler beim Laden der Analyse-Ergebnisse</p>
          </div>
        </div>
      </div>
    )
  }

  if (!analysisData) {
    return null
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="relative max-w-7xl w-full mx-4 h-[95vh] min-h-[95vh] overflow-hidden rounded-2xl shadow-2xl">
        {/* Background Image */}
        {analysisData.mime_type.startsWith('image/') ? (
          <div className="absolute inset-0">
            <img 
              src={`http://localhost:2013/api/v1/assets/${analysisData.asset_id}/thumbnail/large`}
              alt={analysisData.filename}
              className="w-full h-full object-cover"
              onError={(e) => {
                // Try fallback to medium thumbnail
                const img = e.currentTarget as HTMLImageElement
                if (!img.src.includes('/thumbnail/')) {
                  img.src = `http://localhost:2013/api/v1/assets/${analysisData.asset_id}/thumbnail/medium`
                } else if (!img.src.includes('/medium')) {
                  img.src = `http://localhost:2013/api/v1/assets/${analysisData.asset_id}/thumbnail`
                } else {
                  img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIyNCIgZmlsbD0iIzlmYTBhYSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+QnJva2VuIEltYWdlPC90ZXh0Pjwvc3ZnPg=='
                }
              }}
            />
            {/* Dark overlay for better text readability */}
            <div className="absolute inset-0 bg-black bg-opacity-30"></div>
          </div>
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900"></div>
        )}

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-20 bg-white bg-opacity-20 hover:bg-opacity-30 backdrop-blur-sm rounded-full p-2 text-white transition-all duration-200"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Main Content with Glassmorphism */}
        <div className="relative z-10 h-full p-8 overflow-y-auto">
          
          {/* Floating Header */}
          <div className="mb-8">
            <div className="bg-white bg-opacity-10 backdrop-blur-md rounded-2xl p-6 border border-white border-opacity-20 shadow-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="bg-white bg-opacity-20 backdrop-blur-sm rounded-xl p-3">
                    <Brain className="w-8 h-8 text-white" />
                  </div>
                  <div>
                    <h2 className="text-3xl font-bold text-white mb-1">Analyse-Ergebnisse</h2>
                    <p className="text-white text-opacity-80 text-lg">{analysisData.filename}</p>
                  </div>
                </div>
                
                {/* Status Badge */}
                <div className="flex items-center space-x-3">
                  <div className="bg-white bg-opacity-20 backdrop-blur-sm rounded-xl px-4 py-2 border border-white border-opacity-30">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(analysisData.processing_status)}
                      <span className="font-medium text-white capitalize">
                        {analysisData.processing_status}
                      </span>
                    </div>
                  </div>
                  <div className="bg-white bg-opacity-10 backdrop-blur-sm rounded-xl px-4 py-2">
                    <span className="text-white text-opacity-80 text-sm">
                      {analysisData.summary.total_features} Features • {analysisData.mime_type.split('/')[0]}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Features Section */}
          <div className="mb-8">
            <div className="bg-white bg-opacity-10 backdrop-blur-md rounded-2xl p-6 border border-white border-opacity-20 shadow-xl">
              <h3 className="text-xl font-semibold text-white mb-6 flex items-center">
                <BarChart3 className="w-6 h-6 mr-3" />
                Features ({analysisData.features.length})
              </h3>
              
              <div className="space-y-4 max-h-64 overflow-y-auto custom-scrollbar">
                {analysisData.features.length > 0 ? (
                  analysisData.features.map((feature) => (
                    <div key={feature.id} className="bg-white bg-opacity-10 backdrop-blur-sm rounded-xl p-4 border border-white border-opacity-20 hover:bg-opacity-20 transition-all duration-200">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          <Target className="w-5 h-5 text-white" />
                          <span className="font-medium text-white text-lg">{feature.type}</span>
                          <span className="text-xs bg-white bg-opacity-20 text-white px-2 py-1 rounded-full backdrop-blur-sm">
                            {feature.domain}
                          </span>
                        </div>
                        <span className="text-sm text-white text-opacity-80 bg-white bg-opacity-10 px-3 py-1 rounded-full">
                          {formatConfidence(feature.confidence)}
                        </span>
                      </div>
                      
                      {Object.keys(feature.data).length > 0 && (
                        <div className="mt-4">
                          <FeatureDataTableGlassmorphism data={feature.data} />
                        </div>
                      )}
                      
                      <div className="text-xs text-white text-opacity-60 mt-3 flex space-x-4">
                        <span>Analyzer: {feature.analyzer_version}</span>
                        {feature.created_at && <span>Erstellt: {new Date(feature.created_at).toLocaleString()}</span>}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-12 text-white text-opacity-60">
                    <BarChart3 className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-xl">Keine Features gefunden</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Floating Summary */}
          <div className="bg-gradient-to-r from-white from-opacity-10 to-white to-opacity-5 backdrop-blur-md rounded-2xl p-6 border border-white border-opacity-20 shadow-xl">
            <h4 className="font-semibold text-white text-xl mb-4">Zusammenfassung</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white bg-opacity-10 rounded-xl p-4 backdrop-blur-sm border border-white border-opacity-20">
                <span className="text-white text-opacity-80 font-medium block mb-1">Dateityp</span>
                <p className="text-white text-xl font-bold capitalize">{analysisData.mime_type.split('/')[0]}</p>
              </div>
              <div className="bg-white bg-opacity-10 rounded-xl p-4 backdrop-blur-sm border border-white border-opacity-20">
                <span className="text-white text-opacity-80 font-medium block mb-1">Features</span>
                <p className="text-white text-xl font-bold">{analysisData.summary.total_features}</p>
              </div>
              <div className="bg-white bg-opacity-10 rounded-xl p-4 backdrop-blur-sm border border-white border-opacity-20">
                <span className="text-white text-opacity-80 font-medium block mb-1">Status</span>
                <p className="text-white text-xl font-bold capitalize">{analysisData.processing_status}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Custom Scrollbar Styles */}
        <style jsx>{`
          .custom-scrollbar::-webkit-scrollbar {
            width: 6px;
          }
          .custom-scrollbar::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.3);
            border-radius: 10px;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.5);
          }
        `}</style>
      </div>
    </div>
  )
}

// Glassmorphism Feature Data Table
const FeatureDataTableGlassmorphism = ({ data }: { data: any }) => {
  const renderValue = (value: any, key: string): React.ReactNode => {
    if (value === null || value === undefined) {
      return <span className="text-white text-opacity-50 italic">null</span>
    }
    
    if (typeof value === 'boolean') {
      return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
          value ? 'bg-green-500 bg-opacity-20 text-green-200 border border-green-400 border-opacity-30' : 'bg-red-500 bg-opacity-20 text-red-200 border border-red-400 border-opacity-30'
        }`}>
          {value ? 'Ja' : 'Nein'}
        </span>
      )
    }
    
    if (typeof value === 'number') {
      if (key.includes('score') || key.includes('balance') || key.includes('density')) {
        return <span className="font-mono text-yellow-300 bg-white bg-opacity-10 px-2 py-1 rounded-full text-sm">{(value * 100).toFixed(1)}%</span>
      }
      if (key.includes('brightness') || key.includes('contrast')) {
        return <span className="font-mono text-purple-300 bg-white bg-opacity-10 px-2 py-1 rounded-full text-sm">{value.toFixed(1)}</span>
      }
      if (key.includes('x') || key.includes('y') || key.includes('width') || key.includes('height')) {
        return <span className="font-mono text-cyan-300 bg-white bg-opacity-10 px-2 py-1 rounded-full text-sm">{value.toLocaleString()}</span>
      }
      return <span className="font-mono text-white bg-white bg-opacity-10 px-2 py-1 rounded-full text-sm">{value.toFixed(2)}</span>
    }
    
    if (typeof value === 'string') {
      if (value.startsWith('{') || value.startsWith('[')) {
        try {
          const parsed = JSON.parse(value)
          return renderValue(parsed, key)
        } catch {
          return <span className="text-white bg-white bg-opacity-10 px-2 py-1 rounded-full text-sm">{value}</span>
        }
      }
      return <span className="text-white bg-white bg-opacity-10 px-2 py-1 rounded-full text-sm">{String(value)}</span>
    }
    
    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-white text-opacity-50 italic">[]</span>
      }
      
      if (value.length > 0 && typeof value[0] === 'object') {
        return (
          <div className="space-y-2">
            {value.map((item, index) => (
              <div key={index} className="bg-white bg-opacity-5 rounded-lg p-3 border border-white border-opacity-10">
                <div className="text-white text-opacity-70 text-xs font-medium mb-2">Punkt {index + 1}</div>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(item).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs">
                      <span className="text-white text-opacity-60">{k}:</span>
                      <span className="text-white font-mono">{renderValue(v, k)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )
      }
      
      return (
        <div className="flex flex-wrap gap-1">
          {value.map((item, index) => (
            <span key={index} className="bg-white bg-opacity-20 text-white px-2 py-1 rounded-full text-xs border border-white border-opacity-30">
              {renderValue(item, key)}
            </span>
          ))}
        </div>
      )
    }
    
    if (typeof value === 'object') {
      return (
        <div className="bg-white bg-opacity-5 rounded-lg p-3 border border-white border-opacity-10">
          {Object.entries(value).map(([k, v]) => (
            <div key={k} className="flex justify-between mb-1 text-xs">
              <span className="text-white text-opacity-70 font-medium">{k}:</span>
              <span className="text-white">{renderValue(v, k)}</span>
            </div>
          ))}
        </div>
      )
    }
    
    return <span className="text-white bg-white bg-opacity-10 px-2 py-1 rounded-full text-sm">{String(value)}</span>
  }

  if (typeof data === 'string') {
    try {
      const parsedData = JSON.parse(data)
      return <FeatureDataTableGlassmorphism data={parsedData} />
    } catch (error) {
      return (
        <div className="bg-white bg-opacity-5 rounded-lg p-4 border border-white border-opacity-10">
          <div className="text-white text-sm font-mono bg-white bg-opacity-5 p-3 rounded-lg border border-white border-opacity-10">
            {data}
          </div>
        </div>
      )
    }
  }
  
  if (Array.isArray(data)) {
    return (
      <div className="bg-white bg-opacity-5 rounded-lg p-4 border border-white border-opacity-10">
        <div className="text-white text-sm">
          {data.map((item, index) => (
            <div key={index} className="mb-2">
              {renderValue(item, index.toString())}
            </div>
          ))}
        </div>
      </div>
    )
  }
  
  return (
    <div className="space-y-2">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="bg-white bg-opacity-5 rounded-lg p-3 border border-white border-opacity-10 hover:bg-opacity-10 transition-all duration-200">
          <div className="text-white text-opacity-70 font-medium text-sm mb-1">
            {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </div>
          <div className="text-white">
            {renderValue(value, key)}
          </div>
        </div>
      ))}
    </div>
  )
}

// Legacy FeatureDataTable (keeping for compatibility)
const FeatureDataTable = ({ data }: { data: any }) => {
  const renderValue = (value: any, key: string): React.ReactNode => {
    // Debug-Logging
    console.log('renderValue called with:', { value, key, type: typeof value, isArray: Array.isArray(value) })
    
    // Sicherheitscheck: value darf nicht undefined oder null sein
    if (value === null || value === undefined) {
      return <span className="text-gray-400 italic">null</span>
    }
    
    // WICHTIG: Prüfe ob value ein String ist und als Array behandelt wird
    if (typeof value === 'string' && Array.isArray(value)) {
      console.warn('String wird als Array behandelt:', value)
      return <span className="text-gray-700">{value}</span>
    }
    
    // WICHTIG: Prüfe ob value ein String ist, aber als einzelne Zeichen behandelt wird
    if (typeof value === 'string' && value.length === 1 && key.match(/^\d+$/)) {
      console.warn('String-Zeichen wird einzeln behandelt:', value, 'key:', key)
      // Das ist ein einzelnes Zeichen aus einem String - nicht rendern
      return null
    }
    
    if (typeof value === 'boolean') {
      return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          value ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {value ? 'Ja' : 'Nein'}
        </span>
      )
    }
    
    if (typeof value === 'number') {
      // Formatierung für verschiedene Zahlentypen
      if (key.includes('score') || key.includes('balance') || key.includes('density')) {
        return <span className="font-mono text-blue-600">{(value * 100).toFixed(1)}%</span>
      }
      if (key.includes('brightness') || key.includes('contrast')) {
        return <span className="font-mono text-purple-600">{value.toFixed(1)}</span>
      }
      if (key.includes('x') || key.includes('y') || key.includes('width') || key.includes('height')) {
        return <span className="font-mono text-gray-600">{value.toLocaleString()}</span>
      }
      return <span className="font-mono text-gray-700">{value.toFixed(2)}</span>
    }
    
    if (typeof value === 'string') {
      // Prüfe ob es ein JSON-String ist
      if (value.startsWith('{') || value.startsWith('[')) {
        try {
          const parsed = JSON.parse(value)
          return renderValue(parsed, key)
        } catch {
          return <span className="text-gray-700">{value}</span>
        }
      }
      // Wichtig: String als einzelnes Element rendern, nicht als Array
      // React rendert Strings automatisch zeichenweise, daher explizit als Text rendern
      return <span className="text-gray-700">{String(value)}</span>
    }
    
    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-gray-400 italic">[]</span>
      }
      
      // Spezielle Behandlung für Arrays mit Objekten (z.B. rule_of_thirds_points)
      if (value.length > 0 && typeof value[0] === 'object') {
        return (
          <div className="space-y-2">
            {value.map((item, index) => (
              <div key={index} className="bg-gray-50 rounded p-2 text-xs">
                <div className="font-medium text-gray-600 mb-1">Punkt {index + 1}</div>
                <div className="grid grid-cols-2 gap-1">
                  {Object.entries(item).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-gray-500">{k}:</span>
                      <span className="font-mono">{renderValue(v, k)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )
      }
      
      return (
        <div className="flex flex-wrap gap-1">
          {value.map((item, index) => (
            <span key={index} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
              {renderValue(item, key)}
            </span>
          ))}
        </div>
      )
    }
    
    if (typeof value === 'object') {
      return (
        <div className="bg-gray-50 rounded p-2 text-xs">
          {Object.entries(value).map(([k, v]) => (
            <div key={k} className="flex justify-between mb-1">
              <span className="text-gray-600 font-medium">{k}:</span>
              <span>{renderValue(v, k)}</span>
            </div>
          ))}
        </div>
      )
    }
    
    // Fallback für unbekannte Typen - explizit als String rendern
    return <span className="text-gray-500">{String(value)}</span>
  }

  // Debug-Logging für die Hauptkomponente
  console.log('FeatureDataTable data:', data, 'type:', typeof data, 'isArray:', Array.isArray(data))
  
  // WICHTIG: Prüfe ob data ein String ist, der als Array behandelt wird
  if (typeof data === 'string') {
    console.warn('Data ist ein String, versuche JSON zu parsen:', data)
    
    // Versuche JSON zu parsen
    try {
      const parsedData = JSON.parse(data)
      console.log('JSON erfolgreich geparst:', parsedData)
      
      // Rekursiv FeatureDataTable mit geparsten Daten aufrufen
      return <FeatureDataTable data={parsedData} />
    } catch (error) {
      console.warn('JSON-Parsing fehlgeschlagen, rendere als Text:', error)
      
      // Fallback: Als Text rendern
      return (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
            <h4 className="text-sm font-medium text-gray-700">Feature Details</h4>
          </div>
          <div className="px-4 py-3">
            <div className="text-sm text-gray-700 font-mono bg-gray-50 p-3 rounded">
              {data}
            </div>
          </div>
        </div>
      )
    }
  }
  
  // Prüfe ob data ein Array ist (sollte nicht passieren, aber sicherheitshalber)
  if (Array.isArray(data)) {
    console.warn('Data ist ein Array, wird als Liste gerendert:', data)
    return (
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
          <h4 className="text-sm font-medium text-gray-700">Feature Details</h4>
        </div>
        <div className="px-4 py-3">
          <div className="text-sm text-gray-700">
            {data.map((item, index) => (
              <div key={index} className="mb-2">
                {renderValue(item, index.toString())}
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
        <h4 className="text-sm font-medium text-gray-700">Feature Details</h4>
      </div>
      <div className="divide-y divide-gray-200">
        {Object.entries(data).map(([key, value]) => {
          console.log('Rendering entry:', { key, value, type: typeof value })
          return (
            <div key={key} className="px-4 py-3">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900 mb-1">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </div>
                  <div className="text-sm">
                    {renderValue(value, key)}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default AnalysisResults
