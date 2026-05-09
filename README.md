# Mutual Fund FAQ Assistant - Production Grade RAG System

A facts-only, source-cited RAG-based Q&A assistant for mutual fund schemes. Built with enterprise-grade architecture and comprehensive edge case handling.

## 🎯 Project Overview

This system provides factual information about HDFC mutual fund schemes using only approved Groww URLs as sources. It follows strict governance rules to ensure accuracy, privacy, and compliance.

## 🏗️ Architecture

The system is built in 6 phases, each independently runnable and testable:

- **Phase 0**: Foundation & Governance (✅)
- **Phase 1**: Ingestion & Corpus Build
- **Phase 2**: Retrieval Layer
- **Phase 3**: Reasoning & Guardrails
- **Phase 4**: User Interface
- **Phase 5**: Evaluation & Compliance

## 📁 Project Structure

```
MutualFund-RAG-ChatBot/
├── configs/                 # Configuration files
│   ├── sources.yaml         # Approved sources registry
│   ├── refusal_intents.yaml # Refusal patterns
│   ├── disclaimer.txt       # Disclaimer text
│   └── app_config.yaml     # Application config
├── src/                    # Source code
│   ├── utils/              # Utility functions
│   ├── ingestion/          # Data ingestion pipeline
│   ├── retrieval/          # Retrieval layer
│   ├── generation/         # Answer generation
│   ├── backend/            # FastAPI backend
│   └── frontend/           # React frontend
├── data/                   # Data storage
│   ├── raw/               # Raw fetched data
│   ├── processed/          # Processed data
│   └── vectorstore/        # ChromaDB storage
├── tests/                  # Test suites
├── scripts/                # Utility scripts
├── docs/                   # Documentation
└── logs/                   # Application logs
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 16+ (for frontend)
- Docker (optional, for deployment)

### Installation

1. **Clone and setup environment:**
```bash
git clone <repository-url>
cd MutualFund-RAG-ChatBot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

3. **Run Phase 0 setup:**
```bash
python -m src.utils.config  # Validate configuration
```

### Environment Variables

Required variables in `.env`:
- `GROQ_API_KEY`: Groq API key for LLM
- `SECRET_KEY`: Application secret key

Optional variables:
- `OPENAI_API_KEY`: OpenAI API key (alternative embeddings)
- `CHROMA_PERSIST_DIRECTORY`: Vector store location
- `LOG_LEVEL`: Logging level (default: INFO)

## 📋 Approved Sources

The system only ingests and cites information from these 5 approved Groww URLs:

1. [HDFC Mid Cap Fund](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth)
2. [HDFC Equity Fund](https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth)
3. [HDFC Focused Fund](https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth)
4. [HDFC ELSS Tax Saver](https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth)
5. [HDFC Large Cap Fund](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth)

## 🔧 Phase-by-Phase Implementation

### Phase 0: Foundation & Governance ✅
- [x] Project structure setup
- [x] Configuration management
- [x] Source registry with whitelisting
- [x] PII detection utilities
- [x] Logging and retry mechanisms

### Phase 1: Ingestion & Corpus Build
```bash
# Run ingestion pipeline
python -m src.ingestion.pipeline
```

### Phase 2: Retrieval Layer
```bash
# Test retrieval
python -m src.retrieval.hybrid_retriever "What is the expense ratio?"
```

### Phase 3: Reasoning & Guardrails
```bash
# Test orchestrator
python -m src.generation.orchestrator
```

### Phase 4: User Interface
```bash
# Start backend
uvicorn src.backend.main:app --reload

# Start frontend (separate terminal)
cd frontend && npm start
```

### Phase 5: Evaluation & Compliance
```bash
# Run evaluation suite
python -m tests.evaluation.run_eval
```

## 🛡️ Safety & Compliance

### PII Protection
- Automatic detection and redaction of PAN, Aadhaar, email, phone numbers
- No PII storage in logs or databases
- Hashed analytics for privacy

### Source Control
- Strict URL whitelist enforcement
- CI gates for compliance validation
- Atomic updates with rollback capability

### Content Governance
- Facts-only responses (no investment advice)
- Automatic refusal of advisory/comparative queries
- Single source citation per response

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v --cov=src

# Run specific phase tests
pytest tests/ingestion/ -v
pytest tests/retrieval/ -v
```

## 📊 Monitoring & Observability

- Structured logging with PII protection
- Metrics endpoint at `http://localhost:9090/metrics`
- Health checks at `http://localhost:8000/health`
- Comprehensive error tracking

## 🔒 Security

- HTTPS-only API communication
- Rate limiting and abuse protection
- Input validation and sanitization
- Environment-based secret management

## 📚 Documentation

- [Architecture Details](docs/PhaseWiseArchitecture.md)
- [Edge Cases Analysis](docs/edge-cases.md)
- [API Documentation](docs/api.md) (generated)
- [Deployment Guide](docs/deployment.md)

## 🤝 Contributing

1. Follow phase-by-phase implementation approach
2. Maintain architectural consistency
3. Update documentation for changes
4. Ensure all tests pass
5. Follow coding standards (Black, isort, mypy)

## 📄 License

[License information]

## 🆘 Support

For issues and questions:
- Check [Edge Cases Analysis](docs/edge-cases.md) first
- Review logs for detailed error information
- Create GitHub issues with full context

---

**Disclaimer**: Facts-only. No investment advice.
