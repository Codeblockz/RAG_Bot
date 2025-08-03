# RAG Chatbot Template

A production-ready, template-worthy RAG (Retrieval-Augmented Generation) chatbot with modular architecture and comprehensive cloud deployment strategies.

## Features

- **Modular Architecture**: Strategy pattern implementation allowing easy swapping of LLM providers, vector stores, and embedding services
- **Multi-Cloud Ready**: Native support for AWS and Azure with Infrastructure as Code (Terraform)
- **Domain-Agnostic Design**: YAML-based configuration system enabling rapid customization for any industry
- **Production-Ready**: Comprehensive error handling, monitoring, security, and auto-scaling capabilities
- **Template Reusability**: Abstract base classes and factory patterns for maximum extensibility

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenAI API key
- Pinecone API key (optional, ChromaDB available as fallback)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/rag-chatbot-template.git
   cd rag-chatbot-template
   ```

2. **Set up environment variables**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your API keys and configuration
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Verify installation**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/info
   ```

### Manual Setup (Development)

1. **Create virtual environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start the application**
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Configuration

The application uses a hierarchical configuration system:

1. **Environment Variables** (highest priority)
2. **YAML Configuration Files** (config/config.yaml, config/config.{environment}.yaml)
3. **Default Values** (lowest priority)

### Key Configuration Sections

- **API Settings**: Host, port, CORS, rate limiting
- **OpenAI Settings**: API key, models, parameters
- **Vector Store**: Pinecone or ChromaDB configuration
- **Database**: PostgreSQL connection settings
- **Security**: Authentication, API keys, rate limiting
- **Logging**: Level, format, output destinations

### Example Configuration

```yaml
# config/config.yaml
api:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["http://localhost:3000"]

openai:
  model: "gpt-4"
  temperature: 0.7
  max_tokens: 1000

vector_store_provider: "pinecone"
llm_provider: "openai"
embeddings_provider: "openai"
```

## Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend UI   │    │   Backend API   │    │   Vector Store  │
│   (React/Next)  │◄──►│   (FastAPI)     │◄──►│ (Pinecone/Chroma)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   LLM Provider  │
                       │ (OpenAI/Anthropic)│
                       └─────────────────┘
```

### Service Abstractions

- **LLMProvider**: Interface for language model providers (OpenAI, Anthropic)
- **EmbeddingsService**: Interface for embedding services
- **VectorStore**: Interface for vector databases (Pinecone, ChromaDB)
- **RetrievalStrategy**: Interface for document retrieval strategies
- **ChatService**: Interface for conversation orchestration

### Factory Pattern

The `ServiceFactory` creates and manages service instances based on configuration:

```python
from app.services.factory import ServiceFactory

# Get configured services
llm_provider = ServiceFactory.get_llm_provider()
embeddings_service = ServiceFactory.get_embeddings_service()
vector_store = ServiceFactory.get_vector_store()
```

## API Endpoints

### Health and Status

- `GET /health` - Basic health check
- `GET /ready` - Readiness check with service validation
- `GET /info` - Application information and available providers

### Documentation

- `GET /docs` - OpenAPI/Swagger documentation (development only)
- `GET /redoc` - ReDoc documentation (development only)

## Testing

### Running Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test files
pytest tests/unit/test_config.py
pytest tests/integration/

# Run tests in parallel
pytest -n auto
```

### Test Structure

```
tests/
├── unit/                 # Unit tests for individual components
├── integration/          # Integration tests for service interactions
├── fixtures/            # Test data and fixtures
└── conftest.py          # Shared test configuration
```

## Development

### Code Quality

The project uses several tools for code quality:

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy app/

# Run pre-commit hooks
pre-commit run --all-files
```

### Adding New Services

1. **Create service implementation**
   ```python
   # app/services/llm/custom_provider.py
   from ..base import LLMProvider
   
   class CustomLLMProvider(LLMProvider):
       async def generate_response(self, messages, **kwargs):
           # Implementation here
           pass
   ```

2. **Register with factory**
   ```python
   # In factory.py or module __init__.py
   ServiceFactory.register_llm_provider("custom", CustomLLMProvider)
   ```

3. **Update configuration**
   ```yaml
   llm_provider: "custom"
   ```

## Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Scale backend service
docker-compose up -d --scale backend=3

# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables for Production

```bash
# Required
OPENAI_API_KEY=your-openai-api-key
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
SECURITY_SECRET_KEY=your-secure-secret-key

# Database
DB_URL=postgresql://user:password@host:5432/database

# Optional
LOG_LEVEL=INFO
ENVIRONMENT=production
API_WORKERS=4
```

### Cloud Deployment

Refer to deployment documentation:

- [AWS Deployment Guide](docs/deployment/aws.md)
- [Azure Deployment Guide](docs/deployment/azure.md)
- [Kubernetes Guide](docs/deployment/kubernetes.md)

## Customization

### Domain Adaptation

1. **Custom Prompts**: Edit `config/prompts.yaml`
2. **Document Processing**: Modify chunking strategies in `app/utils/`
3. **UI Customization**: Update frontend themes and labels
4. **Business Logic**: Add domain-specific processing plugins

### Example: Legal Document Processing

```yaml
# config/prompts.yaml
system_prompt: |
  You are a legal assistant that helps users understand legal documents.
  Always cite specific sections and provide clear explanations.

chunk_size: 2000  # Larger chunks for legal documents
chunk_overlap: 400

retrieval_strategy: "legal_hybrid"  # Custom strategy
```

## Monitoring and Observability

### Logging

- Structured JSON logging with contextual information
- Request tracing with unique request IDs
- Performance metrics (response time, token usage, costs)

### Health Checks

- Application health endpoint
- Service dependency validation
- Database connectivity checks

### Metrics

- API response times
- LLM token usage and costs
- Vector search performance
- Error rates and types

## Security

### Features

- API key authentication
- Rate limiting per client
- Input validation and sanitization
- Security headers (CORS, CSP, etc.)
- File upload validation

### Best Practices

- Store API keys in environment variables or secret managers
- Use HTTPS in production
- Regular security updates
- Input sanitization and validation
- Audit logging for sensitive operations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation for new features
- Use conventional commit messages
- Maintain backward compatibility

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [Full documentation](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/rag-chatbot-template/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/rag-chatbot-template/discussions)

## Roadmap

- [ ] Phase 2: Vector storage and retrieval strategies
- [ ] Phase 3: Advanced RAG features and conversation memory
- [ ] Phase 4: React frontend with real-time streaming
- [ ] Phase 5: Production deployment automation
- [ ] Multi-language support
- [ ] Advanced analytics and monitoring
- [ ] Plugin system for custom integrations
