/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:2013',
    NEXT_PUBLIC_INGESTION_URL: process.env.NEXT_PUBLIC_INGESTION_URL || 'http://localhost:2013',
    NEXT_PUBLIC_QUERY_URL: process.env.NEXT_PUBLIC_QUERY_URL || 'http://localhost:8003',
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:2013';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${apiUrl}/api/v1/:path*`,
      },
      {
        source: '/health',
        destination: `${apiUrl}/health`,
      },
    ]
  },
  images: {
    domains: ['localhost', 'dataflux.local'],
  },
}

module.exports = nextConfig
