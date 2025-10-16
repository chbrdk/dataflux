import React, { useState, useEffect } from 'react'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { User, Users, Eye, Calendar, Image as ImageIcon, ArrowLeft, Search } from 'lucide-react'
import Link from 'next/link'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
    },
  },
})

interface Person {
  face_id: string
  identity: string
  avatar_base64: string
  appearance_count: number
  first_seen: string
  last_seen: string
  confidence: number
}

interface PersonImage {
  asset_id: string
  filename: string
  uploaded_at: string
  confidence: number
  face_quality: string
}

const PersonsPageContent: React.FC = () => {
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null)
  const [personImages, setPersonImages] = useState<PersonImage[]>([])
  const [loading, setLoading] = useState(false)

  // Fetch all persons from the face database
  const { data: persons, isLoading: personsLoading, error: personsError } = useQuery({
    queryKey: ['persons'],
    queryFn: async () => {
      const response = await fetch('http://localhost:2013/api/v1/persons')
      if (!response.ok) {
        throw new Error('Failed to fetch persons')
      }
      return response.json()
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Fetch images for a specific person
  const fetchPersonImages = async (faceId: string) => {
    setLoading(true)
    try {
      const response = await fetch(`http://localhost:2013/api/v1/persons/${faceId}/images`)
      if (!response.ok) {
        throw new Error('Failed to fetch person images')
      }
      const data = await response.json()
      setPersonImages(data.images || [])
    } catch (error) {
      console.error('Error fetching person images:', error)
      setPersonImages([])
    } finally {
      setLoading(false)
    }
  }

  const handlePersonClick = (person: Person) => {
    setSelectedPerson(person)
    fetchPersonImages(person.face_id)
  }

  const formatDate = (timestamp: string) => {
    try {
      const date = new Date(parseFloat(timestamp) * 1000)
      return date.toLocaleDateString('de-DE', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return 'Unbekannt'
    }
  }

  if (personsLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Lade Personen...</p>
        </div>
      </div>
    )
  }

  if (personsError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Fehler beim Laden der Personen</h2>
          <p className="text-gray-600 mb-4">Die Personen-Daten konnten nicht geladen werden.</p>
          <Link href="/" className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Zurück zur Startseite
          </Link>
        </div>
      </div>
    )
  }

  if (selectedPerson) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <button
              onClick={() => setSelectedPerson(null)}
              className="inline-flex items-center text-blue-600 hover:text-blue-800 mb-4"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Zurück zu allen Personen
            </button>
            
            <div className="flex items-center space-x-4">
              {selectedPerson.avatar_base64 ? (
                <img 
                  src={selectedPerson.avatar_base64} 
                  alt={`Avatar von ${selectedPerson.identity}`}
                  className="w-20 h-20 rounded-full object-cover border-4 border-blue-300"
                />
              ) : (
                <div className="w-20 h-20 rounded-full bg-blue-100 border-4 border-blue-300 flex items-center justify-center">
                  <User className="w-10 h-10 text-blue-600" />
                </div>
              )}
              
              <div>
                <h1 className="text-3xl font-bold text-gray-900">{selectedPerson.identity}</h1>
                <div className="flex items-center space-x-4 text-sm text-gray-600 mt-2">
                  <span className="flex items-center">
                    <Eye className="w-4 h-4 mr-1" />
                    {selectedPerson.appearance_count} Auftritte
                  </span>
                  <span className="flex items-center">
                    <Calendar className="w-4 h-4 mr-1" />
                    Erste Sichtung: {formatDate(selectedPerson.first_seen)}
                  </span>
                  <span className="flex items-center">
                    <Calendar className="w-4 h-4 mr-1" />
                    Letzte Sichtung: {formatDate(selectedPerson.last_seen)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Images Grid */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
              <ImageIcon className="w-5 h-5 mr-2" />
              Bilder mit dieser Person ({personImages.length})
            </h2>
            
            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Lade Bilder...</p>
              </div>
            ) : personImages.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <ImageIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>Keine Bilder mit dieser Person gefunden.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {personImages.map((image) => (
                  <div key={image.asset_id} className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:shadow-md transition-shadow">
                    <div className="aspect-square bg-gray-200 rounded-lg mb-3 flex items-center justify-center">
                      <ImageIcon className="w-8 h-8 text-gray-400" />
                    </div>
                    <div className="text-sm">
                      <p className="font-medium text-gray-900 truncate">{image.filename}</p>
                      <p className="text-gray-600 text-xs mt-1">
                        Qualität: {image.face_quality}
                      </p>
                      <p className="text-gray-600 text-xs">
                        Confidence: {Math.round(image.confidence * 100)}%
                      </p>
                      <p className="text-gray-600 text-xs">
                        {formatDate(image.uploaded_at)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center">
                <Users className="w-8 h-8 mr-3" />
                Personen
              </h1>
              <p className="text-gray-600 mt-2">
                Alle erkannten Personen mit ihren Avatars und Auftrittsstatistiken
              </p>
            </div>
            <Link href="/" className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Zurück zur Startseite
            </Link>
          </div>
        </div>

        {/* Persons Grid */}
        {persons && persons.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {persons.map((person: Person) => (
              <div
                key={person.face_id}
                onClick={() => handlePersonClick(person)}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md hover:border-blue-300 transition-all cursor-pointer group"
              >
                <div className="text-center">
                  {person.avatar_base64 ? (
                    <img 
                      src={person.avatar_base64} 
                      alt={`Avatar von ${person.identity}`}
                      className="w-20 h-20 rounded-full object-cover border-4 border-gray-200 group-hover:border-blue-300 mx-auto mb-4 transition-colors"
                    />
                  ) : (
                    <div className="w-20 h-20 rounded-full bg-gray-100 border-4 border-gray-200 group-hover:border-blue-300 flex items-center justify-center mx-auto mb-4 transition-colors">
                      <User className="w-10 h-10 text-gray-400" />
                    </div>
                  )}
                  
                  <h3 className="font-semibold text-gray-900 mb-2 truncate">{person.identity}</h3>
                  
                  <div className="space-y-2 text-sm text-gray-600">
                    <div className="flex items-center justify-center">
                      <Eye className="w-4 h-4 mr-1" />
                      <span>{person.appearance_count} Auftritte</span>
                    </div>
                    
                    <div className="flex items-center justify-center">
                      <Calendar className="w-4 h-4 mr-1" />
                      <span className="text-xs">
                        {formatDate(person.first_seen)}
                      </span>
                    </div>
                    
                    <div className="flex items-center justify-center">
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                        {Math.round(person.confidence * 100)}% Confidence
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Keine Personen gefunden</h3>
            <p className="text-gray-600 mb-4">
              Es wurden noch keine Personen erkannt. Lade Bilder mit Gesichtern hoch, um Personen zu erkennen.
            </p>
            <Link href="/" className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Zurück zur Startseite
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}

const PersonsPage: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <PersonsPageContent />
    </QueryClientProvider>
  )
}

export default PersonsPage
