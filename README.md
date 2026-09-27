# ContentPulse ⚡
> **Real-Time Competitor Content Monitoring & Intelligence Platform**

ContentPulse is an automated platform that continuously monitors competitor websites to detect newly published articles, blog posts, and press releases with minimal detection latency.

---

## 🌟 Key Features

- **Multi-Source Automatic Discovery**: Auto-detects and monitors:
  - **RSS / Atom Feeds**
  - **XML Sitemaps & Sitemap Indexes**
  - **Direct Blog / Article Listings**
- **Resilient Engine**:
  - **10 Concurrent Worker Threads** using `ThreadPoolExecutor`
  - **Exponential Backoff Retry Strategy** (1s, 2s, 4s backoff for transient 5xx/429 network errors)
  - **15-Second Request Timeouts** with failure isolation
  - **Deduplication Engine** (URL & canonical URL deduplication)
- **Deep Content Extraction**:
  - Full article body & markdown structure
  - Title, author, published date, detection timestamp
  - JSON-LD & OpenGraph metadata parsing (categories, tags, featured images)
  - Extracted internal and external relevant links
- **Full-Featured Dashboard & Intelligence UI**:
  - Real-time KPI metrics (Competitor counts, tracked articles, average/fastest/slowest delays)
  - Interactive delay performance distribution
  - Discovered content ranking by competitor
  - Competitor CRUD management (Add, Edit, Delete, Immediate Manual Trigger)
  - Searchable & filterable article feeds with full-content detail modals
  - Observability & health monitoring with latency records and failure diagnostics

---

## 🏗️ Architecture & Tech Stack

### **Backend**
- **Framework**: FastAPI (Python 3.10+)
- **ORM & Database**: SQLAlchemy (PostgreSQL / SQLite compatible)
- **Scheduler**: APScheduler (`BackgroundScheduler`)
- **Concurrency**: `concurrent.futures.ThreadPoolExecutor`
- **Scraping & Parsing**: `BeautifulSoup4`, `feedparser`, `requests`

### **Frontend**
- **Framework**: React 19 + Vite
- **Styling**: Modern Vanilla CSS
- **Icons**: Lucide React
- **HTTP Client**: Axios

---

## 🚀 Quick Start Guide

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirement.txt

# Start FastAPI dev server
uvicorn main:app --reload --port 8000
```
Backend API docs available at: `http://127.0.0.1:8000/docs`

---

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
Open your browser at: `http://localhost:5173`

---

### 3. Running Demo Sites (Testing & Simulation)

ContentPulse includes test servers to simulate real-time publishing and timeout resilience:

```bash
# Fast controlled RSS demo blog (Publish via http://127.0.0.1:9000/publish?title=My+Article)
python demo_site.py

# Slow server to test 15-second timeout and retry resilience
python slow_demo_site.py
```

---

## 📊 API Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/dashboard/stats` | Aggregated metrics, delay ranges, competitor rankings |
| `GET` | `/competitors` | List all monitored competitors with source counts |
| `POST` | `/competitors` | Add new competitor with automatic site analysis |
| `GET` | `/competitors/{id}` | Deep dive with configured sources and recent logs |
| `PATCH` | `/competitors/{id}` | Update competitor endpoints or toggle monitoring |
| `DELETE` | `/competitors/{id}` | Delete competitor and cascade delete history |
| `POST` | `/competitors/{id}/check` | Trigger immediate monitoring cycle for competitor |
| `GET` | `/articles` | Filterable and searchable detected articles feed |
| `GET` | `/articles/{id}` | Single article detail with full body content and links |
| `GET` | `/monitoring/logs` | Observability logs with response latency and errors |

---

## 🛡️ Reliability & Performance

- **Concurreny Load Test**: Passed 100-site simultaneous checks in under 4 seconds.
- **Live Detection Speed**: Detected newly published content in **17 seconds** under continuous monitoring.
- **Fail-Safe Isolation**: Faulty or slow sites are retried with exponential backoff without blocking other concurrent checks.
