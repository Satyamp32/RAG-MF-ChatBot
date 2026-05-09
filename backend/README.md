# Mutual Fund RAG ChatBot Backend

FastAPI backend for the Mutual Fund RAG ChatBot with modular architecture, retrieval + generation integration, and comprehensive API endpoints.

## Features

- **Hybrid Retrieval**: Dense vector search + Sparse BM25 search with cross-encoder reranking
- **Groq LLM Integration**: OpenAI-compatible API with llama3-70b-8192 model
- **Guardrails**: PII protection, hallucination prevention, and safety filtering
- **Modular Architecture**: Clean separation of concerns with service layer
- **Comprehensive API**: Chat, health, metrics, and metadata endpoints
- **Error Handling**: Centralized error handling with structured responses
- **Logging**: Structured logging with request tracking and performance metrics
- **Security**: CORS, rate limiting, and security headers
- **Configuration**: Environment-based configuration management

## Quick Start

### Prerequisites

- Python 3.9+
- FastAPI and dependencies (see requirements.txt)
- ChromaDB for vector storage
- Groq API key (optional, for LLM generation)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start the server:
```bash
python -m backend.main
```

The API will be available at `http://localhost:8000`

### API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## API Endpoints

### Chat Endpoint

**POST** `/chat`

Process user queries about mutual funds and return factual answers with source attribution.

**Request Body:**
```json
{
  "query": "What is the expense ratio of HDFC Equity Fund?",
  "use_groq": "auto",
  "top_k": 10,
  "scheme_filter": null,
  "section_filter": null,
  "include_metadata": false
}
```

**Response:**
```json
{
  "status": "success",
  "answer": "The expense ratio of HDFC Equity Fund is 1.11% per annum.",
  "source": "https://groww.in/mutual-funds/hdfc-equity-fund",
  "last_updated": "2024-01-01",
  "confidence": 0.85,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Health Endpoint

**GET** `/health`

Check the health status of the application and its components.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "components": {
    "retrieval": {"status": "healthy"},
    "generation": {"status": "healthy"}
  }
}
```

### Metadata Endpoint

**GET** `/meta`

Get API information including available endpoints and features.

### Metrics Endpoint

**GET** `/metrics`

Get application metrics including request counts and performance data.

## Configuration

### Environment Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Groq LLM Configuration
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama3-70b-8192
GROQ_TEMPERATURE=0.1
GROQ_MAX_TOKENS=500

# Retrieval Configuration
DENSE_WEIGHT=0.4
SPARSE_WEIGHT=0.6
TOP_K=10
ENABLE_RERANKING=true

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/backend.log
```

## Architecture

### Components

1. **FastAPI Application** (`main.py`): Main application with endpoints and middleware
2. **Services** (`services.py`): Business logic for retrieval and generation
3. **Schemas** (`schemas.py`): Pydantic models for request/response validation
4. **Middleware** (`middleware.py`): Custom middleware for logging, CORS, rate limiting
5. **Configuration** (`config.py`): Environment-based configuration management
6. **Logger** (`logger.py`): Structured logging configuration

### Service Layer

- **RetrievalService**: Handles query processing and chunk retrieval
- **GenerationService**: Handles response generation with LLM integration
- **ChatService**: Orchestrates the complete chat workflow

### Middleware Stack

1. **CORS Middleware**: Cross-origin request handling
2. **Security Middleware**: Security headers and validation
3. **Metrics Middleware**: Request metrics collection
4. **Rate Limiting**: Request rate limiting
5. **Error Handling**: Centralized error handling
6. **Request Logging**: Request/response logging

## Testing

### Run API Tests

```bash
python backend/sample_requests.py
```

### Manual Testing

Use the provided curl commands:

```bash
# Health check
curl -X GET http://localhost:8000/health

# Chat request
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the expense ratio of HDFC Equity Fund?",
    "use_groq": "false",
    "top_k": 5
  }'
```

## Development

### Running in Development Mode

```bash
python -m backend.main
```

### Code Structure

```
backend/
├── __init__.py          # Package initialization
├── main.py              # FastAPI application
├── config.py            # Configuration management
├── schemas.py           # Pydantic models
├── services.py          # Business logic services
├── middleware.py        # Custom middleware
├── logger.py            # Logging configuration
├── sample_requests.py   # API test suite
└── README.md            # This file
```

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "-m", "backend.main"]
```

### Environment Setup

1. Set environment variables in production
2. Configure CORS origins for production domains
3. Set up proper logging and monitoring
4. Configure rate limiting for production traffic

## Monitoring

### Health Checks

- Application health: `/health`
- Component health: Included in health endpoint response
- Service dependencies: Checked during startup

### Metrics

- Request counts and response times
- Error rates and types
- Component health status
- Resource usage

### Logging

- Structured JSON logging for file output
- Colored console logging for development
- Request tracking with unique IDs
- Performance metrics

## Security

### Features

- CORS configuration
- Security headers
- Rate limiting
- Input validation
- PII detection and filtering
- Request size limits

### Best Practices

- Use HTTPS in production
- Configure proper CORS origins
- Monitor for abuse and attacks
- Keep dependencies updated
- Use environment variables for secrets

## Troubleshooting

### Common Issues

1. **Service Initialization Failed**
   - Check ChromaDB connection
   - Verify configuration settings
   - Check log files for detailed errors

2. **Groq API Errors**
   - Verify API key is valid
   - Check network connectivity
   - Monitor API rate limits

3. **Retrieval Issues**
   - Check vector store health
   - Verify chunk data exists
   - Check embedding model availability

### Debug Mode

Enable debug mode for detailed error information:

```bash
API_DEBUG=true python -m backend.main
```

## Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Use proper logging and error handling
5. Follow security best practices
