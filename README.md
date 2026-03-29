# 📦 StockBot — AI-Powered Inventory Intelligence Agent

**Built with FastAPI • LangGraph • LangChain • OpenAI GPT-4o-mini • SQL Server**

---

## 🚀 Overview

StockBot is a Generative AI–powered inventory chatbot designed for mobile phone retail businesses to query real-time stock data using natural language — including **Hinglish** (Hindi + English mix).

The system connects securely to a Microsoft SQL Server database, understands trade-specific queries like *"2001 50 pcs hai kya?"* or *"Samsung stock kitna hai?"*, and uses an agentic LangGraph reasoning loop to fetch and return accurate, live inventory data.

This project demonstrates real-world integration of Large Language Models (LLMs) with relational databases, agentic tool-use, and scalable web application development.

---

## 🏗️ System Architecture

The application follows a modular and scalable architecture with clear separation of responsibilities.

### 1. FastAPI Backend
- Handles all HTTP routing and business logic
- Exposes `/chat`, `/health`, and `/inventory/summary` endpoints
- Session-aware conversation management with automatic history sanitization

### 2. LangGraph Agentic Loop
- Uses a `StateGraph` with a ReAct-style agent node and a tool execution node
- The agent autonomously decides which database tool to invoke based on user intent
- Multi-turn conversation context is preserved across messages

### 3. LangChain + GPT-4o-mini (LLM Layer)
- Understands natural language queries in English and Hinglish
- Translates user intent into structured tool calls
- Generates clear, human-readable stock responses

### 4. Tool Layer (Database Functions)
- **check_stock_by_item_id** → Query by numeric Item ID
- **check_stock_by_name** → Search by brand or model keyword
- **check_quantity_availability** → Check if a quantity can be fulfilled
- **get_low_stock_items** → List items below a stock threshold
- **get_all_brands_summary** → Brand-wise aggregate stock overview

### 5. SQL Server Database
- Stores all inventory data in a `store_data` table
- Queried in real time via SQLAlchemy + pyodbc
- Supports Item ID, Item Name/Code, and Stock On Hand fields

### 6. Frontend Chat UI
- Single-file dark-themed chat interface (`index.html`)
- Live inventory snapshot sidebar (Total SKUs, Total Units, Out-of-Stock, Low Stock)
- Quick-query shortcut buttons and Hinglish-aware chip suggestions

---

## 🔄 How the Agent Works

User queries often vary in format, language, and intent.  
To handle this, StockBot uses a **LangGraph ReAct agentic loop**.

### Step 1: User Message
- The user sends a message in English or Hinglish
- The session history is retrieved and the new message is appended

### Step 2: Agent Node (GPT-4o-mini)
- The LLM reads the full conversation context and the system prompt
- It decides which tool to call and with what parameters

### Step 3: Tool Node (Database Execution)
- The selected tool queries SQL Server and returns structured JSON data
- Results are passed back to the agent for interpretation

### Step 4: Final Response
- The agent generates a clear, human-readable reply with stock figures
- Tool call badges are displayed in the UI so users know what was queried

This loop repeats until the agent produces a final answer with no further tool calls.

---

## 🗣️ Hinglish Support

StockBot is built specifically for the Indian mobile phone trade market and understands common trade phrases:

| Hinglish Phrase | Meaning |
|---|---|
| `hai kya` | Is it available? |
| `kitna` | How much / How many |
| `pcs chahiye` | Pieces needed |
| `stock kitna hai` | How much stock is there? |
| `block karo` | Reserve / block the stock |
| `bhej do` | Send it / dispatch |
| `urgent` | Urgent request |
| `nos` | Numbers / pieces |
| `stock confirm` | Confirm stock availability |

---

## 🤖 Why GPT-4o-mini?

- Strong tool-use and function-calling performance
- Cost-efficient compared to larger models
- Handles code-mixed Hinglish language accurately
- Fast response times suitable for real-time inventory queries
- Ideal for structured data retrieval in business workflows

---

## 🔐 Security & Configuration

- API keys stored using environment variables (`.env`)
- No hardcoded credentials in source code
- Database credentials injected at runtime via `python-dotenv`
- CORS middleware configurable for production restriction
- Recommended: use a read-only DB user in production

---

## ✨ Key Features

- Agentic AI loop powered by LangGraph StateGraph
- Hinglish natural language understanding
- Real-time SQL Server inventory queries
- Quantity fulfillment checks (can we fulfill X units?)
- Low stock alerts with configurable threshold
- Brand-wise aggregate stock summary
- Multi-turn session-aware conversation
- Live inventory dashboard in the chat UI
- Quick-query shortcut buttons for common checks
- Single-file frontend — no build step required

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Backend Framework | FastAPI + Uvicorn |
| AI Agent | LangGraph (StateGraph) |
| LLM Framework | LangChain |
| Model | OpenAI GPT-4o-mini |
| Database | Microsoft SQL Server |
| DB Driver | SQLAlchemy + pyodbc |
| Frontend | Vanilla HTML / CSS / JS |
| Environment | Python-dotenv |

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- Microsoft SQL Server with ODBC Driver 17
- OpenAI API Key

### 1. Clone the Repository
```bash
git clone https://github.com/BiswajitDas13/StockBot.git
cd StockBot
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your_openai_api_key_here
DB_SERVER=YOUR_SQL_SERVER_NAME
DB_NAME=your_database_name
DB_USER=your_db_username
DB_PASSWORD=your_db_password
```

### 5. Run the Backend
```bash
python app.py
```

### 6. Open the Frontend

Open `index.html` directly in your browser — no build step required.

---

## 📈 Scalability & Extensibility

The system clearly separates:
- Agent reasoning logic
- Database tool execution
- API routing layer
- Frontend rendering

This makes it easy to extend with:
- WhatsApp or Telegram bot integration
- Docker containerization
- Multi-user authentication
- Stock write-back and restock alerts
- Cloud deployment (Azure / AWS / GCP)

---

## 📌 Conclusion

StockBot demonstrates a practical, end-to-end implementation of a Generative AI agent integrated with a live relational database and a real-world business workflow.

By combining FastAPI, LangGraph, LangChain, GPT-4o-mini, and SQL Server, the system delivers Hinglish-aware natural language understanding, real-time inventory queries, agentic tool-use reasoning, and a clean production-ready chat interface.

This project highlights how modern LLM systems can be integrated into business operations using modular design, secure configuration, and agentic decision-making strategies.
