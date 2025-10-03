import React, { useState } from 'react'
import { Brain, Clock, CheckCircle, AlertCircle, XCircle, BarChart3, Target, Info, ChevronDown, ChevronUp, X } from 'lucide-react'

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

const FeatureAccordion: React.FC<{ feature: Feature }> = ({ feature }) => {
  const [isOpen, setIsOpen] = useState(false)

  const formatKey = (key: string) => {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const renderValue = (value: any): React.ReactNode => {
    if (value === null || value === undefined) {
      return <span className="text-gray-400 italic">null</span>
    }

    if (typeof value === 'string') {
      return <span className="text-gray-700">{value}</span>
    }

    if (typeof value === 'number') {
      return <span className="text-blue-600 font-medium">{value}</span>
    }

    if (typeof value === 'boolean') {
      return <span className="text-purple-600 font-medium">{value.toString()}</span>
    }

    if (Array.isArray(value)) {
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
      return (
        <div className="ml-4 space-y-1">
          {Object.entries(value).map(([key, val]) => (
            <div key={key} className="text-sm">
              <span className="text-gray-500 font-medium">{formatKey(key)}:</span>{' '}
              <span className="text-gray-700">{String(val)}</span>
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
          <div className={`w-2 h-2 rounded-full ${
            feature.confidence >= 0.9 ? 'bg-green-500' : 
            feature.confidence >= 0.7 ? 'bg-yellow-500' : 'bg-gray-400'
          }`} />
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
                <div className="text-sm">{renderValue(value)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

const AnalysisResults: React.FC<AnalysisResultsProps> = ({ analysisData, onClose }) => {
  const [selectedTab, setSelectedTab] = useState<'features' | 'metadata' | 'summary'>('features')

  if (!analysisData) {
    return null
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
            <button
              onClick={onClose}
              className="text-white hover:bg-white hover:bg-opacity-20 rounded-lg p-2 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
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
                    {analysisData.features.map((feature) => (
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
                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <pre className="text-xs text-gray-700 overflow-x-auto">
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