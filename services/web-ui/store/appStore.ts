import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ViewType = 'dashboard' | 'upload' | 'search' | 'assets' | 'analytics'

interface AppState {
  // UI State
  currentView: ViewType
  setCurrentView: (view: ViewType) => void
  
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  
  // Upload State
  uploadProgress: Record<string, number>
  setUploadProgress: (fileId: string, progress: number) => void
  
  // Search State
  searchQuery: string
  setSearchQuery: (query: string) => void
  
  searchResults: any[]
  setSearchResults: (results: any[]) => void
  
  // Assets State
  selectedAssets: string[]
  setSelectedAssets: (assets: string[]) => void
  
  // Analytics State
  analyticsTimeRange: '1h' | '24h' | '7d' | '30d'
  setAnalyticsTimeRange: (range: '1h' | '24h' | '7d' | '30d') => void
  
  // Service Status
  serviceStatus: Record<string, 'running' | 'stopped' | 'error'>
  setServiceStatus: (service: string, status: 'running' | 'stopped' | 'error') => void
  
  // Notifications
  notifications: Array<{
    id: string
    type: 'success' | 'error' | 'warning' | 'info'
    title: string
    message: string
    timestamp: Date
  }>
  addNotification: (notification: Omit<AppState['notifications'][0], 'id' | 'timestamp'>) => void
  removeNotification: (id: string) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // UI State
      currentView: 'dashboard',
      setCurrentView: (view) => set({ currentView: view }),
      
      sidebarOpen: true,
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      
      // Upload State
      uploadProgress: {},
      setUploadProgress: (fileId, progress) => 
        set((state) => ({
          uploadProgress: { ...state.uploadProgress, [fileId]: progress }
        })),
      
      // Search State
      searchQuery: '',
      setSearchQuery: (query) => set({ searchQuery: query }),
      
      searchResults: [],
      setSearchResults: (results) => set({ searchResults: results }),
      
      // Assets State
      selectedAssets: [],
      setSelectedAssets: (assets) => set({ selectedAssets: assets }),
      
      // Analytics State
      analyticsTimeRange: '24h',
      setAnalyticsTimeRange: (range) => set({ analyticsTimeRange: range }),
      
      // Service Status
      serviceStatus: {
        ingestion: 'running',
        query: 'running',
        analysis: 'running',
        mcp: 'running'
      },
      setServiceStatus: (service, status) =>
        set((state) => ({
          serviceStatus: { ...state.serviceStatus, [service]: status }
        })),
      
      // Notifications
      notifications: [],
      addNotification: (notification) =>
        set((state) => ({
          notifications: [
            ...state.notifications,
            {
              ...notification,
              id: Math.random().toString(36).substr(2, 9),
              timestamp: new Date()
            }
          ]
        })),
      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter(n => n.id !== id)
        }))
    }),
    {
      name: 'dataflux-app-store',
      partialize: (state) => ({
        currentView: state.currentView,
        sidebarOpen: state.sidebarOpen,
        analyticsTimeRange: state.analyticsTimeRange
      })
    }
  )
)
