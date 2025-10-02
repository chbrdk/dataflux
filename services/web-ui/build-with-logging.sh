#!/bin/bash

echo "🚀 Starting Next.js Build with Detailed Logging..."
echo "📅 $(date)"
echo "📁 Working Directory: $(pwd)"
echo "🔍 Node Version: $(node --version)"
echo "🔍 NPM Version: $(npm --version)"
echo ""

# Setze detaillierte Logging-Umgebungsvariablen
export DEBUG=*
export NODE_OPTIONS="--max-old-space-size=4096"
export NEXT_TELEMETRY_DISABLED=1

echo "🔧 Environment Variables Set:"
echo "  - DEBUG=*"
echo "  - NODE_OPTIONS=--max-old-space-size=4096"
echo "  - NEXT_TELEMETRY_DISABLED=1"
echo ""

# Prüfe ob node_modules existiert
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install --verbose
    echo "✅ Dependencies installed"
else
    echo "✅ node_modules exists"
fi

echo ""
echo "🧹 Cleaning previous build..."
rm -rf .next
echo "✅ Previous build cleaned"

echo ""
echo "🔨 Starting Next.js build with verbose logging..."
echo "⏰ Start time: $(date)"

# Starte Build mit detailliertem Logging
npm run build 2>&1 | tee /tmp/nextjs-build.log

echo ""
echo "⏰ End time: $(date)"
echo "✅ Build completed"

# Zeige Build-Ergebnisse
echo ""
echo "📊 Build Results:"
if [ -d ".next" ]; then
    echo "✅ .next directory created"
    echo "📁 .next contents:"
    ls -la .next/
else
    echo "❌ .next directory not found"
fi

echo ""
echo "📋 Build log saved to: /tmp/nextjs-build.log"
echo "🔍 Last 20 lines of build log:"
tail -20 /tmp/nextjs-build.log
