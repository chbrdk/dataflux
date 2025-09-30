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
      const response = await fetch(`/api/v1/assets/${assetId}/analysis`)
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
                      <div className="text-sm text-gray-600 mb-2">
                        {JSON.stringify(feature.data, null, 2)}
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

export default AnalysisResults
