# Agentic BI Platform

An AI-powered data analysis and visualization platform with intelligent agentic workflows, human-in-the-loop capabilities, and real-time collaboration features.

## Features

- **AI-Powered Analysis**: Natural language to SQL query generation using Azure OpenAI
- **Multi-Agent Workflow**: LangGraph-based orchestration for complex data analysis tasks
- **Human-in-the-Loop**: Interactive approval and guidance for AI-generated queries
- **Real-time Updates**: WebSocket-based live progress monitoring
- **Data Visualization**: Automatic chart generation with customizable styles
- **Role-Based Access**: Fine-grained authorization using Open Policy Agent (OPA)
- **Multi-Database**: Connect to various data sources via MindsDB integration
- **Observability**: Full agent tracing and evaluation with Langfuse integration

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **LangChain & LangGraph** - AI agent orchestration
- **Azure OpenAI** - LLM for query generation
- **PostgreSQL** - Primary database
- **Redis** - Caching and message broker
- **Celery** - Async task processing
- **SQLAlchemy** - ORM

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first styling
- **Shadcn/ui** - Component library
- **Zustand** - State management
- **Recharts** - Data visualization

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **Traefik** - Reverse proxy (external, existing instance)
- **OPA** - Authorization (external, existing instance)
- **MindsDB** - Database connectivity (external service)
- **Langfuse** - Agent observability and evaluation (external service)
- **GitHub Actions** - CI/CD pipeline

## Development Workflow

This project follows **trunk-based development** practices:

- All development happens on short-lived feature branches
- Main branch is always deployable
- Small, frequent merges to main
- Feature flags for work-in-progress features

### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd agentic_bi

# Install pre-commit hooks (recommended)
pip install pre-commit
pre-commit install

# Set up environment variables
make env
# Edit .env file with your configuration

# Start services
make up

# View logs
make logs

# Access the application
# Frontend: http://localhost:3000 (or your configured domain)
# Backend API: http://localhost:8000 (or your configured domain)
# API Docs: http://localhost:8000/docs
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed workflow guidelines.

## Prerequisites

- **Docker** and **Docker Compose** v2.x or higher
- **Make** (for convenience commands)
- **Existing Traefik** instance running on `web` network
- **Existing OPA** instance for authorization (no auth required)
- **Existing Langfuse** instance for observability (requires API keys)
- **Azure OpenAI** account with API access
- **MindsDB** instance for database connectivity (no auth required for MVP)

## Initial Setup

### 1. Environment Configuration

Copy the example environment file and configure it:

```bash
make env
```

Edit `.env` file and configure the following critical variables:

```bash
# Traefik Configuration (adjust to match your setup)
TRAEFIK_NETWORK=web
TRAEFIK_ENTRYPOINT=websecure
TRAEFIK_CERTRESOLVER=letsencrypt
FRONTEND_DOMAIN=agentic-bi.yourdomain.com
API_DOMAIN=api-agentic-bi.yourdomain.com

# Azure OpenAI (required)
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4

# External Services
MINDSDB_API_URL=https://your-mindsdb-instance.com  # No auth
OPA_URL=http://your-opa-instance:8181               # No auth
LANGFUSE_HOST=https://your-langfuse-instance.com    # Requires keys below
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx

# Database (use secure passwords in production)
POSTGRES_PASSWORD=secure-password-here
REDIS_PASSWORD=secure-redis-password

# JWT Secret (generate a secure random string)
JWT_SECRET=your-secure-jwt-secret-here
```

### 2. Traefik Network Setup

Ensure your containers can connect to the existing Traefik network:

```bash
# Check if the 'web' network exists
docker network ls | grep web

# If it doesn't exist, create it
docker network create web
```

The default network name is `web`. If your Traefik uses a different network name, update the `TRAEFIK_NETWORK` variable in `.env`.

### 3. Build and Start Services

```bash
# Build Docker images
make build

# Start all services
make up

# Check service status
make ps

# View logs
make logs
```

### 4. Verify Installation

```bash
# Check backend health
curl http://localhost:8000/health

# Check if services are running
make ps
```

## Development Commands

The project includes a Makefile with convenient commands:

### Service Management
```bash
make up          # Start all services
make down        # Stop all services
make restart     # Restart all services
make ps          # Show running containers
make logs        # View all logs
make logs-backend   # View backend logs only
make logs-frontend  # View frontend logs only
```

### Database Management
```bash
make db-shell    # Access PostgreSQL shell
make db-migrate  # Run database migrations
make db-reset    # Reset database (WARNING: deletes data)
```

### Development
```bash
make backend-shell   # Access backend container shell
make frontend-shell  # Access frontend container shell
make redis-cli       # Access Redis CLI
make test            # Run all tests
make lint            # Run linters
make format          # Format code
```

### Cleanup
```bash
make clean       # Remove containers and volumes
make clean-all   # Remove everything including images
```

## Project Structure

```
agentic_bi/
├── backend/                # FastAPI backend
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Core configuration
│   │   ├── services/      # Business logic
│   │   ├── models/        # Database models
│   │   ├── agents/        # AI agents
│   │   ├── tools/         # Agent tools
│   │   └── schemas/       # Pydantic schemas
│   ├── tests/             # Backend tests
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/              # Next.js frontend
│   ├── src/
│   │   ├── app/          # App router pages
│   │   ├── components/   # React components
│   │   ├── lib/          # Utilities
│   │   ├── hooks/        # Custom hooks
│   │   ├── stores/       # Zustand stores
│   │   ├── types/        # TypeScript types
│   │   └── services/     # API clients
│   ├── public/           # Static assets
│   ├── Dockerfile
│   └── package.json
│
├── infrastructure/        # Infrastructure configs
│   ├── postgres/
│   │   └── init/         # Database init scripts
│   └── redis/
│
├── scripts/              # Utility scripts
├── docs/                 # Documentation
├── prp_files/           # Planning documents
├── docker-compose.yml   # Docker compose config
├── Makefile            # Development commands
└── .env.example        # Environment template
```

## CI/CD

All PRs must pass:
- Automated tests
- Security scanning
- Code quality checks
- Branch age and size checks

Status checks are enforced on the `main` branch.

## Branch Protection

The `main` branch is protected with:
- Required pull request reviews
- Required status checks
- No direct pushes (except emergencies)
- Linear history enforcement

See [.github/BRANCH_PROTECTION.md](.github/BRANCH_PROTECTION.md) for details.

## Configuration

### Traefik Labels

The services are configured to work with an existing Traefik instance. Key labels:

- `traefik.enable=true` - Enable Traefik for the service
- `traefik.docker.network` - Connect to your Traefik network
- `traefik.http.routers.*.rule` - Routing rules (domain-based)
- `traefik.http.routers.*.entrypoints` - Entry points (websecure for HTTPS)
- `traefik.http.routers.*.tls.certresolver` - Let's Encrypt resolver

Customize these in `docker-compose.yml` or via environment variables.

### Environment Variables

Key environment variables (see `.env.example` for complete list):

| Variable | Description | Required |
|----------|-------------|----------|
| `TRAEFIK_NETWORK` | Traefik network name (default: `web`) | Yes |
| `FRONTEND_DOMAIN` | Frontend domain | Yes |
| `API_DOMAIN` | API domain | Yes |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Yes |
| `MINDSDB_API_URL` | MindsDB instance URL | Yes |
| `OPA_URL` | OPA instance URL | Yes |
| `LANGFUSE_HOST` | Langfuse instance URL | Yes |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public API key | Yes |
| `LANGFUSE_SECRET_KEY` | Langfuse secret API key | Yes |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `JWT_SECRET` | JWT signing secret | Yes |
| `REDIS_PASSWORD` | Redis password | Yes |

## Troubleshooting

### Services won't start
- Check if Traefik network `web` exists: `docker network ls | grep web`
- Verify `.env` file is configured correctly
- Check logs: `make logs`

### Database connection errors
- Ensure PostgreSQL is healthy: `make ps`
- Check database credentials in `.env`
- Access database shell: `make db-shell`

### Traefik routing issues
- Verify domain DNS points to your server
- Check Traefik labels in `docker-compose.yml`
- Ensure `TRAEFIK_NETWORK=web` in `.env`
- Verify services are connected to web network: `docker network inspect web`

### Frontend can't connect to backend
- Verify `NEXT_PUBLIC_API_URL` is correctly set
- Check CORS settings in backend
- Inspect browser console for errors

### External service connection issues
- Verify MindsDB URL is accessible: `curl ${MINDSDB_API_URL}/health`
- Check OPA is accessible: `curl ${OPA_URL}/health`
- Test Langfuse connection: `curl ${LANGFUSE_HOST}/api/public/health`
- Verify Langfuse API keys are correct
- Ensure external services are reachable from Docker containers

## Resources

- [Implementation Plan](prp_files/implementation_plan.md) - 12-week development roadmap
- [Technical Specifications](prp_files/technical_specifications.md) - Detailed component specs
- [Contributing Guide](CONTRIBUTING.md) - Development workflow and best practices
- [Branch Protection Guidelines](.github/BRANCH_PROTECTION.md) - Branch protection rules
- [CI/CD Pipeline](.github/workflows/ci.yml) - Automated checks configuration

## Development Roadmap

This project follows a 6-sprint, 12-week implementation plan:

- **Sprint 0** (Weeks 0-1): Foundation & POCs ✅ **(PR#1 Complete)**
- **Sprint 1** (Weeks 2-3): Core Backend & Agent Foundation
- **Sprint 2** (Weeks 4-5): Agent Tools & Workflow Engine
- **Sprint 3** (Weeks 6-7): Frontend & Real-time Features
- **Sprint 4** (Weeks 8-9): Human-in-the-Loop & Visualization
- **Sprint 5** (Weeks 10-11): Integration & Polish
- **Sprint 6** (Week 12): Deployment & Launch

See [Implementation Plan](prp_files/implementation_plan.md) for details.

## Getting Help

- Review the contributing guide
- Check existing issues and PRs
- Consult technical specifications
- Ask questions in team channels

## License

[Add your license here]

---

**Remember:** Integrate early, integrate often!
