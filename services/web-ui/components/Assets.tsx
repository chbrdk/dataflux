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
  AlertTriangle,
  X,
  Folder,
  FolderPlus,
  ChevronRight,
  Home,
  Move,
  Edit,
  Plus
} from 'lucide-react'
import { toast } from 'react-hot-toast'
import AnalysisResults from './AnalysisResults'
import dynamic from 'next/dynamic'

// Dynamically import PDFViewer to avoid SSR issues
const PDFViewer = dynamic(() => import('./PDFViewer'), { ssr: false })

interface Asset {
  id: string
  filename: string
  mime_type: string
  file_size: number
  processing_status: 'queued' | 'processing' | 'completed' | 'failed' | 'pending'
  created_at: string
  thumbnail_path?: string
  dimensions?: { width: number; height: number }
  folder_id?: string
  metadata?: {
    duration?: number
    dimensions?: { width: number; height: number }
    thumbnail?: string
    features_data?: Record<string, any>
  }
}

interface Folder {
  id: string
  name: string
  parent_id?: string
  created_at: string
  updated_at: string
  asset_count?: number
}

const Assets: React.FC = () => {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [selectedAssets, setSelectedAssets] = useState<string[]>([])
  const [filters, setFilters] = useState({
    status: '',
    type: '',
    dateRange: ''
  })
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedAssetForAnalysis, setSelectedAssetForAnalysis] = useState<string | null>(null)
  const [assetToDelete, setAssetToDelete] = useState<Asset | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showPDFViewer, setShowPDFViewer] = useState(false)
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null)
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null)
  const [showCreateFolder, setShowCreateFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [draggedAsset, setDraggedAsset] = useState<string | null>(null)
  const [dragOverFolder, setDragOverFolder] = useState<string | null>(null)
  const [showFolderContextMenu, setShowFolderContextMenu] = useState<{ x: number; y: number; folderId: string } | null>(null)
  
  const queryClient = useQueryClient()

  const { data: assetsData, isLoading, refetch } = useQuery({
    queryKey: ['assets', currentFolderId],
    queryFn: async () => {
      const url = currentFolderId 
        ? `http://localhost:2013/api/v1/assets?folder_id=${currentFolderId}`
        : 'http://localhost:2013/api/v1/assets'
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error('Failed to fetch assets')
      }
      return response.json()
    },
    refetchOnWindowFocus: false,
    staleTime: 30000 // 30 seconds
  })

  const { data: foldersData, refetch: refetchFolders } = useQuery({
    queryKey: ['folders'],
    queryFn: async () => {
      const response = await fetch('http://localhost:2013/api/v1/folders')
      if (!response.ok) {
        throw new Error('Failed to fetch folders')
      }
      return response.json()
    },
    refetchOnWindowFocus: false,
    staleTime: 30000 // 30 seconds
  })

  const allAssets = assetsData?.assets || []
  
  // Filter assets based on search query and filters
  const filteredAssets = allAssets.filter((asset: Asset) => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const matchesSearch = 
        asset.filename.toLowerCase().includes(query) ||
        asset.mime_type.toLowerCase().includes(query) ||
        asset.processing_status.toLowerCase().includes(query)
      
      if (!matchesSearch) return false
    }
    
    // Status filter
    if (filters.status && asset.processing_status !== filters.status) {
      return false
    }
    
    // Type filter
    if (filters.type) {
      const assetType = asset.mime_type.split('/')[0]
      if (assetType !== filters.type) {
        return false
      }
    }
    
    // Date range filter (basic implementation)
    if (filters.dateRange) {
      const assetDate = new Date(asset.created_at)
      const now = new Date()
      
      switch (filters.dateRange) {
        case 'today':
          const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
          if (assetDate < today) return false
          break
        case 'week':
          const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
          if (assetDate < weekAgo) return false
          break
        case 'month':
          const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
          if (assetDate < monthAgo) return false
          break
        case 'year':
          const yearAgo = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000)
          if (assetDate < yearAgo) return false
          break
      }
    }
    
    return true
  })
  
  const assets = filteredAssets
  const folders = foldersData?.folders || []
  
  // Create folder mutation
  const createFolderMutation = useMutation({
    mutationFn: async (folderData: { name: string; parent_id?: string }) => {
      const response = await fetch('http://localhost:2013/api/v1/folders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(folderData)
      })
      if (!response.ok) {
        throw new Error('Failed to create folder')
      }
      return response.json()
    },
    onSuccess: () => {
      toast.success('Ordner erfolgreich erstellt')
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      setShowCreateFolder(false)
      setNewFolderName('')
    },
    onError: (error) => {
      toast.error('Fehler beim Erstellen des Ordners')
      console.error('Create folder error:', error)
    }
  })

  // Move asset mutation
  const moveAssetMutation = useMutation({
    mutationFn: async ({ assetId, folderId }: { assetId: string; folderId: string | null }) => {
      const response = await fetch(`http://localhost:2013/api/v1/assets/${assetId}/move`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ folder_id: folderId })
      })
      if (!response.ok) {
        throw new Error('Failed to move asset')
      }
      return response.json()
    },
    onSuccess: () => {
      toast.success('Asset erfolgreich verschoben')
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['folders'] })
    },
    onError: (error) => {
      toast.error('Fehler beim Verschieben des Assets')
      console.error('Move asset error:', error)
    }
  })

  // Delete folder mutation
  const deleteFolderMutation = useMutation({
    mutationFn: async (folderId: string) => {
      const response = await fetch(`http://localhost:2013/api/v1/folders/${folderId}`, {
        method: 'DELETE'
      })
      if (!response.ok) {
        throw new Error('Failed to delete folder')
      }
      return response.json()
    },
    onSuccess: () => {
      toast.success('Ordner erfolgreich gelöscht')
      queryClient.invalidateQueries({ queryKey: ['folders'] })
      queryClient.invalidateQueries({ queryKey: ['assets'] })
    },
    onError: (error) => {
      toast.error('Fehler beim Löschen des Ordners')
      console.error('Delete folder error:', error)
    }
  })
  
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

  const handleCreateFolder = () => {
    if (newFolderName.trim()) {
      createFolderMutation.mutate({ 
        name: newFolderName.trim(), 
        parent_id: currentFolderId || undefined 
      })
    }
  }

  const handleMoveAsset = (assetId: string, folderId: string | null) => {
    moveAssetMutation.mutate({ assetId, folderId })
  }

  const handleFolderClick = (folderId: string | null) => {
    setCurrentFolderId(folderId)
  }

  const handleFolderContextMenu = (e: React.MouseEvent, folderId: string) => {
    e.preventDefault()
    setShowFolderContextMenu({ x: e.clientX, y: e.clientY, folderId })
  }

  const handleDragStart = (e: React.DragEvent, assetId: string) => {
    setDraggedAsset(assetId)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e: React.DragEvent, folderId?: string | null) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    if (folderId !== undefined) {
      setDragOverFolder(folderId)
    }
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOverFolder(null)
  }

  const handleDrop = (e: React.DragEvent, targetFolderId: string | null) => {
    e.preventDefault()
    if (draggedAsset && draggedAsset !== targetFolderId) {
      // Handle level-up case
      if (targetFolderId === 'level-up') {
        handleMoveAsset(draggedAsset, null) // Move to parent level (null = Main Folder)
      } else {
        handleMoveAsset(draggedAsset, targetFolderId)
      }
    }
    setDraggedAsset(null)
    setDragOverFolder(null)
  }

  const getCurrentFolderPath = () => {
    if (!currentFolderId) return []
    
    const path: Folder[] = []
    const findPath = (folderId: string, allFolders: Folder[]): boolean => {
      const folder = allFolders.find(f => f.id === folderId)
      if (!folder) return false
      
      path.unshift(folder)
      if (folder.parent_id) {
        return findPath(folder.parent_id, allFolders)
      }
      return true
    }
    
    findPath(currentFolderId, folders)
    return path
  }

  const getCurrentFolderName = () => {
    if (!currentFolderId) return 'Main Folder'
    const folder = folders.find((f: Folder) => f.id === currentFolderId)
    return folder?.name || 'Unbekannter Ordner'
  }

  const handleViewAsset = (assetId: string) => {
    const asset = assets.find((a: Asset) => a.id === assetId)
    if (asset) {
      setSelectedAsset(asset)
      if (asset.mime_type === 'application/pdf') {
        setShowPDFViewer(true)
      } else {
        // For non-PDF files, show analysis results or download
        setSelectedAssetForAnalysis(assetId)
      }
    }
  }

  const getFileIcon = (mimeType: string) => {
    if (mimeType.startsWith('video/')) return Video
    if (mimeType.startsWith('image/')) return Image
    if (mimeType.startsWith('audio/')) return Music
    return FileText
  }

  // Mock analysis data creation
  const handleShowAnalysis = (assetId: string) => {
    setSelectedAssetForAnalysis(assetId)
  }

  // Create analysis data for display (real or mock)
  const getAnalysisData = (asset: Asset) => {
    // Try to use real analysis data first
    if ((asset.metadata as any)?.analysis_result?.analysis?.features) {
      const analysis = (asset.metadata as any).analysis_result.analysis
      return {
        asset_id: asset.id,
        filename: asset.filename,
        file_size: asset.file_size,
        mime_type: asset.mime_type,
        dimensions: asset.dimensions || asset.metadata?.dimensions,
        processing_status: asset.processing_status === 'processing' ? 'completed' : 
                           asset.processing_status === 'queued' ? 'pending' : 
                           asset.processing_status as 'completed' | 'pending' | 'failed' | 'processing',
        created_at: asset.created_at,
        features_data: analysis.features.reduce((acc: any, feature: any) => {
          acc[feature.type] = feature.data
          return acc
        }, {}),
        metadata: asset.metadata || {},
        summary: {
          total_features: analysis.features.length,
          processing_time: 1250 // Mock processing time
        },
        features: analysis.features.map((feature: any, index: number) => ({
          id: `f${index + 1}`,
          type: feature.type,
          name: feature.type.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()),
          confidence: feature.confidence || 0.8,
          domain: feature.domain || 'general',
          data: feature.data
        }))
      }
    }
    
    // Fallback to mock data if no real analysis data
    return {
      asset_id: asset.id,
      filename: asset.filename,
      file_size: asset.file_size,
      mime_type: asset.mime_type,
      dimensions: asset.dimensions || asset.metadata?.dimensions,
      processing_status: asset.processing_status === 'processing' ? 'completed' : 
                         asset.processing_status === 'queued' ? 'pending' : 
                         asset.processing_status as 'completed' | 'pending' | 'failed' | 'processing',
      created_at: asset.created_at,
      features_data: asset.metadata?.features_data || {
        "image_quality": "good",
        "objects": ["building", "window", "sky"],
        "colors": ["#FFFFFF", "#0000FF", "#808080"],
        "text": "Sample annotation"
      },
      metadata: asset.metadata || {},
      summary: {
        total_features: 12,
        processing_time: 1250
      },
      features: [
        { id: "f1", type: "object_detection", name: "Building", confidence: 0.87, domain: "computer_vision", data: { text: "Main building structure detected" } },
        { id: "f2", type: "text_extraction", name: "Text Found", confidence: 0.75, domain: "nlp", data: { text: "Architectural elements identified" } },
        { id: "f3", type: "color_analysis", name: "Dominant Colors", confidence: 0.92, domain: "image_processing", data: { text: "Primary color: Blue (#0000FF)" } }
      ]
    }
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
            {assets?.length || 0} files, {folders.filter((folder: Folder) => folder.parent_id === currentFolderId).length} folders
            {(searchQuery || filters.status || filters.type || filters.dateRange) && (
              <span className="text-blue-600 ml-1">(filtered)</span>
            )}
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

      {/* Folder Navigation */}
      <div 
        className={`bg-white rounded-lg border p-4 transition-colors ${
          dragOverFolder === null 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-200'
        }`}
        onDragOver={(e) => handleDragOver(e, null)}
        onDragLeave={handleDragLeave}
        onDrop={(e) => handleDrop(e, null)}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleFolderClick(null)}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
                !currentFolderId 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Home className="w-4 h-4" />
              <span>Main Folder</span>
            </button>
            
            {getCurrentFolderPath().map((folder, index) => (
              <React.Fragment key={folder.id}>
                <ChevronRight className="w-4 h-4 text-gray-400" />
                <button
                  onClick={() => handleFolderClick(folder.id)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
                    currentFolderId === folder.id 
                      ? 'bg-blue-100 text-blue-700' 
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <Folder className="w-4 h-4" />
                  <span>{folder.name}</span>
                </button>
              </React.Fragment>
            ))}
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowCreateFolder(true)}
              className="flex items-center space-x-2 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <FolderPlus className="w-4 h-4" />
              <span>Neuer Ordner</span>
            </button>
          </div>
        </div>

        {/* Current Folder Info */}
        <div className="flex items-center space-x-4 text-sm text-gray-600">
          <div className="flex items-center space-x-1">
            <Folder className="w-4 h-4" />
            <span>Aktueller Ordner: <strong>{getCurrentFolderName()}</strong></span>
          </div>
          {currentFolderId && (
            <button
              onClick={() => handleFolderClick(null)}
              className="text-blue-600 hover:text-blue-700 flex items-center space-x-1"
            >
              <Home className="w-3 h-3" />
              <span>Zurück zum Main Folder</span>
            </button>
          )}
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
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
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
                <option value="application">Document</option>
                <option value="text">Text</option>
              </select>
              
              <select
                value={filters.dateRange}
                onChange={(e) => setFilters(prev => ({ ...prev, dateRange: e.target.value }))}
                className="text-sm border border-gray-300 rounded-md px-2 py-1"
              >
                <option value="">All Time</option>
                <option value="today">Today</option>
                <option value="week">This Week</option>
                <option value="month">This Month</option>
                <option value="year">This Year</option>
              </select>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* Clear Filters Button */}
            {(searchQuery || filters.status || filters.type || filters.dateRange) && (
              <button
                onClick={() => {
                  setSearchQuery('')
                  setFilters({ status: '', type: '', dateRange: '' })
                }}
                className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors"
              >
                Clear Filters
              </button>
            )}
            
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
          {/* Level-Up Card */}
          {currentFolderId && (
            <div 
              className={`bg-white rounded-lg border overflow-hidden hover:shadow-lg transition-all cursor-pointer ${
                dragOverFolder === 'level-up' 
                  ? 'border-green-500 bg-green-50 shadow-lg' 
                  : 'border-gray-200'
              }`}
              onClick={() => handleFolderClick(null)}
              onDragOver={(e) => handleDragOver(e, 'level-up')}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, null)}
            >
              {/* Level-Up Icon */}
              <div className="relative aspect-video bg-gradient-to-br from-green-50 to-green-100 flex items-center justify-center hover:from-green-100 hover:to-green-200 transition-colors">
                <div className="text-center">
                  <ChevronRight className="w-16 h-16 text-green-600 mx-auto mb-2 rotate-180" />
                  <div className="text-sm font-medium text-green-800">Level Up</div>
                  <div className="text-xs text-green-600">Eine Ebene höher</div>
                </div>
                {/* Click overlay */}
                <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-10 transition-all duration-200 flex items-center justify-center opacity-0 hover:opacity-100">
                  <ChevronRight className="w-8 h-8 text-white rotate-180" />
                </div>
              </div>

              {/* Level-Up Info */}
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <h4 className="font-medium text-gray-900 truncate flex-1">
                    Level Up
                  </h4>
                </div>
                
                <div className="space-y-2 text-sm text-gray-600">
                  <div className="flex items-center justify-between">
                    <span className="capitalize">Navigation</span>
                    <span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-800">
                      Up
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span>Action</span>
                    <span>Eine Ebene höher</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
                  <button 
                    onClick={(e) => {
                      e.stopPropagation()
                      handleFolderClick(null)
                    }}
                    className="flex items-center space-x-1 text-green-600 hover:text-green-700 text-sm transition-colors"
                  >
                    <ChevronRight className="w-4 h-4 rotate-180" />
                    <span>Go Up</span>
                  </button>
                  
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-500">Drop assets here to move up</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Folder Cards */}
          {folders
            .filter((folder: Folder) => folder.parent_id === currentFolderId)
            .map((folder: Folder) => (
              <div 
                key={folder.id} 
                className={`bg-white rounded-lg border overflow-hidden hover:shadow-lg transition-all cursor-pointer ${
                  dragOverFolder === folder.id 
                    ? 'border-blue-500 bg-blue-50 shadow-lg' 
                    : 'border-gray-200'
                }`}
                onClick={() => handleFolderClick(folder.id)}
                onContextMenu={(e) => handleFolderContextMenu(e, folder.id)}
                onDragOver={(e) => handleDragOver(e, folder.id)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, folder.id)}
              >
                {/* Folder Icon */}
                <div className="relative aspect-video bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center hover:from-blue-100 hover:to-blue-200 transition-colors">
                  <div className="text-center">
                    <Folder className="w-16 h-16 text-blue-600 mx-auto mb-2" />
                    <div className="text-sm font-medium text-blue-800">{folder.name}</div>
                    <div className="text-xs text-blue-600">{folder.asset_count || 0} items</div>
                  </div>
                  {/* Click overlay */}
                  <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-10 transition-all duration-200 flex items-center justify-center opacity-0 hover:opacity-100">
                    <FolderOpen className="w-8 h-8 text-white" />
                  </div>
                </div>

                {/* Folder Info */}
                <div className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-medium text-gray-900 truncate flex-1">
                      {folder.name}
                    </h4>
                    <button className="p-1 text-gray-400 hover:text-gray-600">
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <div className="space-y-2 text-sm text-gray-600">
                    <div className="flex items-center justify-between">
                      <span className="capitalize">Folder</span>
                      <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800">
                        {folder.asset_count || 0} items
                      </span>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <span>Created</span>
                      <span>{formatDate(folder.created_at)}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
                    <button 
                      onClick={(e) => {
                        e.stopPropagation()
                        handleFolderClick(folder.id)
                      }}
                      className="flex items-center space-x-1 text-blue-600 hover:text-blue-700 text-sm transition-colors"
                    >
                      <FolderOpen className="w-4 h-4" />
                      <span>Open</span>
                    </button>
                    
                    <div className="flex items-center space-x-2">
                      <button 
                        onClick={(e) => {
                          e.stopPropagation()
                          // TODO: Implement folder rename
                        }}
                        className="p-1 text-gray-400 hover:text-gray-600"
                        title="Ordner umbenennen"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm('Möchten Sie diesen Ordner wirklich löschen?')) {
                            deleteFolderMutation.mutate(folder.id)
                          }
                        }}
                        className="p-1 text-red-400 hover:text-red-600"
                        title="Ordner löschen"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}

          {/* Asset Cards */}
          {assets?.map((asset: Asset) => {
            const FileIcon = getFileIcon(asset.mime_type)
            
            return (
              <div 
                key={asset.id} 
                className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow"
                draggable
                onDragStart={(e) => handleDragStart(e, asset.id)}
              >
                {/* Thumbnail - Clickable */}
                <div 
                  className="relative aspect-video bg-gray-100 flex items-center justify-center cursor-pointer hover:bg-gray-200 transition-colors"
                  onClick={() => handleViewAsset(asset.id)}
                >
                  <img 
                    src={`http://localhost:2013/api/v1/assets/${asset.id}/thumbnail`}
                    alt={asset.filename}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      // Fallback to icon if thumbnail fails to load
                      e.currentTarget.style.display = 'none'
                      e.currentTarget.nextElementSibling?.setAttribute('style', 'display: block')
                    }}
                  />
                  <FileIcon className="w-12 h-12 text-gray-400 hidden" />
                  {/* Click overlay */}
                  <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-20 transition-all duration-200 flex items-center justify-center opacity-0 hover:opacity-100">
                    <Eye className="w-8 h-8 text-white" />
                  </div>
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

                    {(asset.dimensions || asset.metadata?.dimensions) && (
                      <div className="text-xs">
                        {(asset.dimensions || asset.metadata?.dimensions)?.width} × {(asset.dimensions || asset.metadata?.dimensions)?.height}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
                    <button 
                      onClick={() => handleViewAsset(asset.id)}
                      className="flex items-center space-x-1 text-blue-600 hover:text-blue-700 text-sm transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                      <span>View</span>
                    </button>
                    
                    <div className="flex items-center space-x-2">
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
            {/* Level-Up Item */}
            {currentFolderId && (
              <div 
                className={`px-6 py-4 cursor-pointer transition-colors ${
                  dragOverFolder === 'level-up' 
                    ? 'bg-green-50 border-green-200' 
                    : 'hover:bg-gray-50'
                }`}
                onClick={() => handleFolderClick(null)}
                onDragOver={(e) => handleDragOver(e, 'level-up')}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, null)}
              >
                <div className="flex items-center space-x-4">
                  <input
                    type="checkbox"
                    disabled
                    className="rounded border-gray-300 opacity-50"
                  />
                  
                  <div 
                    className="w-12 h-12 bg-gradient-to-br from-green-50 to-green-100 rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden hover:from-green-100 hover:to-green-200 transition-colors relative"
                  >
                    <ChevronRight className="w-6 h-6 text-green-600 rotate-180" />
                    {/* Click overlay */}
                    <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-20 transition-all duration-200 flex items-center justify-center opacity-0 hover:opacity-100 rounded-lg">
                      <ChevronRight className="w-4 h-4 text-white rotate-180" />
                    </div>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-gray-900 truncate">
                      Level Up
                    </h4>
                    <div className="flex items-center space-x-4 mt-1 text-sm text-gray-600">
                      <span className="capitalize">Navigation</span>
                      <span>Eine Ebene höher</span>
                      <span>Drop assets here to move up</span>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-800">
                      Level Up
                    </span>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation()
                        handleFolderClick(null)
                      }}
                      className="p-2 text-green-400 hover:text-green-600 transition-colors"
                      title="Eine Ebene höher"
                    >
                      <ChevronRight className="w-4 h-4 rotate-180" />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Folder Items */}
            {folders
              .filter((folder: Folder) => folder.parent_id === currentFolderId)
              .map((folder: Folder) => (
                <div 
                  key={folder.id} 
                  className={`px-6 py-4 cursor-pointer transition-colors ${
                    dragOverFolder === folder.id 
                      ? 'bg-blue-50 border-blue-200' 
                      : 'hover:bg-gray-50'
                  }`}
                  onClick={() => handleFolderClick(folder.id)}
                  onContextMenu={(e) => handleFolderContextMenu(e, folder.id)}
                  onDragOver={(e) => handleDragOver(e, folder.id)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, folder.id)}
                >
                  <div className="flex items-center space-x-4">
                    <input
                      type="checkbox"
                      disabled
                      className="rounded border-gray-300 opacity-50"
                    />
                    
                    <div 
                      className="w-12 h-12 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden hover:from-blue-100 hover:to-blue-200 transition-colors relative"
                    >
                      <Folder className="w-6 h-6 text-blue-600" />
                      {/* Click overlay */}
                      <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-20 transition-all duration-200 flex items-center justify-center opacity-0 hover:opacity-100 rounded-lg">
                        <FolderOpen className="w-4 h-4 text-white" />
                      </div>
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-gray-900 truncate">
                        {folder.name}
                      </h4>
                      <div className="flex items-center space-x-4 mt-1 text-sm text-gray-600">
                        <span className="capitalize">Folder</span>
                        <span>{folder.asset_count || 0} items</span>
                        <span>{formatDate(folder.created_at)}</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800">
                        Folder
                      </span>
                      <button 
                        onClick={(e) => {
                          e.stopPropagation()
                          handleFolderClick(folder.id)
                        }}
                        className="p-2 text-blue-400 hover:text-blue-600 transition-colors"
                        title="Ordner öffnen"
                      >
                        <FolderOpen className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={(e) => {
                          e.stopPropagation()
                          // TODO: Implement folder rename
                        }}
                        className="p-2 text-gray-400 hover:text-gray-600"
                        title="Umbenennen"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button 
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm('Möchten Sie diesen Ordner wirklich löschen?')) {
                            deleteFolderMutation.mutate(folder.id)
                          }
                        }}
                        className="p-2 text-red-400 hover:text-red-600"
                        title="Löschen"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}

            {/* Asset Items */}
            {assets?.map((asset: Asset) => {
              const FileIcon = getFileIcon(asset.mime_type)
              
              return (
                <div 
                  key={asset.id} 
                  className="px-6 py-4 hover:bg-gray-50"
                  draggable
                  onDragStart={(e) => handleDragStart(e, asset.id)}
                >
                  <div className="flex items-center space-x-4">
                    <input
                      type="checkbox"
                      checked={selectedAssets.includes(asset.id)}
                      onChange={() => toggleAssetSelection(asset.id)}
                      className="rounded border-gray-300"
                    />
                    
                    <div 
                      className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden cursor-pointer hover:bg-gray-200 transition-colors relative"
                      onClick={() => handleViewAsset(asset.id)}
                    >
                      <img 
                        src={`http://localhost:2013/api/v1/assets/${asset.id}/thumbnail`}
                        alt={asset.filename}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none'
                          e.currentTarget.nextElementSibling?.setAttribute('style', 'display: block')
                        }}
                      />
                      <FileIcon className="w-6 h-6 text-gray-400 hidden" />
                      {/* Click overlay */}
                      <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-20 transition-all duration-200 flex items-center justify-center opacity-0 hover:opacity-100 rounded-lg">
                        <Eye className="w-4 h-4 text-white" />
                      </div>
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
                        onClick={() => handleViewAsset(asset.id)}
                        className="p-2 text-blue-400 hover:text-blue-600 transition-colors"
                        title="Asset anzeigen"
                      >
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
      {assets?.length === 0 && folders.filter((folder: Folder) => folder.parent_id === currentFolderId).length === 0 && (
        <div className="text-center py-12">
          <FolderOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          {allAssets?.length === 0 && folders.length === 0 ? (
            <>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No assets or folders found</h3>
              <p className="text-gray-600 mb-4">Upload some files or create folders to get started</p>
              <div className="flex items-center justify-center space-x-4">
                <button
                  onClick={() => setShowCreateFolder(true)}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center space-x-2"
                >
                  <FolderPlus className="w-4 h-4" />
                  <span>Create Folder</span>
                </button>
              </div>
            </>
          ) : (
            <>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No items match your filters</h3>
              <p className="text-gray-600 mb-4">
                Try adjusting your search criteria or clear the filters
              </p>
              <button
                onClick={() => {
                  setSearchQuery('')
                  setFilters({ status: '', type: '', dateRange: '' })
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Clear All Filters
              </button>
            </>
          )}
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

      {/* PDF Viewer Modal */}
      {selectedAsset && (
        <PDFViewer
          isOpen={showPDFViewer}
          onClose={() => {
            setShowPDFViewer(false)
            setSelectedAsset(null)
          }}
          assetId={selectedAsset.id}
          filename={selectedAsset.filename}
        />
      )}

      {/* Create Folder Modal */}
      {showCreateFolder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                <FolderPlus className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Neuen Ordner erstellen
                </h3>
                <p className="text-sm text-gray-600">
                  {currentFolderId ? 'in ' + getCurrentFolderName() : 'im Hauptverzeichnis'}
                </p>
              </div>
            </div>
            
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Ordnername
              </label>
              <input
                type="text"
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                placeholder="z.B. Meine Bilder"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                autoFocus
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleCreateFolder()
                  }
                }}
              />
            </div>
            
            <div className="flex items-center justify-end space-x-3">
              <button
                onClick={() => {
                  setShowCreateFolder(false)
                  setNewFolderName('')
                }}
                disabled={createFolderMutation.isPending}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50"
              >
                Abbrechen
              </button>
              <button
                onClick={handleCreateFolder}
                disabled={createFolderMutation.isPending || !newFolderName.trim()}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center space-x-2"
              >
                {createFolderMutation.isPending ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Erstelle...</span>
                  </>
                ) : (
                  <>
                    <FolderPlus className="w-4 h-4" />
                    <span>Erstellen</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Folder Context Menu */}
      {showFolderContextMenu && (
        <div 
          className="fixed z-50 bg-white rounded-lg shadow-lg border border-gray-200 py-2 min-w-[160px]"
          style={{
            left: showFolderContextMenu.x,
            top: showFolderContextMenu.y
          }}
          onClick={() => setShowFolderContextMenu(null)}
        >
          <button
            onClick={() => {
              // TODO: Implement folder rename
              setShowFolderContextMenu(null)
            }}
            className="w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-100 flex items-center space-x-2"
          >
            <Edit className="w-4 h-4" />
            <span>Umbenennen</span>
          </button>
          <button
            onClick={() => {
              if (confirm('Möchten Sie diesen Ordner wirklich löschen?')) {
                deleteFolderMutation.mutate(showFolderContextMenu.folderId)
                setShowFolderContextMenu(null)
              }
            }}
            className="w-full px-4 py-2 text-left text-red-600 hover:bg-red-50 flex items-center space-x-2"
          >
            <Trash2 className="w-4 h-4" />
            <span>Löschen</span>
          </button>
        </div>
      )}
    </div>
  )
}

export default Assets
