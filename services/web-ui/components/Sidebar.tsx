import React from 'react'
import { useAppStore, ViewType } from '../store/appStore'
import {
  LayoutDashboard,
  Upload,
  Search,
  FolderOpen,
  BarChart3,
  Settings,
  Menu,
  X,
  Database,
  Brain,
  FileText,
  Image,
  Video,
  Music
} from 'lucide-react'

const Sidebar: React.FC = () => {
  const { 
    currentView, 
    setCurrentView, 
    sidebarOpen, 
    setSidebarOpen 
  } = useAppStore()

  const menuItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: LayoutDashboard,
      description: 'Overview and statistics'
    },
    {
      id: 'upload',
      label: 'Upload',
      icon: Upload,
      description: 'Upload media files'
    },
    {
      id: 'search',
      label: 'Search',
      icon: Search,
      description: 'Multi-modal search'
    },
    {
      id: 'assets',
      label: 'Assets',
      icon: FolderOpen,
      description: 'Manage media assets'
    },
    {
      id: 'analytics',
      label: 'Analytics',
      icon: BarChart3,
      description: 'Processing analytics'
    }
  ]

  const serviceItems = [
    {
      id: 'ingestion',
      label: 'Ingestion Service',
      icon: Upload,
      status: 'running',
      port: '2013'
    },
    {
      id: 'query',
      label: 'Query Service',
      icon: Search,
      status: 'running',
      port: '8003'
    },
    {
      id: 'analysis',
      label: 'Analysis Service',
      icon: Brain,
      status: 'running',
      port: '8004'
    },
    {
      id: 'mcp',
      label: 'MCP Server',
      icon: Database,
      status: 'running',
      port: '2015'
    }
  ]

  const mediaTypes = [
    { type: 'video', icon: Video, count: 42 },
    { type: 'image', icon: Image, count: 128 },
    { type: 'audio', icon: Music, count: 67 },
    { type: 'document', icon: FileText, count: 23 }
  ]

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed left-0 top-0 h-full bg-white border-r border-gray-200 z-50
        transition-all duration-300 ease-in-out
        ${sidebarOpen ? 'w-64' : 'w-16'}
      `}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          {sidebarOpen && (
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <Database className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-semibold text-gray-900">DataFlux</span>
            </div>
          )}
          
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            {sidebarOpen ? (
              <X className="w-5 h-5 text-gray-600" />
            ) : (
              <Menu className="w-5 h-5 text-gray-600" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto">
          {/* Main Menu */}
          <div className="p-4">
            {sidebarOpen && (
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Navigation
              </h3>
            )}
            
            <div className="space-y-1">
              {menuItems.map((item) => {
                const Icon = item.icon
                const isActive = currentView === item.id
                
                return (
                  <button
                    key={item.id}
                    onClick={() => setCurrentView(item.id as ViewType)}
                    className={`
                      w-full flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors
                      ${isActive 
                        ? 'bg-blue-50 text-blue-700 border border-blue-200' 
                        : 'text-gray-700 hover:bg-gray-100'
                      }
                    `}
                    title={sidebarOpen ? undefined : item.description}
                  >
                    <Icon className={`w-5 h-5 ${sidebarOpen ? 'mr-3' : 'mx-auto'}`} />
                    {sidebarOpen && <span>{item.label}</span>}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Services Status */}
          <div className="p-4 border-t border-gray-200">
            {sidebarOpen && (
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Services
              </h3>
            )}
            
            <div className="space-y-2">
              {serviceItems.map((service) => {
                const Icon = service.icon
                const statusColor = service.status === 'running' ? 'text-green-500' : 'text-red-500'
                
                return (
                  <div
                    key={service.id}
                    className={`
                      flex items-center px-3 py-2 rounded-lg text-sm
                      ${sidebarOpen ? 'justify-between' : 'justify-center'}
                    `}
                    title={sidebarOpen ? undefined : `${service.label} (${service.status})`}
                  >
                    <div className="flex items-center">
                      <Icon className={`w-4 h-4 ${sidebarOpen ? 'mr-2' : 'mx-auto'} text-gray-600`} />
                      {sidebarOpen && <span className="text-gray-700">{service.label}</span>}
                    </div>
                    
                    {sidebarOpen && (
                      <div className="flex items-center space-x-2">
                        <div className={`w-2 h-2 rounded-full ${service.status === 'running' ? 'bg-green-500' : 'bg-red-500'}`} />
                        <span className="text-xs text-gray-500">{service.port}</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Media Types */}
          <div className="p-4 border-t border-gray-200">
            {sidebarOpen && (
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Media Types
              </h3>
            )}
            
            <div className="space-y-2">
              {mediaTypes.map((media) => {
                const Icon = media.icon
                
                return (
                  <div
                    key={media.type}
                    className={`
                      flex items-center px-3 py-2 rounded-lg text-sm
                      ${sidebarOpen ? 'justify-between' : 'justify-center'}
                    `}
                    title={sidebarOpen ? undefined : `${media.type}: ${media.count} files`}
                  >
                    <div className="flex items-center">
                      <Icon className={`w-4 h-4 ${sidebarOpen ? 'mr-2' : 'mx-auto'} text-gray-600`} />
                      {sidebarOpen && (
                        <span className="text-gray-700 capitalize">{media.type}</span>
                      )}
                    </div>
                    
                    {sidebarOpen && (
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                        {media.count}
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200">
          <button className="w-full flex items-center px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-gray-100 transition-colors">
            <Settings className={`w-5 h-5 ${sidebarOpen ? 'mr-3' : 'mx-auto'}`} />
            {sidebarOpen && <span>Settings</span>}
          </button>
        </div>
      </div>
    </>
  )
}

export default Sidebar
