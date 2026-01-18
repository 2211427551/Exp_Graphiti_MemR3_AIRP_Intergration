# Week 1 Setup Guide

## Overview
This guide covers setting up the AIRP Memory System infrastructure.

## Prerequisites
- Python 3.13+
- Docker & Docker Compose
- DeepSeek API key
- SiliconFlow API key

## Setup Steps

### 1. Create Project Structure
```bash
cd /home/user/Exp_Graphiti_MemR3_AIRP_Intergration
mkdir -p airp_memory_system
cd airp_memory_system
```

### 2. Create Environment File
```bash
cp .env.example .env
# Edit .env with your API keys
nano .env
```

Required environment variables:
- `DEEPSEEK_API_KEY`: Your DeepSeek API key
- `SILICONFLOW_API_KEY`: Your SiliconFlow API key

### 3. Start Services
```bash
docker-compose up -d
```

This will start:
- Neo4j (ports 7474, 7687)
- Redis (port 6379)
- AIRP Memory API (port 8001)

### 4. Check Service Status
```bash
docker-compose ps
```

All services should show as "healthy".

### 5. View Logs
```bash
docker-compose logs -f api
```

### 6. Verify Installation

#### Test Health Endpoint
```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "app_name": "AIRP Memory System",
  "version": "1.0.0",
  "components": {
    "api": "healthy",
    "neo4j": "not_implemented",
    "redis": "not_implemented",
    "deepseek": "not_implemented",
    "siliconflow": "not_implemented"
  }
}
```

#### Test Root Endpoint
```bash
curl http://localhost:8001/
```

#### Access API Documentation
Open in browser: http://localhost:8001/docs

### 7. Initialize Neo4j (Week 2)
```bash
python scripts/init_neo4j.py
```

### 8. Access Neo4j Browser
Open in browser: http://localhost:7474
- Username: `neo4j`
- Password: `neo4j_password`

## Troubleshooting

### Neo4j Connection Issues
```bash
# Check Neo4j logs
docker-compose logs neo4j

# Verify Neo4j is running
docker-compose ps neo4j

# Test connection
curl http://localhost:7474
```

### API Issues
```bash
# Check API logs
docker-compose logs api

# Verify environment variables
docker-compose config

# Check container status
docker-compose ps api
```

### Port Already in Use
```bash
# Check what's using the port
lsof -i :8001
lsof -i :7474
lsof -i :7687
lsof -i :6379

# Change ports in docker-compose.yml if needed
```

### Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
```

## Development Setup

### Local Development (without Docker)
```bash
# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set environment variables
export $(cat .env | xargs)

# Run application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Running Tests
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### Code Quality
```bash
# Format code
ruff format app/

# Lint code
ruff check app/

# Type checking
mypy app/
```

## Next Steps

After completing Week 1 setup:
1. ✅ Verify all services are running
2. ✅ Test API endpoints
3. ✅ Access API documentation
4. ✅ Check Neo4j browser

Week 2 will implement:
- Graphiti client integration
- Episode ingestion
- Memory search
- Entity extraction

## Useful Commands

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild containers
docker-compose build --no-cache

# View resource usage
docker stats

# Execute commands in container
docker-compose exec api bash
docker-compose exec neo4j cypher-shell -u neo4j -p neo4j_password
```

## Configuration Reference

### Environment Variables
See `.env.example` for all available configuration options.

### API Endpoints
- `GET /health` - Health check
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /docs` - API documentation (Swagger UI)
- `GET /redoc` - API documentation (ReDoc)
- `GET /` - Root endpoint with API info

### Service Ports
- API: 8001
- Neo4j HTTP: 7474
- Neo4j Bolt: 7687
- Redis: 6379
