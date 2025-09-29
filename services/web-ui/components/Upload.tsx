import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Upload as UploadIcon,
  FileText,
  Image,
  Video,
  Music,
  X,
  CheckCircle,
  AlertCircle,
  Clock,
  Trash2
} from 'lucide-react'
import { useAppStore } from '../store/appStore'

interface UploadFile {
  id: string
  file: File
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error'
  progress: number
  error?: string
}

const Upload: React.FC = () => {
  const [files, setFiles] = useState<UploadFile[]>([])
  const [dragActive, setDragActive] = useState(false)
  const { setUploadProgress } = useAppStore()

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('context', 'Web UI Upload')
      formData.append('priority', '5')

      const response = await fetch('http://localhost:2013/api/v1/assets', {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      return response.json()
    },
    onSuccess: (data, file) => {
      toast.success(`${file.name} uploaded successfully`)
      setFiles(prev => prev.map(f => 
        f.file === file 
          ? { ...f, status: 'completed', progress: 100 }
          : f
      ))
    },
    onError: (error, file) => {
      toast.error(`Failed to upload ${file.name}`)
      setFiles(prev => prev.map(f => 
        f.file === file 
          ? { ...f, status: 'error', error: error.message }
          : f
      ))
    }
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadFile[] = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      status: 'pending',
      progress: 0
    }))

    setFiles(prev => [...prev, ...newFiles])
    toast.success(`${acceptedFiles.length} file(s) added to upload queue`)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.avi', '.mov', '.mkv', '.webm'],
      'image/*': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
      'audio/*': ['.mp3', '.wav', '.flac', '.ogg', '.aac'],
      'application/pdf': ['.pdf'],
      'text/*': ['.txt', '.md'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    multiple: true,
    maxSize: 100 * 1024 * 1024 // 100MB
  })

  const handleUpload = async (file: UploadFile) => {
    setFiles(prev => prev.map(f => 
      f.id === file.id 
        ? { ...f, status: 'uploading', progress: 0 }
        : f
    ))

    // Simulate progress
    const progressInterval = setInterval(() => {
      setFiles(prev => prev.map(f => {
        if (f.id === file.id && f.status === 'uploading') {
          const newProgress = Math.min(f.progress + 10, 90)
          setUploadProgress(f.id, newProgress)
          return { ...f, progress: newProgress }
        }
        return f
      }))
    }, 200)

    try {
      const result = await uploadMutation.mutateAsync(file.file)
      
      // Set to processing and simulate processing completion
      setFiles(prev => prev.map(f => 
        f.id === file.id 
          ? { ...f, status: 'processing', progress: 95 }
          : f
      ))
      
      // Simulate processing completion after 2 seconds
      setTimeout(() => {
        setFiles(prev => prev.map(f => 
          f.id === file.id 
            ? { ...f, status: 'completed', progress: 100 }
            : f
        ))
        toast.success(`${file.file.name} processing completed`)
      }, 2000)
      
    } catch (error) {
      // Error handled in mutation
    } finally {
      clearInterval(progressInterval)
    }
  }

  const removeFile = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }

  const getFileIcon = (file: File) => {
    if (file.type.startsWith('video/')) return Video
    if (file.type.startsWith('image/')) return Image
    if (file.type.startsWith('audio/')) return Music
    return FileText
  }

  const getStatusIcon = (status: UploadFile['status']) => {
    switch (status) {
      case 'completed': return CheckCircle
      case 'error': return AlertCircle
      case 'uploading':
      case 'processing': return Clock
      default: return null
    }
  }

  const getStatusColor = (status: UploadFile['status']) => {
    switch (status) {
      case 'completed': return 'text-green-600'
      case 'error': return 'text-red-600'
      case 'uploading':
      case 'processing': return 'text-blue-600'
      default: return 'text-gray-600'
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Upload Media</h2>
        <p className="text-gray-600 mt-1">Upload and process your media files</p>
      </div>

      {/* Upload Area */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragActive 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
        `}
      >
        <input {...getInputProps()} />
        <UploadIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
        </h3>
        <p className="text-gray-600 mb-4">
          or click to select files
        </p>
        <div className="text-sm text-gray-500">
          <p>Supported formats: MP4, AVI, MOV, JPG, PNG, MP3, WAV, PDF, DOC</p>
          <p>Maximum file size: 100MB</p>
        </div>
      </div>

      {/* Upload Queue */}
      {files.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Upload Queue</h3>
            <div className="text-sm text-gray-500">
              {files.length} file(s) in queue
            </div>
          </div>

          <div className="space-y-3">
            {files.map((file) => {
              const FileIcon = getFileIcon(file.file)
              const StatusIcon = getStatusIcon(file.status)

              return (
                <div key={file.id} className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
                  <FileIcon className="w-8 h-8 text-gray-600" />
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {file.file.name}
                      </p>
                      <div className="flex items-center space-x-2">
                        {StatusIcon && (
                          <StatusIcon className={`w-4 h-4 ${getStatusColor(file.status)}`} />
                        )}
                        <span className={`text-sm font-medium ${getStatusColor(file.status)}`}>
                          {file.status}
                        </span>
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between mt-1">
                      <p className="text-xs text-gray-500">
                        {formatFileSize(file.file.size)}
                      </p>
                      <div className="flex items-center space-x-2">
                        {file.status === 'pending' && (
                          <button
                            onClick={() => handleUpload(file)}
                            className="px-3 py-1 bg-blue-600 text-white text-xs rounded-md hover:bg-blue-700 transition-colors"
                          >
                            Upload
                          </button>
                        )}
                        <button
                          onClick={() => removeFile(file.id)}
                          className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    {(file.status === 'uploading' || file.status === 'processing') && (
                      <div className="mt-2">
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${file.progress}%` }}
                          ></div>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {file.progress}% complete
                        </p>
                      </div>
                    )}

                    {/* Error Message */}
                    {file.status === 'error' && file.error && (
                      <p className="text-xs text-red-600 mt-1">
                        {file.error}
                      </p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Batch Actions */}
          <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-200">
            <div className="text-sm text-gray-500">
              {files.filter(f => f.status === 'completed').length} completed,{' '}
              {files.filter(f => f.status === 'error').length} failed
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => {
                  files.filter(f => f.status === 'pending').forEach(handleUpload)
                }}
                disabled={files.filter(f => f.status === 'pending').length === 0}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Upload All
              </button>
              <button
                onClick={() => setFiles([])}
                className="px-4 py-2 bg-gray-600 text-white text-sm rounded-md hover:bg-gray-700 transition-colors"
              >
                Clear All
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Tips */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-blue-900 mb-2">Upload Tips</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Large files will be processed in the background</li>
          <li>• You can upload multiple files at once</li>
          <li>• Processing time depends on file size and type</li>
          <li>• Check the Analytics page for processing statistics</li>
        </ul>
      </div>
    </div>
  )
}

export default Upload
