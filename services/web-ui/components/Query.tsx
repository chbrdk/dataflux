import React, { useState, useRef, useEffect } from 'react'
import { useAppStore } from '../store/appStore'
import { Send, Bot, User, Image as ImageIcon, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

interface Asset {
  id: string
  filename: string
  thumbnail_url: string
  description?: string
  confidence?: number
  relevance_score?: number
}

interface SearchResponse {
  assets: Asset[]
  summary: string
  search_metadata: any
}

const Query: React.FC = () => {
  const { chatHistory, addChatMessage, clearChatHistory } = useAppStore()
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [chatHistory])

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    const userMessage = inputValue.trim()
    setInputValue('')
    setIsLoading(true)

    // Add user message to chat history
    addChatMessage({
      role: 'user',
      content: userMessage
    })

    try {
      // Call search service
      const response = await fetch('http://localhost:2016/api/v1/search/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userMessage,
          limit: 10
        })
      })

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
      }

      const searchResult: SearchResponse = await response.json()

      // Add assistant response to chat history
      addChatMessage({
        role: 'assistant',
        content: searchResult.summary,
        assets: searchResult.assets
      })

    } catch (error) {
      console.error('Search error:', error)
      toast.error('Suche fehlgeschlagen. Bitte versuchen Sie es erneut.')
      
      // Add error message to chat history
      addChatMessage({
        role: 'assistant',
        content: 'Entschuldigung, bei der Suche ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut.'
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleClearChat = () => {
    clearChatHistory()
    toast.success('Chat-Verlauf gelöscht')
  }

  return (
    <div className="flex flex-col h-full max-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">AI Query</h1>
          <p className="text-sm text-gray-600">Natürlichsprachliche Suche in Ihren Medien</p>
        </div>
        <button
          onClick={handleClearChat}
          className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors"
        >
          Chat löschen
        </button>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {chatHistory.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Bot className="w-16 h-16 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Willkommen bei AI Query
            </h3>
            <p className="text-gray-600 mb-4 max-w-md">
              Stellen Sie Fragen in natürlicher Sprache, um Ihre Medien zu durchsuchen.
              Zum Beispiel: "Zeige mir alle Bilder mit Personen am Strand"
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                "Bilder mit Autos"
              </span>
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                "Personen im Freien"
              </span>
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                "Rote Objekte"
              </span>
            </div>
          </div>
        ) : (
          chatHistory.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl flex ${
                  message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                } items-start space-x-3`}
              >
                {/* Avatar */}
                <div
                  className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-600 text-white'
                  }`}
                >
                  {message.role === 'user' ? (
                    <User className="w-4 h-4" />
                  ) : (
                    <Bot className="w-4 h-4" />
                  )}
                </div>

                {/* Message Content */}
                <div
                  className={`px-4 py-3 rounded-lg ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-900 border border-gray-200'
                  }`}
                >
                  <p className="text-sm">{message.content}</p>
                  
                  {/* Assets Grid */}
                  {message.assets && message.assets.length > 0 && (
                    <div className="mt-3 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                      {message.assets.map((asset) => (
                        <div
                          key={asset.id}
                          className="bg-gray-100 rounded-lg overflow-hidden hover:bg-gray-200 transition-colors cursor-pointer"
                          onClick={() => {
                            // Open asset in new tab or modal
                            window.open(`/api/v1/assets/${asset.id}`, '_blank')
                          }}
                        >
                          <div className="aspect-square bg-gray-200 flex items-center justify-center">
                            {asset.thumbnail_url ? (
                              <img
                                src={asset.thumbnail_url}
                                alt={asset.filename}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  const target = e.target as HTMLImageElement
                                  target.style.display = 'none'
                                  target.nextElementSibling?.classList.remove('hidden')
                                }}
                              />
                            ) : null}
                            <div className="hidden w-full h-full flex items-center justify-center text-gray-500">
                              <ImageIcon className="w-8 h-8" />
                            </div>
                          </div>
                          <div className="p-2">
                            <p className="text-xs font-medium text-gray-900 truncate">
                              {asset.filename}
                            </p>
                            {asset.description && (
                              <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                                {asset.description}
                              </p>
                            )}
                            {asset.relevance_score && (
                              <div className="mt-1">
                                <div className="w-full bg-gray-200 rounded-full h-1">
                                  <div
                                    className="bg-blue-600 h-1 rounded-full"
                                    style={{ width: `${asset.relevance_score * 100}%` }}
                                  />
                                </div>
                                <p className="text-xs text-gray-500 mt-1">
                                  {Math.round(asset.relevance_score * 100)}% Relevanz
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="max-w-3xl flex items-start space-x-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-600 text-white flex items-center justify-center">
                <Bot className="w-4 h-4" />
              </div>
              <div className="px-4 py-3 rounded-lg bg-white text-gray-900 border border-gray-200">
                <div className="flex items-center space-x-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Suche läuft...</span>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-200 bg-white">
        <div className="flex items-end space-x-3">
          <div className="flex-1">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Stellen Sie eine Frage in natürlicher Sprache..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={1}
              style={{ minHeight: '40px', maxHeight: '120px' }}
              disabled={isLoading}
            />
          </div>
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span>Senden</span>
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Drücken Sie Enter zum Senden, Shift+Enter für neue Zeile
        </p>
      </div>
    </div>
  )
}

export default Query
