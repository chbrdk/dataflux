import React, { useState } from 'react'
import { Brain, Clock, CheckCircle, AlertCircle, XCircle, BarChart3, Target, Info } from 'lucide-react'

interface FeatureData {
  id: string
  type: string
  confidence: number
  domain: string
  data: Record<string, any>
}

interface AnalysisData {
  asset_id: string
  filename: string
  mime_type: string
  file_size: number
  dimensions?: { width: number; height: number }
  processing_status: 'completed' | 'pending' | 'failed' | 'processing'
  features: Feature[]
  features_data: Record<string, any>
  summary: {
    total_features: number
    processing_time?: number
  }
  created_at: string
  metadata?: Record<string, any>
}

interface Feature {
  id: string
  type: string
  confidence: number
  domain: string
  data: Record<string, any>
}

interface AnalysisResultsProps {
  analysisData: AnalysisData
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

const AnalysisResults: React.FC<AnalysisResultsProps> = ({ analysisData, onClose }) => {
  const [selectedTab, setSelectedTab] = useState<'features' | 'metadata' | 'summary'>('features')

  if (!analysisData) {
    return null
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <div className="w-full max-w-7xl h-[95vh] min-h-[95vh] bg-white bg-opacity-10 backdrop-blur-md rounded-2xl shadow-2xl borderborder-white border-opacity-20 overflow-hidden">
        {/* Modal Header */}
        <div className="bg-white bg-opacity-15 border-b border-white border-opacity-20">
          <div className="flex items-center justify-between px-6 py-4">
            <div className="flex items-center space-x-3">
              <Brain className="w-8 h-8 text-white" />
              <div>
                <h2 className="text-2xl font-bold text-white">{analysisData.filename}</h2>
                <p className="text-white text-opacity-80">{analysisData.summary.total_features} Features • {analysisData.mime_type.split('/')[0]}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:text-gray-200 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        
        {/* Main Content Area - 2/3 Image + 1/3 Features */}
        <div className="flex h-[calc(95vh-80px)]">
          {/* Left Side - Image Display (2/3) */}
          <div className="w-2/3 flex items-center justify-center bg-black bg-opacity-40">
            {analysisData.mime_type.startsWith('image/') ? (
              <div className="max-w-full max-h-full flex items-center justify-center p-8">
                <img 
                  src={`http://localhost:2013/api/v1/assets/${analysisData.asset_id}/thumbnail/large`}
                  alt={analysisData.filename}
                  className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
                  onError={(e) => {
                    // Try fallback to medium thumbnail
                    const img = e.currentTarget as HTMLImageElement
                    if (!img.src.includes('/thumbnail/')) {
                      img.src = `http://localhost:2013/api/v1/assets/${analysisData.asset_id}/thumbnail/medium`
                    } else if (!img.src.includes('/medium')) {
                      img.src = `http://localhost:2013/api/v1/assets/${analysisData.asset_id}/thumbnail`
                    } else {
                      img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIyNCIgZmlsbD0iIzlmYTAwYSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+QnJva2VuIEltYWdlPC90ZXh0Pjwvc3ZnPg=='
                    }
                  }}
                />
              </div>
            ) : (
              <div className="text-center">
                <div className="text-white text-xl mb-4">📄</div>
                <div className="text-white text-opacity-60">{analysisData.mime_type.split('/')[1]?.toUpperCase() || 'FILE'}</div>
              </div>
            )}
          </div>
          
          {/* Right Side - Features Panel (1/3) */}
          <div className="w-1/3 bg-white bg-opacity-5 backdrop-blur-sm border-l border-white border-opacity-20 overflow-y-auto">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                <Brain className="w-5 h-5 mr-2" />
                Analyse-Ergebnisse
              </h3>
              
              {/* Tab Navigation */}
              <div className="mb-4">
                <div className="flex space-x-4">
                  <button
                    onClick={() => setSelectedTab('features')}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      selectedTab === 'features'
                        ? 'bg-white bg-opacity-20 text-white'
                        : 'text-white text-opacity-60 hover:text-opacity-80'
                    }`}
                  >
                    Features
                  </button>
                  <button
                    onClick={() => setSelectedTab('summary')}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      selectedTab === 'summary'
                        ? 'bg-white bg-opacity-20 text-white'
                        : 'text-white text-opacity-60 hover:text-opacity-80'
                    }`}
                  >
                    Summary
                  </button>
                  <button
                    onClick={() => setSelectedTab('metadata')}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      selectedTab === 'metadata'
                        ? 'bg-white bg-opacity-20 text-white'
                        : 'text-white text-opacity-60 hover:text-opacity-80'
                    }`}
                  >
                    Metadata
                  </button>
                </div>
              </div>

              {/* Tab Content */}
              <div className="mt-4">
                {selectedTab === 'features' && (
                  <FeatureDataTableGlassmorphism data={analysisData.features_data} />
                )}
                
                {selectedTab === 'summary' && (
                  <div className="space-y-4">
                    <div className="bg-white bg-opacity-10 backdrop-blur-sm rounded-lg p-4 border border-white border-opacity-20">
                      <h4 className="font-semibold text-white mb-2">Asset Info</h4>
                      <div className="text-sm text-white space-y-1">
                        <p><span className="font-medium">Filename:</span> {analysisData.filename}</p>
                        <p><span className="font-medium">Size:</span> {(analysisData.file_size / (1024 * 1024)).toFixed(2)} MB</p>
                        <p><span className="font-medium">Type:</span> {analysisData.mime_type}</p>
                        {analysisData.dimensions && (
                          <p><span className="font-medium">Dimensions:</span> {analysisData.dimensions.width}x{analysisData.dimensions.height}</p>
                        )}
                        <p><span className="font-medium">Status:</span> <span className="capitalize">{analysisData.processing_status}</span></p>
                        <p><span className="font-medium">Uploaded:</span> {new Date(analysisData.created_at).toLocaleString()}</p>
                      </div>
                    </div>
                    
                    <div className="bg-white bg-opacity-10 backdrop-blur-sm rounded-lg p-4 border border-white border-opacity-20">
                      <h4 className="font-semibold text-white mb-2">Analysis Summary</h4>
                      <div className="text-sm text-white space-y-1">
                        <p><span className="font-medium">Total Features:</span> {analysisData.summary.total_features}</p>
                        {analysisData.summary.processing_time && (
                          <p><span className="font-medium">Processing Time:</span> {analysisData.summary.processing_time}s</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
                
                {selectedTab === 'metadata' && (
                  <div className="bg-white bg-opacity-10 backdrop-blur-sm rounded-lg p-4 border border-white border-opacity-20">
                    <pre className="text-xs text-white overflow-x-auto custom-scrollbar">
                      {JSON.stringify(analysisData.metadata || {}, null, 2)}
                    </pre>
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