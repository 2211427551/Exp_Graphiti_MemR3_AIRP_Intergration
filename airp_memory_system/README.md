# AIRP Memory System

AI Role Play Memory System using Graphiti Temporal Knowledge Graph.

## Overview

The AIRP Memory System is a temporal knowledge graph designed for AI role-play applications. It uses Graphiti to maintain time-aware entity relationships and supports complex memory retrieval and context injection.

## Features

- **Temporal Knowledge Graph**: Track entities and relationships over time
- **Hybrid Search**: Vector + keyword + graph traversal search
- **Memory Injection**: Context-aware memory retrieval for LLMs
- **OpenAI-Compatible API**: Drop-in replacement for chat completions
- **SillyTavern Integration**: Built specifically for SillyTavern workflows

## Tech Stack

- **Knowledge Graph**: Neo4j 5.26 + Graphiti
- **LLM**: DeepSeek V3.2
- **Embedding**: SiliconFlow bge-m3 (1024 dimensions)
- **Reranker**: SiliconFlow bge-reranker-v2-m3
- **API Framework**: FastAPI
- **Cache**: Redis

## Quick Start

### 1. Clone and Setup
```bash
cd /home/user/Exp_Graphiti_MemR3_AIRP_Intergration/airp_memory_system
cp .env.example .env
```

### 2. Configure API Keys
Edit `.env` and add your API keys:
```
DEEPSEEK_API_KEY=your_key_here
SILICONFLOW_API_KEY=your_key_here
```

### 3. Start Services
```bash
docker-compose up -d
```

### 4. Verify
```bash
curl http://localhost:8001/health
```

## Documentation

- [Week 1 Setup Guide](docs/WEEK1_SETUP.md)
- [API Documentation](http://localhost:8001/docs) (after starting)
- [Implementation Plan](../AIRP_记忆系统_详尽实现计划.md)

## Project Status

**Current Progress**: Week 1 Infrastructure Complete ✅

- ✅ FastAPI application framework
- ✅ Configuration management
- ✅ Logging system
- ✅ Docker deployment
- ✅ Neo4j + Redis integration
- ⏳ Graphiti client (Week 2)
- ⏳ Memory ingestion (Week 2)
- ⏳ Content parsing (Week 3-4)
- ⏳ Advanced search (Week 5-6)

## API Endpoints

### Health
- `GET /health` - Health check with component status
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe

### Memory (Coming Soon)
- `POST /api/v1/memory/episodes` - Add episode
- `GET /api/v1/memory/episodes/{id}` - Get episode
- `POST /api/v1/memory/search` - Search memory
- `GET /api/v1/memory/entities/{id}` - Get entity
- `GET /api/v1/memory/entities` - List entities

### Chat (Coming Soon)
- `POST /api/v1/chat/completions` - Chat with memory

## Development

### Requirements
- Python 3.13+
- Docker & Docker Compose

### Setup
```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run Tests
```bash
pytest
```

### Code Quality
```bash
ruff format app/
ruff check app/
mypy app/
```

## Architecture

```
SillyTavern → AIRP Memory API → Graphiti (Neo4j)
                              ↓
                         DeepSeek LLM
                              ↓
                         SiliconFlow Embedding
```

## Contributing

This is part of the 10-week implementation plan. See [AIRP_记忆系统_详尽实现计划.md](../AIRP_记忆系统_详尽实现计划.md) for details.

## License

MIT

## References

- [Graphiti Framework](https://github.com/getzep/graphiti)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/)
- [exp_dsv3_2_json_schema_compatiable](../exp_dsv3_2_json_schema_compatiable/)
