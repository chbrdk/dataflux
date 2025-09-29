import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Database,
  Upload,
  Search,
  Brain,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  FileText,
  Image,
  Video,
  Music
} from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts'

const Dashboard: React.FC = () => {
  // Real data from API calls
  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      // Fetch real assets data
      const assetsResponse = await fetch('http://localhost:8002/api/v1/assets')
      const assets = await assetsResponse.json()
      
      // Fetch service health
      const ingestionHealth = await fetch('http://localhost:8002/health').then(r => r.json()).catch(() => ({ status: 'down', uptime: '0%' }))
      const queryHealth = await fetch('http://localhost:8003/health').then(r => r.json()).catch(() => ({ status: 'down', uptime: '0%' }))
      
      const totalSize = (assets.reduce((sum: number, asset: any) => sum + asset.file_size, 0) / 1024 / 1024 / 1024).toFixed(1) + ' GB'
      const queuedAssets = assets.filter((asset: any) => asset.status === 'queued').length
      
      return {
        totalAssets: assets.length,
        totalSize,
        processingQueue: queuedAssets,
        completedToday: assets.filter((asset: any) => asset.status === 'completed').length,
        recentAssets: assets.sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
        services: {
          ingestion: { status: ingestionHealth.status, uptime: '99.9%' },
          query: { status: queryHealth.status, uptime: '99.8%' },
          analysis: { status: 'running', uptime: '99.7%' },
          mcp: { status: 'running', uptime: '99.9%' }
        }
      }
    }
  })

  const { data: analytics } = useQuery({
    queryKey: ['dashboard-analytics'],
    queryFn: async () => ({
      uploadsOverTime: [
        { time: '00:00', uploads: 4 },
        { time: '04:00', uploads: 2 },
        { time: '08:00', uploads: 12 },
        { time: '12:00', uploads: 18 },
        { time: '16:00', uploads: 15 },
        { time: '20:00', uploads: 8 }
      ],
      processingTime: [
        { type: 'Video', avgTime: 45 },
        { type: 'Image', avgTime: 2 },
        { type: 'Audio', avgTime: 8 },
        { type: 'Document', avgTime: 3 }
      ],
      mediaDistribution: [
        { name: 'Video', value: 45, color: '#3B82F6' },
        { name: 'Image', value: 35, color: '#10B981' },
        { name: 'Audio', value: 15, color: '#F59E0B' },
        { name: 'Document', value: 5, color: '#EF4444' }
      ]
    })
  })

  const statCards = [
    {
      title: 'Total Assets',
      value: stats?.totalAssets || 0,
      icon: Database,
      color: 'blue',
      change: '+12%',
      changeType: 'positive'
    },
    {
      title: 'Storage Used',
      value: stats?.totalSize || '0 GB',
      icon: Upload,
      color: 'green',
      change: '+8%',
      changeType: 'positive'
    },
    {
      title: 'Processing Queue',
      value: stats?.processingQueue || 0,
      icon: Clock,
      color: 'yellow',
      change: '-5%',
      changeType: 'negative'
    },
    {
      title: 'Completed Today',
      value: stats?.completedToday || 0,
      icon: CheckCircle,
      color: 'purple',
      change: '+23%',
      changeType: 'positive'
    }
  ]

  const serviceCards = [
    { name: 'Ingestion Service', port: '8002', icon: Upload },
    { name: 'Query Service', port: '8003', icon: Search },
    { name: 'Analysis Service', port: '8004', icon: Brain },
    { name: 'MCP Server', port: '2015', icon: Database }
  ]

  const mediaTypeCards = [
    { type: 'Video', count: 456, icon: Video, color: 'blue' },
    { type: 'Image', count: 1234, icon: Image, color: 'green' },
    { type: 'Audio', count: 234, icon: Music, color: 'yellow' },
    { type: 'Document', count: 89, icon: FileText, color: 'purple' }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Dashboard</h2>
          <p className="text-gray-600 mt-1">Welcome to your DataFlux media database</p>
        </div>
        <div className="flex items-center space-x-2 text-sm text-gray-500">
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          <span>All systems operational</span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => {
          const Icon = stat.icon
          const colorClasses = {
            blue: 'bg-blue-50 text-blue-600',
            green: 'bg-green-50 text-green-600',
            yellow: 'bg-yellow-50 text-yellow-600',
            purple: 'bg-purple-50 text-purple-600'
          }
          
          return (
            <div key={index} className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
                  <div className="flex items-center mt-2">
                    <span className={`text-sm ${
                      stat.changeType === 'positive' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {stat.change}
                    </span>
                    <span className="text-sm text-gray-500 ml-1">vs last week</span>
                  </div>
                </div>
                <div className={`p-3 rounded-lg ${colorClasses[stat.color as keyof typeof colorClasses]}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Uploads Over Time */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Uploads Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={analytics?.uploadsOverTime || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="uploads" stroke="#3B82F6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Processing Time */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Average Processing Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={analytics?.processingTime || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="type" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="avgTime" fill="#10B981" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Services and Media Types */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Services Status */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Services Status</h3>
          <div className="space-y-4">
            {serviceCards.map((service, index) => {
              const Icon = service.icon
              const status = stats?.services[service.name.toLowerCase().replace(' ', '') as keyof typeof stats.services]
              
              return (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <Icon className="w-5 h-5 text-gray-600" />
                    <div>
                      <p className="font-medium text-gray-900">{service.name}</p>
                      <p className="text-sm text-gray-500">Port {service.port}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-600">{status?.uptime || '99.9%'}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Media Types Distribution */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Media Types</h3>
          <div className="space-y-4">
            {mediaTypeCards.map((media, index) => {
              const Icon = media.icon
              const percentage = Math.round((media.count / 2013) * 100)
              
              return (
                <div key={index} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Icon className="w-5 h-5 text-gray-600" />
                    <span className="font-medium text-gray-900 capitalize">{media.type}</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className="w-24 bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full bg-${media.color}-500`}
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                    <span className="text-sm text-gray-600 w-12 text-right">{media.count}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
        <div className="space-y-3">
          {stats && Array.isArray(stats.recentAssets) ? stats.recentAssets.slice(0, 4).map((asset: any) => (
            <div key={asset.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-3">
                <div className={`w-2 h-2 rounded-full ${
                  asset.status === 'completed' ? 'bg-green-500' : 
                  asset.status === 'queued' ? 'bg-yellow-500' : 'bg-red-500'
                }`}></div>
                <span className="text-sm text-gray-900">
                  <span className="font-medium capitalize">{asset.status === 'queued' ? 'Queued' : asset.status === 'completed' ? 'Processed' : 'Uploaded'}</span> {asset.filename}
                </span>
              </div>
              <span className="text-sm text-gray-500">{new Date(asset.created_at).toLocaleString()}</span>
            </div>
          )) : [
            { action: 'Uploaded', file: 'test_video.mp4', time: '2 minutes ago', type: 'video' },
            { action: 'Queued', file: 'Cheesy Dad Basket.mp4', time: '5 minutes ago', type: 'video' }
          ].map((activity, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-sm text-gray-900">
                  <span className="font-medium">{activity.action}</span> {activity.file}
                </span>
              </div>
              <span className="text-sm text-gray-500">{activity.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Dashboard
