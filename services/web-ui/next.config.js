/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://dataflux-ingestion:2013',
    NEXT_PUBLIC_INGESTION_URL: process.env.NEXT_PUBLIC_INGESTION_URL || 'http://dataflux-ingestion:2013',
    NEXT_PUBLIC_QUERY_URL: process.env.NEXT_PUBLIC_QUERY_URL || 'http://dataflux-query:8003',
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://dataflux-ingestion:2013';
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
    domains: ['localhost', 'dataflux.local', 'dataflux-ingestion', 'dataflux-analysis'],
  },
  
  // Webpack-Konfiguration für besseres Logging
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    // Logging für jeden Build-Schritt
    console.log(`🔧 Webpack Build - BuildId: ${buildId}, Dev: ${dev}, IsServer: ${isServer}`);
    
    // Plugin für Build-Progress
    config.plugins.push(
      new webpack.ProgressPlugin((percentage, message, ...args) => {
        console.log(`📊 Build Progress: ${Math.round(percentage * 100)}% - ${message}`, ...args);
      })
    );
    
    return config;
  },
}

module.exports = nextConfig
