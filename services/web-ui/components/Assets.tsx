import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  FolderOpen,
  Grid,
  List,
  Filter,
  Search,
  Download,
  Trash2,
  Eye,
  Star,
  MoreVertical,
  FileText,
  Image,
  Video,
  Music,
  Clock,
  Calendar,
  RefreshCw,
  Brain
} from 'lucide-react'
import AnalysisResults from './AnalysisResults'

interface Asset {
  id: string
  filename: string
  mime_type: string
  file_size: number
  processing_status: 'queued' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  metadata?: {
    duration?: number
    dimensions?: { width: number; height: number }
    thumbnail?: string
  }
}

const Assets: React.FC = () => {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [selectedAssets, setSelectedAssets] = useState<string[]>([])
  const [filters, setFilters] = useState({
    status: '',
    type: '',
    dateRange: ''
  })
  const [selectedAssetForAnalysis, setSelectedAssetForAnalysis] = useState<string | null>(null)

  const { data: assetsData, isLoading, refetch } = useQuery({
    queryKey: ['assets'],
    queryFn: async () => {
      const response = await fetch('/api/v1/assets')
      if (!response.ok) {
        throw new Error('Failed to fetch assets')
      }
      return response.json()
    },
    refetchOnWindowFocus: false,
    staleTime: 30000 // 30 seconds
  })

  const assets = assetsData?.assets || []

  const getFileIcon = (mimeType: string) => {
    if (mimeType.startsWith('video/')) return Video
    if (mimeType.startsWith('image/')) return Image
    if (mimeType.startsWith('audio/')) return Music
    return FileText
  }

  const handleShowAnalysis = (assetId: string) => {
    setSelectedAssetForAnalysis(assetId)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'processing': return 'bg-blue-100 text-blue-800'
      case 'queued': return 'bg-yellow-100 text-yellow-800'
      case 'failed': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const toggleAssetSelection = (assetId: string) => {
    setSelectedAssets(prev => 
      prev.includes(assetId) 
        ? prev.filter(id => id !== assetId)
        : [...prev, assetId]
    )
  }

  const selectAllAssets = () => {
    if (selectedAssets.length === assets?.length) {
      setSelectedAssets([])
    } else {
      setSelectedAssets(assets?.map((asset: Asset) => asset.id) || [])
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Assets</h2>
          <p className="text-gray-600 mt-1">Manage your media files</p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="text-sm text-gray-500">
            {assets?.length || 0} files
          </div>
          <button
            onClick={() => refetch()}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
            title="Refresh assets"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filters and Actions */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search assets..."
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Filters */}
            <div className="flex items-center space-x-2">
              <Filter className="w-4 h-4 text-gray-600" />
              <select
                value={filters.status}
                onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
                className="text-sm border border-gray-300 rounded-md px-2 py-1"
              >
                <option value="">All Status</option>
                <option value="completed">Completed</option>
                <option value="processing">Processing</option>
                <option value="queued">Queued</option>
                <option value="failed">Failed</option>
              </select>
              
              <select
                value={filters.type}
                onChange={(e) => setFilters(prev => ({ ...prev, type: e.target.value }))}
                className="text-sm border border-gray-300 rounded-md px-2 py-1"
              >
                <option value="">All Types</option>
                <option value="video">Video</option>
                <option value="image">Image</option>
                <option value="audio">Audio</option>
                <option value="document">Document</option>
              </select>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* View Mode */}
            <div className="flex items-center space-x-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded-md ${viewMode === 'grid' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:bg-gray-100'}`}
              >
                <Grid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded-md ${viewMode === 'list' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:bg-gray-100'}`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>

            {/* Bulk Actions */}
            {selectedAssets.length > 0 && (
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">
                  {selectedAssets.length} selected
                </span>
                <button className="px-3 py-1 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700">
                  Download
                </button>
                <button className="px-3 py-1 bg-red-600 text-white text-sm rounded-md hover:bg-red-700">
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Assets Grid/List */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {assets?.map((asset: Asset) => {
            const FileIcon = getFileIcon(asset.mime_type)
            
            return (
              <div key={asset.id} className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow">
                {/* Thumbnail */}
                <div className="aspect-video bg-gray-100 flex items-center justify-center">
                  {asset.metadata?.thumbnail ? (
                    <img 
                      src={asset.metadata.thumbnail} 
                      alt={asset.filename}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <FileIcon className="w-12 h-12 text-gray-400" />
                  )}
                </div>

                {/* Content */}
                <div className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-medium text-gray-900 truncate flex-1">
                      {asset.filename}
                    </h4>
                    <button className="p-1 text-gray-400 hover:text-gray-600">
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <div className="space-y-2 text-sm text-gray-600">
                    <div className="flex items-center justify-between">
                      <span className="capitalize">
                        {asset.mime_type.split('/')[0]}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(asset.processing_status)}`}>
                        {asset.processing_status}
                      </span>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <span>{formatFileSize(asset.file_size)}</span>
                      <span>{formatDate(asset.created_at)}</span>
                    </div>

                    {asset.metadata?.duration && (
                      <div className="flex items-center space-x-1">
                        <Clock className="w-3 h-3" />
                        <span>{formatDuration(asset.metadata.duration)}</span>
                      </div>
                    )}

                    {asset.metadata?.dimensions && (
                      <div className="text-xs">
                        {asset.metadata.dimensions.width} × {asset.metadata.dimensions.height}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
                    <button className="flex items-center space-x-1 text-blue-600 hover:text-blue-700 text-sm">
                      <Eye className="w-4 h-4" />
                      <span>View</span>
                    </button>
                    
                    <div className="flex items-center space-x-2">
                      <button 
                        onClick={() => handleShowAnalysis(asset.id)}
                        className="p-1 text-purple-400 hover:text-purple-600"
                        title="Analyse-Ergebnisse anzeigen"
                      >
                        <Brain className="w-4 h-4" />
                      </button>
                      <button className="p-1 text-gray-400 hover:text-gray-600">
                        <Download className="w-4 h-4" />
                      </button>
                      <button className="p-1 text-gray-400 hover:text-gray-600">
                        <Star className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200">
          {/* List Header */}
          <div className="px-6 py-3 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center space-x-4">
              <input
                type="checkbox"
                checked={selectedAssets.length === assets?.length}
                onChange={selectAllAssets}
                className="rounded border-gray-300"
              />
              <span className="text-sm font-medium text-gray-700">Name</span>
            </div>
          </div>

          {/* List Items */}
          <div className="divide-y divide-gray-200">
            {assets?.map((asset: Asset) => {
              const FileIcon = getFileIcon(asset.mime_type)
              
              return (
                <div key={asset.id} className="px-6 py-4 hover:bg-gray-50">
                  <div className="flex items-center space-x-4">
                    <input
                      type="checkbox"
                      checked={selectedAssets.includes(asset.id)}
                      onChange={() => toggleAssetSelection(asset.id)}
                      className="rounded border-gray-300"
                    />
                    
                    <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <FileIcon className="w-6 h-6 text-gray-400" />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-gray-900 truncate">
                        {asset.filename}
                      </h4>
                      <div className="flex items-center space-x-4 mt-1 text-sm text-gray-600">
                        <span className="capitalize">{asset.mime_type.split('/')[0]}</span>
                        <span>{formatFileSize(asset.file_size)}</span>
                        <span>{formatDate(asset.created_at)}</span>
                        {asset.metadata?.duration && (
                          <span>{formatDuration(asset.metadata.duration)}</span>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(asset.processing_status)}`}>
                        {asset.processing_status}
                      </span>
                      <button className="p-2 text-gray-400 hover:text-gray-600">
                        <Eye className="w-4 h-4" />
                      </button>
                      <button className="p-2 text-gray-400 hover:text-gray-600">
                        <Download className="w-4 h-4" />
                      </button>
                      <button className="p-2 text-gray-400 hover:text-gray-600">
                        <MoreVertical className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Empty State */}
      {assets?.length === 0 && (
        <div className="text-center py-12">
          <FolderOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No assets found</h3>
          <p className="text-gray-600">Upload some files to get started</p>
        </div>
      )}

      {/* Analysis Results Modal */}
      {selectedAssetForAnalysis && (
        <AnalysisResults
          assetId={selectedAssetForAnalysis}
          onClose={() => setSelectedAssetForAnalysis(null)}
        />
      )}
    </div>
  )
}

export default Assets
