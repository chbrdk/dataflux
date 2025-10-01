import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
  Brain,
  AlertTriangle
} from 'lucide-react'
import { toast } from 'react-hot-toast'
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
  const [assetToDelete, setAssetToDelete] = useState<Asset | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  
  const queryClient = useQueryClient()

  const { data: assetsData, isLoading, refetch } = useQuery({
    queryKey: ['assets'],
    queryFn: async () => {
      const response = await fetch('http://localhost:2013/api/v1/assets')
      if (!response.ok) {
        throw new Error('Failed to fetch assets')
      }
      return response.json()
    },
    refetchOnWindowFocus: false,
    staleTime: 30000 // 30 seconds
  })

  const assets = assetsData?.assets || []
  
  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (assetId: string) => {
      const response = await fetch(`http://localhost:2013/api/v1/assets/${assetId}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        throw new Error('Failed to delete asset')
      }
      return response.json()
    },
    onSuccess: (data, assetId) => {
      toast.success('Asset erfolgreich gelöscht')
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      setShowDeleteConfirm(false)
      setAssetToDelete(null)
      // Remove from selected assets if it was selected
      setSelectedAssets(prev => prev.filter(id => id !== assetId))
    },
    onError: (error) => {
      toast.error('Fehler beim Löschen des Assets')
      console.error('Delete error:', error)
    }
  })
  
  // Bulk delete mutation
  const bulkDeleteMutation = useMutation({
    mutationFn: async (assetIds: string[]) => {
      const response = await fetch('http://localhost:2013/api/v1/assets/bulk-delete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(assetIds)
      })
      if (!response.ok) {
        throw new Error('Failed to delete assets')
      }
      return response.json()
    },
    onSuccess: (data) => {
      toast.success(`${data.deleted_count} Asset(s) erfolgreich gelöscht`)
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      setSelectedAssets([])
    },
    onError: (error) => {
      toast.error('Fehler beim Löschen der Assets')
      console.error('Bulk delete error:', error)
    }
  })
  
  const handleDeleteClick = (asset: Asset) => {
    setAssetToDelete(asset)
    setShowDeleteConfirm(true)
  }
  
  const handleConfirmDelete = () => {
    if (assetToDelete) {
      deleteMutation.mutate(assetToDelete.id)
    }
  }
  
  const handleBulkDelete = () => {
    if (selectedAssets.length > 0) {
      if (confirm(`Möchten Sie wirklich ${selectedAssets.length} Asset(s) löschen?`)) {
        bulkDeleteMutation.mutate(selectedAssets)
      }
    }
  }

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
                <button 
                  onClick={handleBulkDelete}
                  disabled={bulkDeleteMutation.isPending}
                  className="px-3 py-1 bg-red-600 text-white text-sm rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
                >
                  <Trash2 className="w-3 h-3" />
                  <span>{bulkDeleteMutation.isPending ? 'Löschen...' : 'Löschen'}</span>
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
                      <button 
                        onClick={() => handleDeleteClick(asset)}
                        className="p-1 text-red-400 hover:text-red-600"
                        title="Asset löschen"
                      >
                        <Trash2 className="w-4 h-4" />
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
                      <button 
                        onClick={() => handleShowAnalysis(asset.id)}
                        className="p-2 text-purple-400 hover:text-purple-600"
                        title="Analyse-Ergebnisse"
                      >
                        <Brain className="w-4 h-4" />
                      </button>
                      <button className="p-2 text-gray-400 hover:text-gray-600">
                        <Eye className="w-4 h-4" />
                      </button>
                      <button className="p-2 text-gray-400 hover:text-gray-600">
                        <Download className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={() => handleDeleteClick(asset)}
                        className="p-2 text-red-400 hover:text-red-600"
                        title="Löschen"
                      >
                        <Trash2 className="w-4 h-4" />
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

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && assetToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Asset löschen?
                </h3>
              </div>
            </div>
            
            <p className="text-gray-600 mb-2">
              Möchten Sie das Asset <strong>{assetToDelete.filename}</strong> wirklich löschen?
            </p>
            <p className="text-sm text-gray-500 mb-6">
              Diese Aktion kann nicht rückgängig gemacht werden. Das Asset und alle zugehörigen Analyse-Daten werden permanent gelöscht.
            </p>
            
            <div className="flex items-center justify-end space-x-3">
              <button
                onClick={() => {
                  setShowDeleteConfirm(false)
                  setAssetToDelete(null)
                }}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50"
              >
                Abbrechen
              </button>
              <button
                onClick={handleConfirmDelete}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center space-x-2"
              >
                {deleteMutation.isPending ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Löschen...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    <span>Löschen</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Assets
