#!/bin/bash

# DATAFLUX - Lokales Start-Script für Mac Mini M4
echo "🚀 Starting DATAFLUX locally on Mac Mini M4..."

# Farben
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Starte Docker Container (nur PostgreSQL und Redis)
echo -e "${BLUE}📦 Starting Docker containers...${NC}"
docker start dataflux-postgres dataflux-redis 2>/dev/null || echo "Containers already running"
sleep 3

# 2. Starte Ingestion Service
echo -e "${BLUE}📥 Starting Ingestion Service (Port 2013)...${NC}"
cd /Users/m4mini/Desktop/DOCKER-local/DATAFLUX/services/ingestion-service
DATABASE_URL="postgresql://dataflux_user:secure_password_here@localhost:2001/dataflux" \
REDIS_URL="redis://:secure_redis_password_here@localhost:2002" \
python3 src/main_simple.py > /tmp/ingestion_service.log 2>&1 &
echo -e "${GREEN}✅ Ingestion Service started${NC}"

# 3. Starte Analysis Service mit YOLO + FaceNet + Docling
echo -e "${BLUE}🧠 Starting Analysis Service (Port 2014)...${NC}"
cd /Users/m4mini/Desktop/DOCKER-local/DATAFLUX/services/analysis-service
DATABASE_URL="postgresql://dataflux_user:secure_password_here@localhost:2001/dataflux" \
CLAUDE_API_KEY="YOUR_CLAUDE_API_KEY_HERE" \
INGESTION_SERVICE_URL="http://localhost:2013" \
PYTHONPATH=/Users/m4mini/Desktop/DOCKER-local/DATAFLUX/services/analysis-service \
python3 src/api_processor.py > /tmp/analysis_service.log 2>&1 &
echo -e "${GREEN}✅ Analysis Service started (YOLO + DeepFace + FaceNet + Docling on M4 GPU)${NC}"

# 4. Starte Query Service
echo -e "${BLUE}🔍 Starting Query Service (Port 8003)...${NC}"
cd /Users/m4mini/Desktop/DOCKER-local/DATAFLUX/services/query-service
INGESTION_SERVICE_URL="http://localhost:2013" \
go run cmd/main_simple.go > /tmp/query_service.log 2>&1 &
echo -e "${GREEN}✅ Query Service started${NC}"

# 5. Starte Claude Vision Service
echo -e "${BLUE}🤖 Starting Claude Vision Service (Port 2015)...${NC}"
cd /Users/m4mini/Desktop/DOCKER-local/DATAFLUX/services/analysis-service
python3 src/claude_service.py > /tmp/claude_service.log 2>&1 &
echo -e "${GREEN}✅ Claude Vision Service started${NC}"

# 6. Starte Web-UI
echo -e "${BLUE}🌐 Starting Web-UI (Port 3000)...${NC}"
cd /Users/m4mini/Desktop/DOCKER-local/DATAFLUX/services/web-ui
npm run dev > /tmp/webui.log 2>&1 &
echo -e "${GREEN}✅ Web-UI started${NC}"

# Warte auf Services
echo ""
echo -e "${BLUE}⏳ Waiting for services to start...${NC}"
sleep 8

# Zeige Status
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}🎉 DATAFLUX is running!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Services:"
echo "  • Web-UI:          http://localhost:3000"
echo "  • Ingestion API:   http://localhost:2013"
echo "  • Query API:       http://localhost:8003"
echo "  • Analysis:        Running (YOLO + FaceNet)"
echo "  • Claude Vision:   http://localhost:2015"
echo ""
echo "🗄️  Databases:"
echo "  • PostgreSQL:      localhost:2001"
echo "  • Redis:           localhost:2002"
echo ""
echo "📝 Logs:"
echo "  • Ingestion:       tail -f /tmp/ingestion_service.log"
echo "  • Analysis:        tail -f /tmp/analysis_service.log"
echo "  • Query:           tail -f /tmp/query_service.log"
echo "  • Claude Vision:   tail -f /tmp/claude_service.log"
echo "  • Web-UI:          tail -f /tmp/webui.log"
echo ""
echo "🛑 To stop: ./stop-local.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
