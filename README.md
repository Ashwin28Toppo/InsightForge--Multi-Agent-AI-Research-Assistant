# 🔥 InsightForge — Multi-Agent AI Research Assistant

**InsightForge** is an AI-powered **Multi-Agent Research Assistant** that autonomously researches any topic by coordinating multiple specialized AI agents. The system gathers information from the web, extracts detailed content, generates a structured research report, and critically evaluates the final output to ensure quality and completeness.

Built using **LangChain**, **Groq (Llama 3.3 70B)**, **Tavily Search**, **BeautifulSoup**, and **Streamlit**.

---

## 🚀 Features

- 🔍 **Search Agent** — Finds recent and relevant information from the web using Tavily Search
- 📄 **Reader Agent** — Extracts detailed content from selected sources through web scraping
- ✍️ **Writer Agent** — Generates comprehensive and well-structured research reports
- 🧐 **Critic Agent** — Reviews reports and provides constructive feedback with scoring
- 🌐 **Real-Time Web Research** — Accesses current information beyond static training data
- ⚡ **Automated Research Workflow** — End-to-end pipeline from search to final report
- 🎨 **Modern Streamlit Interface** — Interactive dashboard for research generation
- 🧩 **Modular Agent Architecture** — Easily extensible with additional specialized agents

---

## 🏗️ System Workflow

### Research Pipeline

```text
User Research Query
          │
          ▼
 ┌─────────────────┐
 │  Search Agent   │
 │ (Tavily Search) │
 └─────────────────┘
          │
          ▼
 ┌─────────────────┐
 │  Reader Agent   │
 │ (Web Scraping)  │
 └─────────────────┘
          │
          ▼
 ┌─────────────────┐
 │  Writer Agent   │
 │ Report Creation │
 └─────────────────┘
          │
          ▼
 ┌─────────────────┐
 │  Critic Agent   │
 │ Quality Review  │
 └─────────────────┘
          │
          ▼
 Final Research Report
 + Quality Feedback
```

---

## ⚙️ Agent Responsibilities

| Agent | Responsibility |
|---------|--------------|
| Search Agent | Finds reliable and recent information using Tavily Search |
| Reader Agent | Scrapes and extracts detailed content from relevant sources |
| Writer Agent | Synthesizes information into a professional research report |
| Critic Agent | Evaluates report quality, strengths, weaknesses, and overall score |

---

## 🏗️ Tech Stack

### AI & Agent Framework

- LangChain
- Groq API
- Llama 3.3 70B Versatile

### Search & Data Collection

- Tavily Search API
- BeautifulSoup4
- Requests

### Frontend

- Streamlit

### Backend

- Python

### Utilities

- Python Dotenv
- Rich
- Pydantic

---

## 📂 Folder Structure

```text
INSIGHTFORGE/
│
├── app.py
├── agents.py
├── tools.py
├── workflow.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Ashwin28Toppo/InsightForge.git
cd InsightForge
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv .venv
```

### 3️⃣ Activate Environment

Windows:

```bash
.venv\Scripts\Activate.ps1
```

Linux / Mac:

```bash
source .venv/bin/activate
```

### 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 5️⃣ Configure Environment Variables

```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
```

### 6️⃣ Run the Application

```bash
python -m streamlit run app.py
```

Visit:

```text
http://localhost:8501
```

---

## 💬 Example Research Queries

- Latest developments in AI Agents
- Future of Quantum Computing
- Impact of Artificial Intelligence on Healthcare
- Recent advancements in Renewable Energy
- Large Language Models in 2026

---

## 🧩 Core Modules

| Module Name | Description |
|------------|-------------|
| Search Agent | Collects current information from the web |
| Reader Agent | Extracts detailed content from selected sources |
| Writer Agent | Generates structured research reports |
| Critic Agent | Reviews report quality and provides scoring |
| Workflow Engine | Coordinates interactions between agents |
| Streamlit UI | Provides interactive user interface |

---

## 🎯 Future Improvements

- Multi-source research aggregation
- Citation verification system
- PDF report export
- LangGraph integration
- Research memory and context persistence
- Research history dashboard
- Multi-agent collaboration visualization
- Support for multiple LLM providers

---

## ⭐ Contributing

Contributions are welcome!

Feel free to fork the repository, create issues, and submit pull requests.

---

