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
      <div className="bg-white rounded-lg p-6 max-w-6xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <Brain className="w-6 h-6 text-blue-500" />
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Analyse-Ergebnisse</h2>
              <p className="text-gray-600">{analysisData.filename}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            ✕
          </button>
        </div>

        {/* Status */}
        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {getStatusIcon(analysisData.processing_status)}
              <span className="font-medium">
                Status: {analysisData.processing_status}
              </span>
            </div>
            <div className="text-sm text-gray-600">
              {analysisData.summary.total_segments} Segmente • {analysisData.summary.total_features} Features
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Segments */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <Clock className="w-5 h-5 mr-2" />
              Segmente ({analysisData.segments.length})
            </h3>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {analysisData.segments.length > 0 ? (
                analysisData.segments.map((segment) => (
                  <div key={segment.id} className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        {getTypeIcon(segment.type)}
                        <span className="font-medium capitalize">{segment.type}</span>
                      </div>
                      <span className="text-sm text-gray-500">
                        {formatConfidence(segment.confidence)}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">
                      Sequenz: {segment.sequence_number}
                      {segment.duration && ` • Dauer: ${formatTime(segment.duration)}`}
                    </div>
                    {(Object.keys(segment.start_marker).length > 0 || Object.keys(segment.end_marker).length > 0) && (
                      <div className="mt-2 text-xs text-gray-500">
                        <div>Start: {JSON.stringify(segment.start_marker, null, 2)}</div>
                        <div>Ende: {JSON.stringify(segment.end_marker, null, 2)}</div>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Keine Segmente gefunden</p>
                </div>
              )}
            </div>
          </div>

          {/* Features */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <BarChart3 className="w-5 h-5 mr-2" />
              Features ({analysisData.features.length})
            </h3>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {analysisData.features.length > 0 ? (
                analysisData.features.map((feature) => (
                  <div key={feature.id} className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <Target className="w-4 h-4" />
                        <span className="font-medium">{feature.type}</span>
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                          {feature.domain}
                        </span>
                      </div>
                      <span className="text-sm text-gray-500">
                        {formatConfidence(feature.confidence)}
                      </span>
                    </div>
                    {Object.keys(feature.data).length > 0 && (
                      <div className="mt-3">
                        <FeatureDataTable data={feature.data} />
                      </div>
                    )}
                    <div className="text-xs text-gray-500">
                      <div>Analyzer: {feature.analyzer_version}</div>
                      {feature.created_at && <div>Erstellt: {new Date(feature.created_at).toLocaleString()}</div>}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Keine Features gefunden</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className="mt-6 bg-blue-50 rounded-lg p-4">
          <h4 className="font-semibold text-blue-900 mb-2">Zusammenfassung</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-blue-700 font-medium">Dateityp:</span>
              <p className="text-blue-600">{analysisData.mime_type}</p>
            </div>
            <div>
              <span className="text-blue-700 font-medium">Segmente:</span>
              <p className="text-blue-600">{analysisData.summary.total_segments}</p>
            </div>
            <div>
              <span className="text-blue-700 font-medium">Features:</span>
              <p className="text-blue-600">{analysisData.summary.total_features}</p>
            </div>
            <div>
              <span className="text-blue-700 font-medium">Status:</span>
              <p className="text-blue-600 capitalize">{analysisData.processing_status}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Komponente für die strukturierte Darstellung der Feature-Daten
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
