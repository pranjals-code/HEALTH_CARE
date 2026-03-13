#!/bin/bash
# Healthcare System - OTP/SMS Authentication Setup & Run Guide

echo "=================================="
echo "🏥 Healthcare System - Setup Guide"
echo "=================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check prerequisites
echo -e "\n${BLUE}Step 1: Checking Prerequisites${NC}"
echo "=================================="

# Check Python
if command -v python3 &> /dev/null; then
    echo "✅ Python 3: $(python3 --version)"
else
    echo "❌ Python 3 not found. Please install Python 3.9+"
    exit 1
fi

# Check PostgreSQL
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL: $(psql --version)"
else
    echo "⚠️  PostgreSQL not found. Please install PostgreSQL and make sure 'psql' is available."
fi

# Step 2: Install dependencies
echo -e "\n${BLUE}Step 2: Installing Python Dependencies${NC}"
echo "=================================="
pip install -r requirements.txt

# Step 3: Database setup
echo -e "\n${BLUE}Step 3: Database Setup${NC}"
echo "=================================="
echo "Creating database..."
psql -U postgres -c "CREATE DATABASE health_care;" 2>/dev/null || echo "⚠️  Database may already exist"

echo "Running migrations..."
cd backend
alembic upgrade head

# Step 4: Test setup
echo -e "\n${BLUE}Step 4: Seeding Roles & Permissions${NC}"
echo "=================================="
python test_setup.py

# Step 5: Final instructions
echo -e "\n${GREEN}✅ Setup Complete!${NC}"
echo "=================================="
echo -e "\n${YELLOW}To run the application:${NC}"
echo ""
echo "Terminal 1: Start Redis"
echo "  redis-server"
echo ""
echo "Terminal 2: Start Celery worker"
echo "  cd backend"
echo "  celery -A app.celery_app worker --loglevel=info"
echo ""
echo "Terminal 3: Start FastAPI"
echo "  cd backend"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Terminal 4: Run OTP Tests"
echo "  cd backend"
echo "  python test_otp_flow.py"
echo ""
echo -e "${YELLOW}API Documentation:${NC}"
echo "  📚 Swagger UI: http://localhost:8000/api/docs"
echo "  📖 ReDoc: http://localhost:8000/api/redoc"
echo ""
echo -e "${YELLOW}Key Environment Variables:${NC}"
echo "  - REDIS_URL: redis://localhost:6379/0"
echo "  - TWILIO_ACCOUNT_SID: Set in .env"
echo "  - TWILIO_AUTH_TOKEN: Set in .env"
echo "  - TWILIO_PHONE_NUMBER: Set in .env"
echo ""
