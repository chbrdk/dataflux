#!/bin/bash

# Stoppe alte Prozesse
pkill -9 -f "main_simple.py"
pkill -9 -f "api_processor.py"
sleep 2

# Logs leeren
rm -f /tmp/dataflux-*.log

# Ingestion Service starten
echo "🚀 Starte Ingestion Service..."
cd /Users/m4mini/Desktop/DOCKER-local/DATAFLUX/services/ingestion-service
python3 src/main_simple.py > /tmp/dataflux-ingestion.log 2>&1 &
INGESTION_PID=$!
echo "✅ Ingestion Service gestartet (PID: $INGESTION_PID)"

sleep 3

# Analysis Service starten
echo "🚀 Starte Analysis Service..."
cd /Users/m4mini/Desktop/DOCKER-local/DATAFLUX/services/analysis-service
python3 src/api_processor.py > /tmp/dataflux-analysis.log 2>&1 &
ANALYSIS_PID=$!
echo "✅ Analysis Service gestartet (PID: $ANALYSIS_PID)"

sleep 2

echo ""
echo "📊 Services Status:"
echo "   Ingestion: http://localhost:2013 (PID: $INGESTION_PID)"
echo "   Analysis:  Läuft (PID: $ANALYSIS_PID)"
echo ""
echo "📝 Logs:"
echo "   tail -f /tmp/dataflux-ingestion.log"
echo "   tail -f /tmp/dataflux-analysis.log"

