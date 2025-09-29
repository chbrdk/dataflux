import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart3,
  TrendingUp,
  Clock,
  Database,
  Cpu,
  HardDrive,
  Activity,
  Calendar,
  Download,
  Upload,
  Play,
  Pause
} from 'lucide-react'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  PieChart, 
  Pie, 
  Cell,
  AreaChart,
  Area
} from 'recharts'
import { useAppStore } from '../store/appStore'

const Analytics: React.FC = () => {
  const { analyticsTimeRange, setAnalyticsTimeRange } = useAppStore()
  const [selectedMetric, setSelectedMetric] = useState('processing')

  const { data: analytics } = useQuery({
    queryKey: ['analytics', analyticsTimeRange],
    queryFn: async () => ({
      // Mock data - in production, this would come from API calls
      processingStats: {
        totalProcessed: 1234,
        processingTime: 45.2,
        successRate: 98.5,
        queueSize: 12
      },
      uploadStats: {
        totalUploads: 567,
        totalSize: '2.3 TB',
        averageSize: '4.1 MB',
        uploadSpeed: '12.5 MB/s'
      },
      serviceStats: {
        ingestion: { uptime: 99.9, requests: 1234, avgResponseTime: 45 },
        query: { uptime: 99.8, requests: 5678, avgResponseTime: 23 },
        analysis: { uptime: 99.7, requests: 890, avgResponseTime: 120 },
        mcp: { uptime: 99.9, requests: 234, avgResponseTime: 67 }
      },
      processingOverTime: [
        { time: '00:00', processed: 4, queued: 2 },
        { time: '04:00', processed: 2, queued: 1 },
        { time: '08:00', processed: 12, queued: 8 },
        { time: '12:00', processed: 18, queued: 5 },
        { time: '16:00', processed: 15, queued: 3 },
        { time: '20:00', processed: 8, queued: 2 }
      ],
      mediaTypeDistribution: [
        { name: 'Video', value: 45, count: 456, color: '#3B82F6' },
        { name: 'Image', value: 35, count: 1234, color: '#10B981' },
        { name: 'Audio', value: 15, count: 234, color: '#F59E0B' },
        { name: 'Document', value: 5, count: 89, color: '#EF4444' }
      ],
      processingTimeByType: [
        { type: 'Video', avgTime: 45, minTime: 12, maxTime: 120 },
        { type: 'Image', avgTime: 2, minTime: 1, maxTime: 5 },
        { type: 'Audio', avgTime: 8, minTime: 3, maxTime: 25 },
        { type: 'Document', avgTime: 3, minTime: 1, maxTime: 8 }
      ],
      systemMetrics: {
        cpuUsage: 45.2,
        memoryUsage: 67.8,
        diskUsage: 23.4,
        networkIO: 12.5
      }
    })
  })

  const timeRangeOptions = [
    { value: '1h', label: 'Last Hour' },
    { value: '24h', label: 'Last 24 Hours' },
    { value: '7d', label: 'Last 7 Days' },
    { value: '30d', label: 'Last 30 Days' }
  ]

  const metricCards = [
    {
      title: 'Total Processed',
      value: analytics?.processingStats.totalProcessed || 0,
      icon: Database,
      color: 'blue',
      change: '+12%',
      changeType: 'positive'
    },
    {
      title: 'Avg Processing Time',
      value: `${analytics?.processingStats.processingTime || 0}s`,
      icon: Clock,
      color: 'green',
      change: '-8%',
      changeType: 'negative'
    },
    {
      title: 'Success Rate',
      value: `${analytics?.processingStats.successRate || 0}%`,
      icon: TrendingUp,
      color: 'purple',
      change: '+2%',
      changeType: 'positive'
    },
    {
      title: 'Queue Size',
      value: analytics?.processingStats.queueSize || 0,
      icon: Activity,
      color: 'yellow',
      change: '-15%',
      changeType: 'negative'
    }
  ]

  const systemCards = [
    {
      title: 'CPU Usage',
      value: `${analytics?.systemMetrics.cpuUsage || 0}%`,
      icon: Cpu,
      color: 'blue'
    },
    {
      title: 'Memory Usage',
      value: `${analytics?.systemMetrics.memoryUsage || 0}%`,
      icon: Database,
      color: 'green'
    },
    {
      title: 'Disk Usage',
      value: `${analytics?.systemMetrics.diskUsage || 0}%`,
      icon: HardDrive,
      color: 'yellow'
    },
    {
      title: 'Network I/O',
      value: `${analytics?.systemMetrics.networkIO || 0} MB/s`,
      icon: Activity,
      color: 'purple'
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Analytics</h2>
          <p className="text-gray-600 mt-1">Processing statistics and system metrics</p>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-gray-600" />
            <select
              value={analyticsTimeRange}
              onChange={(e) => setAnalyticsTimeRange(e.target.value as any)}
              className="text-sm border border-gray-300 rounded-md px-3 py-2"
            >
              {timeRangeOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Processing Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metricCards.map((card, index) => {
          const Icon = card.icon
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
                  <p className="text-sm font-medium text-gray-600">{card.title}</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{card.value}</p>
                  <div className="flex items-center mt-2">
                    <span className={`text-sm ${
                      card.changeType === 'positive' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {card.change}
                    </span>
                    <span className="text-sm text-gray-500 ml-1">vs last period</span>
                  </div>
                </div>
                <div className={`p-3 rounded-lg ${colorClasses[card.color as keyof typeof colorClasses]}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Processing Over Time */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Processing Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={analytics?.processingOverTime || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="processed" stackId="1" stroke="#3B82F6" fill="#3B82F6" />
              <Area type="monotone" dataKey="queued" stackId="1" stroke="#10B981" fill="#10B981" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Media Type Distribution */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Media Type Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={analytics?.mediaTypeDistribution || []}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {(analytics?.mediaTypeDistribution || []).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Processing Time by Type */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Average Processing Time by Type</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={analytics?.processingTimeByType || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="type" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="avgTime" fill="#3B82F6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* System Metrics */}
      <div className="space-y-6">
        <h3 className="text-lg font-semibold text-gray-900">System Metrics</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {systemCards.map((card, index) => {
            const Icon = card.icon
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
                    <p className="text-sm font-medium text-gray-600">{card.title}</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{card.value}</p>
                  </div>
                  <div className={`p-3 rounded-lg ${colorClasses[card.color as keyof typeof colorClasses]}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Service Status */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Service Status</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(analytics?.serviceStats || {}).map(([service, stats]: [string, any]) => (
            <div key={service} className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900 capitalize">{service}</h4>
                <div className="flex items-center space-x-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm text-gray-600">{stats.uptime}%</span>
                </div>
              </div>
              <div className="space-y-1 text-sm text-gray-600">
                <div className="flex justify-between">
                  <span>Requests:</span>
                  <span>{stats.requests}</span>
                </div>
                <div className="flex justify-between">
                  <span>Avg Response:</span>
                  <span>{stats.avgResponseTime}ms</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
        <div className="space-y-3">
          {[
            { action: 'Processed', file: 'video_sample.mp4', time: '2 minutes ago', status: 'success' },
            { action: 'Failed', file: 'corrupted_file.avi', time: '5 minutes ago', status: 'error' },
            { action: 'Queued', file: 'image_batch.zip', time: '8 minutes ago', status: 'pending' },
            { action: 'Completed', file: 'audio_podcast.wav', time: '12 minutes ago', status: 'success' }
          ].map((activity, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-3">
                <div className={`w-2 h-2 rounded-full ${
                  activity.status === 'success' ? 'bg-green-500' : 
                  activity.status === 'error' ? 'bg-red-500' : 'bg-yellow-500'
                }`}></div>
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

export default Analytics
