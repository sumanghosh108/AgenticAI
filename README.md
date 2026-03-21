# AgenticAI - Autonomous Research & Decision Intelligence Platform

> **🚀 Live Demo:** Experience AgenticAI in action at [agenticai.sumannaba.in](https://agenticai.sumannaba.in)

## Problem Statement
In today's fast-paced business environment, conducting deep, comprehensive research on specialized topics is highly manual, time-consuming, and prone to human bias. Analysts and researchers spend countless hours gathering data from various sources, synthesizing information, and drafting reports, which delays critical decision-making. Additionally, complex business decisions require breaking down problems into manageable tasks and coordinating insights across multiple domains.

## What AgenticAI Does
**AgenticAI** is an autonomous AI-driven research and decision intelligence platform that automates the entire research and analysis process. The system uses specialized AI agents orchestrated through LangGraph to:

- **Autonomous Research:** Conduct multi-turn, simulated interviews with diverse analyst personas to gather comprehensive perspectives on any topic
- **Real-Time Intelligence:** Search the web autonomously using multiple sources (Tavily, DuckDuckGo, Wikipedia, YouTube) for current, accurate information
- **Decision Analysis:** Decompose complex queries into atomic tasks, route them to specialized domain agents, and synthesize actionable recommendations
- **Professional Reports:** Generate structured, citation-backed PDF reports with introduction, analysis sections, and conclusions
- **Cross-Verification:** Validate findings across multiple sources to ensure accuracy and reduce hallucination

This transforms multi-day research and analysis processes into tasks that take only minutes.

## Business Impact
- **Time Savings:** Reduces research and report generation time by up to 90%, freeing analysts to focus on strategy and action
- **Cost Efficiency:** Lowers operational costs by automating manual data processing, synthesis, and decision support
- **Objective Insights:** Eliminates human bias by gathering diverse perspectives autonomously through multiple AI personas
- **Accelerated Decision-Making:** Provides executives and stakeholders with rapid, high-quality insights and recommendations on demand
- **Scalable Intelligence:** Handle multiple research projects simultaneously with parallel agent execution

---

## Architecture Overview

AgenticAI follows a multi-agent orchestration pattern with specialized agents for different domains and tasks:

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                    │
│  Dashboard │ Analysis │ Reports │ Metrics │ Auth            │
└────────────┬────────────────────────────────────────────────┘
             │ REST API + WebSocket
┌────────────┴────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           LangGraph Orchestration Layer              │   │
│  │  ┌────────────────┐  ┌────────────────┐             │   │
│  │  │ Report         │  │ Decision       │             │   │
│  │  │ Generator      │  │ Workflow       │             │   │
│  │  │ Workflow       │  │ Builder        │             │   │
│  │  └────────┬───────┘  └────────┬───────┘             │   │
│  └───────────┼──────────────────┼─────────────────────┘   │
│              │                  │                           │
│  ┌───────────┴──────────────────┴─────────────────────┐   │
│  │            Specialized Agent Layer                  │   │
│  │  • ResearchAgent    • FinanceAgent                  │   │
│  │  • HealthcareAgent  • CriticAgent                   │   │
│  └─────────────────────┬───────────────────────────────┘   │
│                        │                                    │
│  ┌─────────────────────┴───────────────────────────────┐   │
│  │              Tool & Service Layer                    │   │
│  │  • Web Search (Tavily, DuckDuckGo)                   │   │
│  │  • Data Analysis • Document Parser • Scraper         │   │
│  │  • Task Queue • Memory • Verification                │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────┴────────────────────────────────────────────────┐
│  PostgreSQL Database │ B2 Cloud Storage │ External APIs     │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend
- **Framework:** FastAPI + Uvicorn (async Python web server)
- **AI/LLM:** LangGraph, LangChain, LangChain Core
- **LLM Providers:** OpenRouter, Google GenAI (Gemini), OpenAI, Groq (multi-provider support)
- **Search & Data:** Tavily API, Wikipedia, DuckDuckGo, YouTube Search, yfinance
- **Database:** PostgreSQL + Supabase integration
- **Document Generation:** FPDF2 (PDF), python-docx (Word), Markdown
- **Authentication:** Google OAuth 2.0 (requests_oauthlib)
- **Storage:** Backblaze B2 (cloud storage for reports)
- **Async/Jobs:** Custom task queue with WebSocket support
- **Logging:** structlog (structured logging)
- **Containerization:** Docker, Docker Compose

### Frontend
- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS + PostCSS
- **Routing:** React Router v6
- **UI Components:** Lucide React (icons), Recharts (charts)
- **State Management:** React Context API (Auth, Theme)
- **HTTP Client:** Custom fetch wrapper with auth injection
- **Real-time:** WebSocket client for task progress streaming
- **Deployment:** Nginx (production), Vercel-ready

---

## Key Features

### 1. Autonomous Research Reports
- Submit any research topic and receive a comprehensive PDF report
- Multi-analyst approach with diverse perspectives
- Real-time web search integration for current information
- Citation-backed findings with source URLs
- Professional formatting with introduction, analysis, and conclusions

### 2. Decision Intelligence
- Complex query decomposition into atomic tasks
- Domain-specific agent routing (Finance, Healthcare, General)
- Parallel task execution with dependency management
- Cross-verification across multiple sources
- Structured decision recommendations with confidence scores

### 3. Real-Time Progress Tracking
- WebSocket-based live updates during report generation
- Step-by-step progress visualization
- Task status monitoring (queued, in-progress, completed)
- Estimated completion time

### 4. Multi-Domain Support
- **Finance:** Market analysis, financial metrics, investment research
- **Healthcare:** Medical research, clinical studies, health trends
- **General:** Any topic with web-searchable information
- Pluggable domain pack architecture for easy extension

### 5. User Management & Analytics
- Google OAuth authentication
- Usage tracking and rate limiting
- Report history and management
- Download reports in multiple formats (PDF, Markdown, DOCX)
- Activity metrics and KPI dashboard

---

## End-to-End Workflows

### Research Report Generation Workflow

```mermaid
graph TD
    A[User Enters Topic in React UI] -->|HTTP POST /api/generate_report| B[FastAPI Backend]
    B --> C[ReportService.start_report_generation]
    C --> D[AutonomousReportGenerator LangGraph]
    D --> E[Create Analyst Personas]
    E --> F[For Each Analyst: Interview Workflow]
    F --> G[Ask Question]
    G --> H[Search Web - Tavily/DuckDuckGo]
    H --> I[Answer Question with LLM]
    I --> J{More Questions?}
    J -->|Yes| G
    J -->|No| K[Write Report Section]
    K --> L[All Analysts Complete]
    L --> M[Write Introduction & Conclusion]
    M --> N[Generate PDF via FPDF2]
    N --> O[Save to PostgreSQL + B2 Storage]
    O --> P[WebSocket: Progress Updates]
    P --> Q[User Downloads PDF Report]
```

### Decision Analysis Workflow

```mermaid
graph TD
    A[User Query] -->|POST /api/decision/analyze| B[TaskDecomposer]
    B --> C[Parse Domain - Finance/Healthcare/General]
    C --> D[Decompose into 3-7 Atomic Tasks]
    D --> E[Identify Dependencies & Execution Layers]
    E --> F[DecisionWorkflowBuilder LangGraph]
    F --> G[Dispatch Tasks to Specialized Agents]
    G --> H[Parallel Execution Where Possible]
    H --> I[Cross-Verify Findings]
    I --> J[Synthesize Recommendations]
    J --> K[Return Structured Decision Output]
    K --> L[WebSocket: Real-time Progress]
    L --> M[Display Results in Analysis Page]
```

---

## Setup & Installation

### Prerequisites
- Python 3.11 or higher
- Node.js 18+ and npm
- PostgreSQL 15+ (or use Docker)
- Docker & Docker Compose (for containerized setup)

### Option 1: Docker Setup (Recommended)

The easiest way to run the entire stack (Database, Backend API, Frontend UI) is via Docker.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sumanghosh108/AgenticAI.git
   cd AgenticAI
   ```

2. **Create your `.env` file** (see Configuration section below)

3. **Build and start all services:**
   ```bash
   docker-compose up -d --build
   ```

4. **Access the application:**
   - **Frontend UI:** http://localhost:3000
   - **Backend API:** http://localhost:8000
   - **API Documentation:** http://localhost:8000/docs

5. **View logs:**
   ```bash
   docker-compose logs -f
   ```

6. **Stop services:**
   ```bash
   docker-compose down
   ```

### Option 2: Manual/Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sumanghosh108/AgenticAI.git
   cd AgenticAI
   ```

2. **Set up Python backend:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL database:**
   - Install PostgreSQL if not already installed
   - Create a database named `AgenticAI`:
     ```sql
     CREATE DATABASE AgenticAI;
     ```
   - Update `DATABASE_URL` in `.env` with your credentials

4. **Configure environment variables:**
   - Create a `.env` file in the root directory (see Configuration section)

5. **Run the FastAPI backend:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Set up and run the React frontend** (in a new terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

7. **Access the application:**
   - **Frontend:** http://localhost:5173 (Vite dev server)
   - **Backend API:** http://localhost:8000
   - **API Docs:** http://localhost:8000/docs

---

## Configuration

### Environment Variables (`.env`)

Create a `.env` file in the root directory with the following configuration:

```ini
# ============================================
# LLM Provider Configuration
# ============================================
# Add API keys for the providers you want to use
GEMINI_API_KEY="your_gemini_api_key"
OPENROUTER_API_KEY="your_openrouter_api_key"  # Free tier available
GROQ_API_KEY="your_groq_api_key"              # Free tier available
OPENAI_API_KEY="your_openai_api_key"

# Select active provider (openrouter, openai, groq, gemini)
LLM_PROVIDER="openrouter"

# ============================================
# Search & Data Tools
# ============================================
TAVILY_API_KEY="your_tavily_api_key"  # Free tier: 1000 searches/month

# ============================================
# Database Configuration
# ============================================
# For Docker setup (matches docker-compose.yml):
DATABASE_URL="postgresql://postgres:password@db:5432/AgenticAI"

# For local setup (update with your PostgreSQL credentials):
# DATABASE_URL="postgresql://postgres:your_password@localhost:5432/AgenticAI"

# ============================================
# API Configuration
# ============================================
# For Docker setup:
API_BASE_URL="http://api:8000/api"

# For local setup:
# API_BASE_URL="http://localhost:8000/api"

# ============================================
# Google OAuth 2.0 (Required for Authentication)
# ============================================
GOOGLE_CLIENT_ID="your_google_client_id"
GOOGLE_CLIENT_SECRET="your_google_client_secret"
GOOGLE_REDIRECT_URI="http://localhost:3000"

# ============================================
# Cloud Storage (Optional - for production)
# ============================================
# B2_APPLICATION_KEY_ID="your_b2_key_id"
# B2_APPLICATION_KEY="your_b2_application_key"
# B2_BUCKET_NAME="your_bucket_name"
```

### Google OAuth Setup

AgenticAI uses Google OAuth 2.0 for secure user authentication. Follow these steps:

1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable OAuth 2.0:**
   - Navigate to **APIs & Services > Credentials**
   - Click **Create Credentials > OAuth client ID**
   - Select **Web application** as the application type

3. **Configure Authorized Redirect URIs:**
   - Add your frontend URL: `http://localhost:3000` (for local development)
   - For production, add your production domain

4. **Copy Credentials:**
   - Copy the **Client ID** and **Client Secret**
   - Add them to your `.env` file as shown above

### Authentication Flow:
1. User clicks "Login with Google" → Redirected to Google consent screen
2. User approves → Google redirects back with authorization code
3. Frontend sends code to backend → Backend exchanges for access token
4. Backend fetches user profile → Creates/verifies user in PostgreSQL
5. JWT token returned to frontend → Stored in localStorage for authenticated API calls

---

## Project Structure

```
AgenticAI/
├── research_and_analyst/          # Backend core
│   ├── agents/                    # Specialized AI agents
│   │   ├── research_agent.py      # General research agent
│   │   ├── finance_agent.py       # Financial analysis agent
│   │   ├── healthcare_agent.py    # Healthcare research agent
│   │   ├── critic_agent.py        # Quality assurance agent
│   │   └── tools/                 # Agent tools (search, scraper, parser)
│   ├── workflows/                 # LangGraph orchestration
│   │   ├── report_generator_workflows.py
│   │   ├── interview_workflow.py
│   │   └── decision_workflow.py
│   ├── decision_engine/           # Task decomposition & routing
│   │   ├── task_decomposer.py
│   │   └── schemas.py
│   ├── domain_packs/              # Pluggable domain configurations
│   │   ├── base_domain.py
│   │   ├── finance_pack.py
│   │   └── healthcare_pack.py
│   ├── api/                       # FastAPI routes & services
│   │   ├── routes/                # HTTP endpoints
│   │   └── services/              # Business logic layer
│   ├── database/                  # PostgreSQL schema & models
│   ├── job_queue/                 # Async task management
│   ├── auth/                      # Google OAuth implementation
│   ├── business_intel/            # KPI extraction & formatting
│   ├── memory/                    # Conversation & persistent memory
│   ├── observability/             # Tracing, metrics, logging
│   ├── reliability/               # Retry handlers, resilient calls
│   ├── verification/              # Cross-verification logic
│   └── storage/                   # B2 cloud storage integration
├── frontend/                      # React TypeScript UI
│   ├── src/
│   │   ├── pages/                 # Route pages
│   │   │   ├── Dashboard/         # Main report generation UI
│   │   │   ├── Analysis/          # Decision analysis interface
│   │   │   ├── Report/            # Report history & viewing
│   │   │   ├── Metrics/           # Usage analytics
│   │   │   └── Auth/              # Login/Signup
│   │   ├── components/            # Reusable UI components
│   │   ├── context/               # Auth & Theme contexts
│   │   ├── hooks/                 # Custom React hooks
│   │   ├── services/              # WebSocket client
│   │   └── api/                   # HTTP client wrapper
│   └── dist/                      # Production build output
├── prompts/                       # LLM prompt templates (v1, v2)
├── generated_report/              # Output directory for reports
├── logs/                          # Application logs
├── main.py                        # FastAPI application entry point
├── docker-compose.yml             # Multi-container orchestration
├── Dockerfile                     # Backend container definition
└── requirements.txt               # Python dependencies
```

---

## Key Components

### Backend Modules

| Module | Responsibility |
|--------|----------------|
| **agents/** | Specialized AI agents with domain expertise and tool access |
| **workflows/** | LangGraph state machines for orchestrating multi-step processes |
| **decision_engine/** | Task decomposition, dependency analysis, agent routing |
| **domain_packs/** | Pluggable configurations for Finance, Healthcare, and other domains |
| **api/routes/** | REST endpoints for auth, reports, decisions, feedback, files |
| **api/services/** | Business logic layer (ReportService, DecisionService) |
| **database/** | PostgreSQL schema, ORM models, user/report management |
| **job_queue/** | Async task queue with checkpoints and WebSocket progress |
| **auth/** | Google OAuth 2.0 flow implementation |
| **business_intel/** | KPI extraction, report formatting, source scoring |
| **memory/** | Short-term (conversation) and long-term (persistent) memory |
| **observability/** | Distributed tracing, metrics collection, structured logging |
| **reliability/** | Retry handlers with exponential backoff, resilient LLM calls |
| **verification/** | Cross-verification of findings across multiple sources |
| **storage/** | B2 cloud storage integration, document format conversion |

### Frontend Structure

| Component | Purpose |
|-----------|---------|
| **pages/Dashboard/** | Main interface for submitting research topics |
| **pages/Analysis/** | Decision analysis and task execution interface |
| **pages/Report/** | Report history, viewing, and download management |
| **pages/Metrics/** | Usage statistics and analytics dashboard |
| **pages/Auth/** | Login and signup with Google OAuth |
| **components/common/** | Reusable UI elements (Button, Card, Modal, etc.) |
| **components/charts/** | Data visualization components |
| **context/** | Global state management (Auth, Theme) |
| **hooks/** | Custom React hooks (useTaskProgress) |
| **services/** | WebSocket client for real-time updates |
| **api/client.ts** | Centralized HTTP client with auth token injection |

---

## How It Works

### Research Report Generation

1. **User Input:** User submits a research topic through the Dashboard
2. **Analyst Creation:** System generates 2-3 analyst personas with unique perspectives
3. **Interview Workflow:** Each analyst conducts a multi-turn interview:
   - Asks focused research questions
   - Searches the web using Tavily/DuckDuckGo
   - Synthesizes answers from search results
   - Iterates until comprehensive coverage
4. **Section Writing:** Each analyst writes their section with citations
5. **Report Assembly:** Introduction and conclusion are generated
6. **PDF Generation:** Markdown converted to professional PDF
7. **Storage:** Report saved to PostgreSQL + B2 cloud storage
8. **Delivery:** User downloads the final report

### Decision Analysis

1. **Query Submission:** User submits a complex decision query
2. **Task Decomposition:** System breaks query into 3-7 atomic tasks
3. **Domain Detection:** Identifies relevant domain (Finance, Healthcare, General)
4. **Agent Routing:** Tasks assigned to specialized agents
5. **Parallel Execution:** Independent tasks run concurrently
6. **Cross-Verification:** Findings validated across multiple sources
7. **Synthesis:** Results combined into actionable recommendations
8. **Delivery:** Structured decision output with confidence scores

---

## API Endpoints

### Authentication
- `GET /api/google_auth_url` - Get Google OAuth authorization URL
- `POST /api/google_auth` - Exchange auth code for JWT token
- `GET /api/user` - Get current user profile

### Reports
- `POST /api/generate_report` - Start autonomous report generation
- `GET /api/reports` - List user's reports
- `GET /api/reports/{report_id}` - Get specific report details
- `GET /api/reports/{report_id}/download` - Download report file
- `DELETE /api/reports/{report_id}` - Delete a report

### Decision Analysis
- `POST /api/decision/analyze` - Analyze complex decision query
- `GET /api/decision/tasks/{task_id}` - Get task status

### Feedback & Metrics
- `POST /api/feedback` - Submit user feedback
- `GET /api/metrics` - Get usage statistics

### WebSocket
- `WS /ws/task/{task_id}` - Real-time task progress updates

---

## Usage Examples

### Generate a Research Report

```python
import requests

# Authenticate
auth_response = requests.post("http://localhost:8000/api/google_auth", 
    json={"code": "google_auth_code"})
token = auth_response.json()["access_token"]

# Generate report
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://localhost:8000/api/generate_report",
    headers=headers,
    json={
        "topic": "Impact of AI on Healthcare in 2026",
        "num_analysts": 3,
        "questions_per_analyst": 5
    }
)

task_id = response.json()["task_id"]
print(f"Report generation started: {task_id}")
```

### Analyze a Decision

```python
response = requests.post(
    "http://localhost:8000/api/decision/analyze",
    headers=headers,
    json={
        "query": "Should we invest in renewable energy stocks in Q2 2026?",
        "domain": "finance"
    }
)

decision = response.json()
print(f"Recommendation: {decision['recommendation']}")
```

---

## Development

### Running Tests
```bash
# Backend tests
pytest

# Frontend tests
cd frontend && npm test
```

### Code Quality
```bash
# Python linting
ruff check .

# Python formatting
ruff format .

# TypeScript checking
cd frontend && npm run type-check
```

### Database Migrations
```bash
# The database schema is automatically created on first run
# Check research_and_analyst/database/db_config.py for schema definitions
```

---

## Deployment

### Production Deployment (Render)

1. **Backend:**
   - Connect your GitHub repository to Render
   - Create a new Web Service
   - Set environment variables from `.env`
   - Deploy command: `uvicorn main:app --host 0.0.0.0 --port 8000`

2. **Frontend:**
   - Deploy to Vercel or Render
   - Set `API_BASE_URL` to your backend URL
   - Build command: `npm run build`
   - Publish directory: `dist`

3. **Database:**
   - Use Render PostgreSQL or managed PostgreSQL service
   - Update `DATABASE_URL` in environment variables

### Environment-Specific Configuration

**Local Development:**
```ini
DATABASE_URL="postgresql://postgres:password@localhost:5432/AgenticAI"
API_BASE_URL="http://localhost:8000/api"
GOOGLE_REDIRECT_URI="http://localhost:3000"
```

**Docker:**
```ini
DATABASE_URL="postgresql://postgres:password@db:5432/AgenticAI"
API_BASE_URL="http://api:8000/api"
GOOGLE_REDIRECT_URI="http://localhost:3000"
```

**Production:**
```ini
DATABASE_URL="postgresql://user:pass@prod-db-host:5432/AgenticAI"
API_BASE_URL="https://api.yourdomain.com/api"
GOOGLE_REDIRECT_URI="https://yourdomain.com"
```

---

## Notable Design Patterns

### 1. Multi-Agent Orchestration
- Agents specialized by domain with distinct tool access
- LangGraph manages state transitions and conditional routing
- Parallel execution where tasks are independent

### 2. Pluggable Domain Packs
- `BaseDomainPack` interface for extensibility
- Each pack defines tools, metrics, scoring dimensions, prompts
- Easy to add new domains without modifying core logic

### 3. Context-Constrained Prompts
- Research agents explicitly instructed to use ONLY provided sources
- Prevents hallucination by bounding LLM context
- All outputs include source citations

### 4. Async Task Queue with Checkpoints
- Long-running tasks don't block HTTP responses
- Checkpoints allow resuming interrupted workflows
- WebSocket streams progress to frontend in real-time

### 5. Interview-Based Research
- Multi-turn Q&A between analyst personas and expert
- Produces natural, conversational report sections
- Each turn: question → search → answer → iterate

### 6. Hybrid Search Strategy
- Primary: Tavily (real-time, high-quality)
- Fallback: DuckDuckGo, Wikipedia, YouTube
- Multi-query generation for comprehensive coverage

### 7. Rate Limiting & Usage Tracking
- Daily usage limits per user
- Tracks report generation, downloads, API calls
- Prevents abuse while maintaining generous quotas

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and test thoroughly
4. Commit with clear messages: `git commit -m "Add feature X"`
5. Push to your fork: `git push origin feature/your-feature`
6. Open a Pull Request

---

## License

This project is licensed under the terms specified in [LICENSE](LICENSE).

---

## Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

---

## Support & Contact

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check existing documentation in `/docs`
- Review API documentation at `http://localhost:8000/docs`

---

## Roadmap

- [ ] Additional domain packs (Legal, Technology, Marketing)
- [ ] Multi-language report generation
- [ ] Advanced visualization and charts in reports
- [ ] Collaborative research with team workspaces
- [ ] API rate limiting and usage tiers
- [ ] Enhanced memory and context retention
- [ ] Integration with enterprise knowledge bases
- [ ] Custom agent creation interface

---

**Built with ❤️ using LangGraph, FastAPI, and React**
