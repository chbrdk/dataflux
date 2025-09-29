import type { NextPage } from 'next'
import Head from 'next/head'
import { useState, useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import Layout from '../components/Layout'
import Dashboard from '../components/Dashboard'
import Upload from '../components/Upload'
import Search from '../components/Search'
import Assets from '../components/Assets'
import Analytics from '../components/Analytics'
import { useAppStore } from '../store/appStore'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    },
  },
})

const Home: NextPage = () => {
  const [mounted, setMounted] = useState(false)
  const { currentView, setCurrentView } = useAppStore()

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return null
  }

  const renderContent = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard />
      case 'upload':
        return <Upload />
      case 'search':
        return <Search />
      case 'assets':
        return <Assets />
      case 'analytics':
        return <Analytics />
      default:
        return <Dashboard />
    }
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Head>
        <title>DataFlux - AI Media Database</title>
        <meta name="description" content="Universal AI-native database for media content" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <Layout>
        {renderContent()}
      </Layout>

      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
        }}
      />
    </QueryClientProvider>
  )
}

export default Home
