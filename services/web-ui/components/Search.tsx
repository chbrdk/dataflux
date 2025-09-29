import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Search as SearchIcon,
  Filter,
  Grid,
  List,
  Play,
  Download,
  Eye,
  Clock,
  FileText,
  Image,
  Video,
  Music,
  Star,
  Tag
} from 'lucide-react'
import { useAppStore } from '../store/appStore'

interface SearchResult {
  id: string
  type: 'video' | 'image' | 'audio' | 'document'
  filename: string
  mime_type: string
  file_size: number
  created_at: string
  score: number
  metadata: {
    duration?: number
    dimensions?: { width: number; height: number }
    thumbnail?: string
    tags?: string[]
  }
}

const Search: React.FC = () => {
  const [query, setQuery] = useState('')
  const [selectedFilters, setSelectedFilters] = useState({
    mediaTypes: [] as string[],
    dateRange: '',
    fileSize: '',
    sortBy: 'relevance'
  })
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const { searchQuery, setSearchQuery, searchResults, setSearchResults } = useAppStore()

  const searchMutation = useMutation({
    mutationFn: async (searchQuery: string) => {
      const response = await fetch('http://localhost:8003/api/v1/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: searchQuery,
          media_types: selectedFilters.mediaTypes.length > 0 ? selectedFilters.mediaTypes : undefined,
          limit: 50,
          include_segments: true
        })
      })

      if (!response.ok) {
        throw new Error('Search failed')
      }

      return response.json()
    },
    onSuccess: (data) => {
      setSearchResults(data.results || [])
      toast.success(`Found ${data.results?.length || 0} results`)
    },
    onError: (error) => {
      toast.error('Search failed')
      console.error('Search error:', error)
    }
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      setSearchQuery(query)
      searchMutation.mutate(query)
    }
  }

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'video': return Video
      case 'image': return Image
      case 'audio': return Music
      default: return FileText
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Search</h2>
        <p className="text-gray-600 mt-1">Multi-modal search across all your media</p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="relative">
          <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for videos, images, audio, or documents..."
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg text-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-gray-600" />
            <span className="text-sm font-medium text-gray-700">Filters:</span>
          </div>

          {/* Media Type Filter */}
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600">Type:</label>
            <select
              value={selectedFilters.mediaTypes[0] || ''}
              onChange={(e) => setSelectedFilters(prev => ({
                ...prev,
                mediaTypes: e.target.value ? [e.target.value] : []
              }))}
              className="text-sm border border-gray-300 rounded-md px-2 py-1"
            >
              <option value="">All Types</option>
              <option value="video">Video</option>
              <option value="image">Image</option>
              <option value="audio">Audio</option>
              <option value="document">Document</option>
            </select>
          </div>

          {/* Sort Filter */}
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600">Sort:</label>
            <select
              value={selectedFilters.sortBy}
              onChange={(e) => setSelectedFilters(prev => ({
                ...prev,
                sortBy: e.target.value
              }))}
              className="text-sm border border-gray-300 rounded-md px-2 py-1"
            >
              <option value="relevance">Relevance</option>
              <option value="date">Date</option>
              <option value="size">File Size</option>
              <option value="name">Name</option>
            </select>
          </div>
        </div>

        <button
          type="submit"
          disabled={searchMutation.isPending}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {searchMutation.isPending ? 'Searching...' : 'Search'}
        </button>
      </form>

      {/* Search Results */}
      {searchMutation.isSuccess && (
        <div className="space-y-4">
          {/* Results Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Search Results ({searchResults.length})
              </h3>
              <div className="flex items-center space-x-2">
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
            </div>
          </div>

          {/* Results Grid/List */}
          {viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {searchResults.map((result: SearchResult) => {
                const FileIcon = getFileIcon(result.type)
                
                return (
                  <div key={result.id} className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow">
                    {/* Thumbnail */}
                    <div className="aspect-video bg-gray-100 flex items-center justify-center">
                      {result.metadata.thumbnail ? (
                        <img 
                          src={result.metadata.thumbnail} 
                          alt={result.filename}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <FileIcon className="w-12 h-12 text-gray-400" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="p-4">
                      <h4 className="font-medium text-gray-900 truncate mb-2">
                        {result.filename}
                      </h4>
                      
                      <div className="space-y-2 text-sm text-gray-600">
                        <div className="flex items-center justify-between">
                          <span className="capitalize">{result.type}</span>
                          <span className="text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded-full">
                            {Math.round(result.score * 100)}% match
                          </span>
                        </div>
                        
                        <div className="flex items-center justify-between">
                          <span>{formatFileSize(result.file_size)}</span>
                          <span>{formatDate(result.created_at)}</span>
                        </div>

                        {result.metadata.duration && (
                          <div className="flex items-center space-x-1">
                            <Clock className="w-3 h-3" />
                            <span>{formatDuration(result.metadata.duration)}</span>
                          </div>
                        )}

                        {result.metadata.dimensions && (
                          <div className="text-xs">
                            {result.metadata.dimensions.width} × {result.metadata.dimensions.height}
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
            <div className="space-y-3">
              {searchResults.map((result: SearchResult) => {
                const FileIcon = getFileIcon(result.type)
                
                return (
                  <div key={result.id} className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
                    <div className="flex items-center space-x-4">
                      <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <FileIcon className="w-8 h-8 text-gray-400" />
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-gray-900 truncate">
                          {result.filename}
                        </h4>
                        <div className="flex items-center space-x-4 mt-1 text-sm text-gray-600">
                          <span className="capitalize">{result.type}</span>
                          <span>{formatFileSize(result.file_size)}</span>
                          <span>{formatDate(result.created_at)}</span>
                          {result.metadata.duration && (
                            <span>{formatDuration(result.metadata.duration)}</span>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <span className="text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded-full">
                          {Math.round(result.score * 100)}% match
                        </span>
                        <button className="p-2 text-gray-400 hover:text-gray-600">
                          <Eye className="w-4 h-4" />
                        </button>
                        <button className="p-2 text-gray-400 hover:text-gray-600">
                          <Download className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* No Results */}
      {searchMutation.isSuccess && searchResults.length === 0 && (
        <div className="text-center py-12">
          <SearchIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No results found</h3>
          <p className="text-gray-600">Try adjusting your search terms or filters</p>
        </div>
      )}
    </div>
  )
}

export default Search
