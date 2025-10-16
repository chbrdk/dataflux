import React, { useState, useEffect } from 'react'
import { X, Download, FileText, ExternalLink, Eye, Info, Calendar, Tag, Layers, BarChart3, File, Clock, User, MapPin, Brain, Sparkles, Loader, AlertCircle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'

interface PDFViewerProps {
  isOpen: boolean
  onClose: () => void
  assetId: string
  filename: string
}

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

const PDFViewer: React.FC<PDFViewerProps> = ({ isOpen, onClose, assetId, filename }) => {
  const [selectedTab, setSelectedTab] = useState<'features' | 'metadata' | 'summary'>('features')
  const pdfUrl = `http://localhost:2013/api/v1/assets/${assetId}/download`

  // Fetch analysis features for this PDF
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
    refetchOnWindowFocus: false,
    enabled: isOpen
  })

  const handleDownload = () => {
    const link = document.createElement('a')
    link.href = pdfUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleOpenInNewTab = () => {
    window.open(pdfUrl, '_blank')
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <div className="w-2 h-2 bg-green-500 rounded-full"></div>
      case 'processing':
        return <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
      case 'failed':
        return <div className="w-2 h-2 bg-red-500 rounded-full"></div>
      case 'pending':
        return <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
      default:
        return <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatConfidence = (confidence: number) => {
    return `${Math.round(confidence * 100)}%`
  }

  const getFeatureIcon = (featureType: string) => {
    switch (featureType) {
      case 'document_structure':
        return <Layers className="w-5 h-5 text-blue-600" />
      case 'text_extraction':
        return <FileText className="w-5 h-5 text-green-600" />
      case 'table_extraction':
        return <BarChart3 className="w-5 h-5 text-orange-600" />
      case 'figure_extraction':
        return <Eye className="w-5 h-5 text-purple-600" />
      case 'metadata':
        return <Info className="w-5 h-5 text-gray-600" />
      default:
        return <Brain className="w-5 h-5 text-gray-600" />
    }
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
        
        return (
          <div className="ml-4 space-y-1">
            {value.slice(0, 5).map((item, index) => (
              <div key={index} className="text-sm text-gray-600">
                • {String(item)}
              </div>
            ))}
            {value.length > 5 && (
              <div className="text-xs text-gray-400">
                ... and {value.length - 5} more items
              </div>
            )}
          </div>
        )
      }

      if (typeof value === 'object') {
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
              <p className="text-xs text-gray-500">{formatConfidence(feature.confidence)} Confidence • {feature.domain}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {isOpen ? (
              <div className="w-5 h-5 text-gray-400">−</div>
            ) : (
              <div className="w-5 h-5 text-gray-400">+</div>
            )}
          </div>
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

  if (!isOpen) return null

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 overflow-hidden">
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
        <div className="absolute inset-y-0 right-0 w-full max-w-4xl bg-gradient-to-br from-gray-900 via-purple-900 to-indigo-900 shadow-2xl">
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Loader className="w-12 h-12 text-white animate-spin mx-auto mb-4" />
              <p className="text-white text-lg">Lade PDF-Analyse...</p>
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
              <p className="text-white text-lg">Fehler beim Laden der PDF-Analyse</p>
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
              <FileText className="w-8 h-8 text-white" />
              <div>
                <h2 className="text-2xl font-bold text-white">{analysisData.filename}</h2>
                <p className="text-blue-100">{analysisData.summary.total_features} Features • PDF Document</p>
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
        
        {/* Main Content Area - 2/3 PDF + 1/3 Features */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left Side - PDF Display (2/3) */}
          <div className="w-2/3 flex items-center justify-center bg-gray-100">
            <div className="text-center p-8">
              <div className="bg-white rounded-lg shadow-lg p-8 max-w-md mx-auto">
                <FileText className="w-24 h-24 text-blue-500 mx-auto mb-6" />
                <h3 className="text-xl font-semibold text-gray-900 mb-4">PDF Document</h3>
                <p className="text-gray-600 mb-6">
                  {analysisData.filename}
                </p>
                <div className="space-y-3">
                  <button
                    onClick={handleOpenInNewTab}
                    className="w-full flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
                  >
                    <ExternalLink className="w-5 h-5" />
                    <span>PDF in neuem Tab öffnen</span>
                  </button>
                  <button
                    onClick={handleDownload}
                    className="w-full flex items-center justify-center space-x-2 bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg transition-colors"
                  >
                    <Download className="w-5 h-5" />
                    <span>PDF herunterladen</span>
                  </button>
                </div>
              </div>
            </div>
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
                      <h4 className="font-semibold text-gray-900 mb-3">Document Info</h4>
                      <div className="text-sm text-gray-600 space-y-2">
                        <p><span className="font-medium text-gray-700">Filename:</span> {analysisData.filename}</p>
                        <p><span className="font-medium text-gray-700">Size:</span> {formatFileSize(analysisData.file_size)}</p>
                        <p><span className="font-medium text-gray-700">Type:</span> {analysisData.mime_type}</p>
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
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <h4 className="font-semibold text-gray-900 mb-3">Raw Analysis Data</h4>
                      <pre className="text-xs text-gray-700 overflow-x-auto bg-white p-3 rounded border max-h-96">
                        {JSON.stringify(analysisData, null, 2)}
                      </pre>
                    </div>
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

export default PDFViewer