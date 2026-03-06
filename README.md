# AgenticAI- Autonomus report generation

## Problem Statement
In today's fast-paced business environment, conducting deep, comprehensive research on specialized topics is highly manual, time-consuming, and prone to human bias. Analysts and researchers spend countless hours gathering data from various sources, synthesizing information, and drafting reports, which delays critical decision-making.

## What Problem It Solves
**AgenticAI** is an autonomous AI-driven research assistant that automates the entire research process. Instead of manually searching for information and compiling data, AgenticAI uses intelligent agents to:
- Conduct multi-turn, simulated interviews to gather diverse perspectives on a given topic.
- Autonomously search the web for real-time, accurate information.
- Synthesize findings into structured, professional, and comprehensive PDF reports.
This transforms a multi-day research process into a task that takes only minutes.

## Business Impact
- **Time Savings:** Reduces research and report generation time by up to 90%, freeing analysts to focus on strategy and action.
- **Cost Efficiency:** Lowers operational costs by automating manual data processing and synthesis.
- **Objective Insights:** Eliminates human bias by gathering diverse perspectives autonomously.
- **Accelerated Decision-Making:** Provides executives and stakeholders with rapid, high-quality insights on demand.

---

## Tech Stack Used
- **Core AI Framework:** LangGraph, LangChain, LangChain Core
- **LLM Providers:** OpenRouter, Google GenAI, OpenAI, Groq
- **Search & Tools:** Tavily API, Wikipedia, DuckDuckGo (ddgs), YouTube Search, yfinance
- **Backend API:** FastAPI, Uvicorn
- **Frontend UI:** Streamlit
- **Database:** PostgreSQL (with `psycopg2-binary`)
- **Document Generation:** FPDF2, Markdown
- **Authentication:** Google OAuth (`requests_oauthlib`)
- **Containerization:** Docker, Docker Compose

---

## End-to-End Workflow

```mermaid
graph TD
    A[User Enters Topic in Streamlit UI] -->|HTTP POST| B[FastAPI Backend]
    B --> C[LangGraph Pipeline Starts]
    C --> D[Create Analyst & Perspectives]
    D --> E[Conduct Multi-Turn Interviews]
    E -->|Tavily/Web Search| F[Gather Real-Time Data]
    F --> G[Write Report Sections]
    G --> H[Finalize & Format Report]
    H --> I[Generate PDF via FPDF2]
    I --> J[Save to PostgreSQL & Return to UI]
    J --> K[User Downloads PDF Report]
```

### Workflow Steps:
1. **Input:** The user logs in via the Streamlit frontend and submits a research topic.
2. **Analyst Creation:** The system generates analytical personas tailored to the topic.
3. **Interview/Research:** The generated analysts perform autonomous web searches (Tavily) and interview simulations to gather deep insights.
4. **Drafting:** The system drafts the Introduction, Body, and Conclusion based on the gathered data.
5. **Finalization:** The report is formatted into Markdown and then converted to a downloadable PDF.
6. **Storage:** User data and report metadata are stored securely in PostgreSQL.

---

## Setup Process

### Option 1: Manual/Local Setup

1. **Clone the repository and navigate to the project directory:**
   ```bash
   git clone https://github.com/sumanghosh108/AgenticAI.git
   cd AgenticAI
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the Database (PostgreSQL):**
   - Ensure you have PostgreSQL installed.
   - Create a database named `AgenticAI` (or adjust `.env` accordingly).

5. **Configure Environment Variables:**
   - Create a `.env` file (see the configuration section below).

6. **Run the FastAPI Backend:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Run the Streamlit Frontend (In a new terminal):**
   ```bash
   streamlit run research_and_analyst/streamlit_app.py --server.port 8501
   ```

### Option 2: Docker Build Process

The easiest way to run the entire stack (Database, Backend API, Frontend UI) is via Docker.

1. **Ensure Docker and Docker Compose are installed.**
2. **Create your `.env` file in the root directory.**
3. **Run the following command to build and start the containers:**
   ```bash
   docker-compose up -d --build
   ```
4. **Access the application:**
   - **Frontend UI:** `http://localhost:8501`
   - **Backend API Docs:** `http://localhost:8000/docs`

---

## Configuration (The `.env` File)

Users must configure several API keys and secrets for the application to function correctly. Create a `.env` file in the root directory with the following structure:

```ini
# LLM Providers (Add keys for the providers you intend to use)
GEMINI_API_KEY="your_gemini_api_key"
OPENROUTER_API_KEY="your_openrouter_api_key" # free of cost
GROQ_API_KEY="your_groq_api_key"
GOOGLE_API_KEY="your_google_api_key"
OPENAI_API_KEY="your_openai_api_key"

# Search Tools
TAVILY_API_KEY="your_tavily_api_key" # free of cost

# Core Application Settings
LLM_PROVIDER="openrouter" # Choose between: openrouter, openai, groq, gemini

# Database Settings
# Local setup URL format (update with your postgres password)
# DATABASE_URL="postgresql://postgres:your_password@localhost:5432/AgenticAI"
# Docker setup URL format (matches docker-compose.yml)
DATABASE_URL="postgresql://postgres:password@db:5432/AgenticAI"

# API Base URL (For Streamlit to communicate with FastAPI)
# Local setup:
# API_BASE_URL="http://localhost:8000/api"
# Docker setup:
API_BASE_URL="http://api:8000/api"

# Google OAuth Settings (Required for Login)
GOOGLE_CLIENT_ID="your_google_client_id"
GOOGLE_CLIENT_SECRET="your_google_client_secret"
GOOGLE_REDIRECT_URI="http://localhost:8501"
```

---

## Google Auth Process

AgenticAI uses Google OAuth 2.0 to securely authenticate users via the Streamlit frontend. Here is how to set it up and how it works:

### Setup Steps for Google Cloud Console:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Navigate to **APIs & Services > Credentials**.
4. Click **Create Credentials > OAuth client ID**.
5. Select **Web application** as the Application type.
6. Under **Authorized readirect URIs**, add your frontend URL exactly as it runs (e.g., `http://localhost:8501`).
7. Copy the generated **Client ID** and **Client Secret** and add them to your `.env` file:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI="http://localhost:8501"`

### How Authentication Works in the App:
1. **Login Trigger:** When a user clicks "Login with Google" on the Streamlit UI, the `research_and_analyst/auth/google_oauth.py` module generates an authorization URL and redirects the user to Google's consent screen.
2. **Callback Handling:** After the user approves, Google redirects back to `http://localhost:8501` with an authorization code.
3. **Token Exchange:** The Streamlit app captures this code and exchanges it for a secure access token.
4. **Session Management:** The user's Google profile information (email, name) is fetched, an account is created/verified in the internal PostgreSQL database, and their session state (`logged_in = True`) is set to grant access to the dashboard.
