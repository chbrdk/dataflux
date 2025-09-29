import React from 'react'
import { useAppStore } from '../store/appStore'
import { Bell, User, Search, RefreshCw } from 'lucide-react'

const Header: React.FC = () => {
  const { currentView, setCurrentView } = useAppStore()

  const getPageTitle = () => {
    switch (currentView) {
      case 'dashboard': return 'Dashboard'
      case 'upload': return 'Upload Media'
      case 'search': return 'Search'
      case 'assets': return 'Assets'
      case 'analytics': return 'Analytics'
      default: return 'DataFlux'
    }
  }

  const getPageDescription = () => {
    switch (currentView) {
      case 'dashboard': return 'Overview of your media database'
      case 'upload': return 'Upload and process media files'
      case 'search': return 'Multi-modal search across all media'
      case 'assets': return 'Manage your media assets'
      case 'analytics': return 'Processing statistics and insights'
      default: return 'AI-powered media database'
    }
  }

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Page Info */}
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            {getPageTitle()}
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            {getPageDescription()}
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-4">
          {/* Quick Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Quick search..."
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Refresh Button */}
          <button className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors">
            <RefreshCw className="w-5 h-5" />
          </button>

          {/* Notifications */}
          <button className="relative p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>

          {/* User Menu */}
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
              <User className="w-5 h-5 text-white" />
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-medium text-gray-900">Admin User</p>
              <p className="text-xs text-gray-500">admin@dataflux.local</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header
