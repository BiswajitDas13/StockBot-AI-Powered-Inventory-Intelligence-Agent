import os, json, re, logging
from typing import TypedDict, Annotated, Sequence
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator
import uvicorn

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_SERVER   = os.getenv("DB_SERVER", "DESKTOP-DM5OK69")
DB_NAME     = os.getenv("DB_NAME", "new")
DB_USER     = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "jitdas1234")

def get_engine():
    if DB_USER and DB_PASSWORD:
        conn_str = (
            f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}"
            "?driver=ODBC+Driver+17+for+SQL+Server"
        )
    else:
        conn_str = (
            f"mssql+pyodbc://@{DB_SERVER}/{DB_NAME}"
            "?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
        )
    return create_engine(conn_str, poolclass=NullPool, echo=False)

engine = get_engine()

@tool
def check_stock_by_item_id(item_id: int) -> str:
    """
    Query stock information for a specific item using its numeric Item ID.
    Returns item name, stock on hand. Use when user provides a numeric ID like 42672 or short code like 2001.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT TOP 5 [Item ID], [Item ID2], CAST([Stock On Hand] AS BIGINT) FROM store_data WHERE [Item ID] = :id"),
                {"id": item_id}
            ).fetchall()

            if not result:
                result = conn.execute(
                    text("SELECT TOP 5 [Item ID], [Item ID2], CAST([Stock On Hand] AS BIGINT) FROM store_data WHERE [Item ID2] LIKE :pattern"),
                    {"pattern": f"%{item_id}%"}
                ).fetchall()

        if not result:
            return json.dumps({"found": False, "message": f"No item found for ID {item_id}"})

        items = [{"item_id": r[0], "name": r[1], "stock": int(r[2] or 0)} for r in result]
        return json.dumps({"found": True, "items": items})
    except Exception as e:
        logger.error(f"DB error in check_stock_by_item_id: {e}")
        return json.dumps({"found": False, "message": f"Database error: {str(e)}"})


@tool
def check_stock_by_name(keyword: str) -> str:
    """
    Search stock items by name/brand keyword (e.g., 'iPhone', 'Samsung', 'Oppo', 'vivo', 'Nokia').
    Returns all matching items with their stock levels.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT TOP 10 [Item ID], [Item ID2], CAST([Stock On Hand] AS BIGINT) FROM store_data WHERE [Item ID2] LIKE :kw ORDER BY CAST([Stock On Hand] AS BIGINT) DESC"),
                {"kw": f"%{keyword}%"}
            ).fetchall()

        if not result:
            return json.dumps({"found": False, "message": f"No items found matching '{keyword}'"})

        items = [{"item_id": r[0], "name": r[1], "stock": int(r[2] or 0)} for r in result]
        total = sum(i["stock"] for i in items)
        return json.dumps({"found": True, "items": items, "total_stock": total, "count": len(items)})
    except Exception as e:
        logger.error(f"DB error in check_stock_by_name: {e}")
        return json.dumps({"found": False, "message": f"Database error: {str(e)}"})


@tool
def check_quantity_availability(item_id: int, quantity_needed: int) -> str:
    """
    Check if a specific quantity is available for an item.
    Returns whether quantity can be fulfilled and current stock level.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT TOP 3 [Item ID], [Item ID2], CAST([Stock On Hand] AS BIGINT) FROM store_data WHERE [Item ID] = :id OR [Item ID2] LIKE :pattern"),
                {"id": item_id, "pattern": f"%{item_id}%"}
            ).fetchall()

        if not result:
            return json.dumps({"found": False, "message": f"Item {item_id} not found"})

        r = result[0]
        stock = int(r[2] or 0)
        can_fulfill = stock >= quantity_needed
        shortage = max(0, quantity_needed - stock)

        return json.dumps({
            "found": True,
            "item_id": r[0],
            "name": r[1],
            "stock": stock,
            "requested": quantity_needed,
            "can_fulfill": can_fulfill,
            "shortage": shortage,
            "message": (
                f"Yes ✓ — {stock} pcs in stock, {quantity_needed} requested. Can fulfill."
                if can_fulfill else
                f"No ✗ — Only {stock} pcs available, {quantity_needed} requested. Short by {shortage} pcs."
            )
        })
    except Exception as e:
        logger.error(f"DB error in check_quantity_availability: {e}")
        return json.dumps({"found": False, "message": f"Database error: {str(e)}"})


@tool
def get_low_stock_items(threshold: int = 10) -> str:
    """
    Get all items with stock below a given threshold (default 10 units).
    Useful for inventory management queries.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT TOP 20 [Item ID], [Item ID2], CAST([Stock On Hand] AS BIGINT) FROM store_data WHERE CAST([Stock On Hand] AS BIGINT) <= :t AND CAST([Stock On Hand] AS BIGINT) >= 0 ORDER BY CAST([Stock On Hand] AS BIGINT) ASC"),
                {"t": threshold}
            ).fetchall()

        items = [{"item_id": r[0], "name": r[1], "stock": int(r[2] or 0)} for r in result]
        return json.dumps({"found": True, "items": items, "count": len(items), "threshold": threshold})
    except Exception as e:
        logger.error(f"DB error in get_low_stock_items: {e}")
        return json.dumps({"found": False, "message": f"Database error: {str(e)}"})


@tool
def get_all_brands_summary() -> str:
    """
    Get a summary of all brands and their total stock.
    Useful when user asks general inventory overview.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT 
                        CASE 
                            WHEN [Item ID2] LIKE '%vivo%' THEN 'Vivo/Android'
                            WHEN [Item ID2] LIKE '%Iphone%' OR [Item ID2] LIKE '%IOS%' OR [Item ID2] LIKE '%Apple%' THEN 'Apple iPhone'
                            WHEN [Item ID2] LIKE '%samsung%' OR [Item ID2] LIKE '%Galaxy%' THEN 'Samsung'
                            WHEN [Item ID2] LIKE '%Oppo%' THEN 'Oppo'
                            WHEN [Item ID2] LIKE '%Nokia%' OR [Item ID2] LIKE '%Lumia%' THEN 'Nokia'
                            WHEN [Item ID2] LIKE '%Xiaomi%' THEN 'Xiaomi'
                            WHEN [Item ID2] LIKE '%Motorola%' OR [Item ID2] LIKE '%Moto%' THEN 'Motorola'
                            WHEN [Item ID2] LIKE '%IQOO%' THEN 'IQOO'
                            WHEN [Item ID2] LIKE '%Nothing%' OR [Item ID2] LIKE '%CMF%' THEN 'Nothing/CMF'
                            ELSE 'Other'
                        END as brand,
                        COUNT(*) as total_models,
                        SUM(CAST([Stock On Hand] AS BIGINT)) as total_stock
                    FROM store_data
                    GROUP BY 
                        CASE 
                            WHEN [Item ID2] LIKE '%vivo%' THEN 'Vivo/Android'
                            WHEN [Item ID2] LIKE '%Iphone%' OR [Item ID2] LIKE '%IOS%' OR [Item ID2] LIKE '%Apple%' THEN 'Apple iPhone'
                            WHEN [Item ID2] LIKE '%samsung%' OR [Item ID2] LIKE '%Galaxy%' THEN 'Samsung'
                            WHEN [Item ID2] LIKE '%Oppo%' THEN 'Oppo'
                            WHEN [Item ID2] LIKE '%Nokia%' OR [Item ID2] LIKE '%Lumia%' THEN 'Nokia'
                            WHEN [Item ID2] LIKE '%Xiaomi%' THEN 'Xiaomi'
                            WHEN [Item ID2] LIKE '%Motorola%' OR [Item ID2] LIKE '%Moto%' THEN 'Motorola'
                            WHEN [Item ID2] LIKE '%IQOO%' THEN 'IQOO'
                            WHEN [Item ID2] LIKE '%Nothing%' OR [Item ID2] LIKE '%CMF%' THEN 'Nothing/CMF'
                            ELSE 'Other'
                        END
                    ORDER BY SUM(CAST([Stock On Hand] AS BIGINT)) DESC
                """)
            ).fetchall()

        brands = [{"brand": r[0], "total_models": r[1], "total_stock": int(r[2] or 0)} for r in result]
        return json.dumps({"found": True, "brands": brands})
    except Exception as e:
        logger.error(f"DB error in get_all_brands_summary: {e}")
        return json.dumps({"found": False, "message": f"Database error: {str(e)}"})

tools = [
    check_stock_by_item_id,
    check_stock_by_name,
    check_quantity_availability,
    get_low_stock_items,
    get_all_brands_summary,
]

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
)

llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are a smart, helpful stock assistant for a mobile phone inventory business.

Your job is to help users check stock levels, query item availability, and understand inventory data.

IMPORTANT RULES:
1. Users often send messages in HINGLISH (Hindi + English mix). Understand them:
   - "pcs chahiye" = pieces needed
   - "block karo" = reserve/block stock
   - "bhej do" = send it / dispatch
   - "hai kya" = is it available?
   - "kitna" = how much/many
   - "nos" = numbers/pieces
   - "box" = box (quantity unit)
   - "urgent" = urgent request
   - "stock confirm" = confirm stock availability

2. Item IDs: Users often say short codes like "2001", "2003" etc which are part of item names (e.g., "Android2001 vivo"). 
   Always search by both the full numeric ID and as a name keyword.

3. When asked about quantity (e.g., "2001 50 pcs?"), ALWAYS check if that quantity is available.

4. Be concise but informative. Format responses clearly with stock numbers.

5. If a user's message is not about stock/inventory, politely redirect them.

6. Always use the appropriate tool to get REAL data from the database. Never guess stock numbers.

Available brands in inventory: Vivo, Apple iPhone, Samsung Galaxy, Oppo, Nokia/Lumia, Xiaomi, Motorola, IQOO, Nothing/CMF.
"""

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


def should_continue(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def call_model(state: AgentState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


tool_node = ToolNode(tools)

graph_builder = StateGraph(AgentState)
graph_builder.add_node("agent", call_model)
graph_builder.add_node("tools", tool_node)
graph_builder.set_entry_point("agent")
graph_builder.add_conditional_edges("agent", should_continue)
graph_builder.add_edge("tools", "agent")

agent_graph = graph_builder.compile()

conversation_store: dict[str, list[BaseMessage]] = {}

def get_conversation(session_id: str) -> list[BaseMessage]:
    return conversation_store.get(session_id, [])


def sanitize_history(messages: list[BaseMessage]) -> list[BaseMessage]:
    """
    Strip ToolMessage and intermediate AIMessage-with-tool_calls so the replayed
    history never contains a 'tool' role without a preceding 'tool_calls' message.
    Only HumanMessages and final AIMessages (no pending tool calls) are kept.
    """
    clean: list[BaseMessage] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            clean.append(msg)
        elif isinstance(msg, AIMessage):
            if not (hasattr(msg, "tool_calls") and msg.tool_calls):
                clean.append(msg)
        # ToolMessage intentionally dropped
    return clean[-20:]


def save_conversation(session_id: str, messages: list[BaseMessage]):
    conversation_store[session_id] = sanitize_history(list(messages))

app = FastAPI(
    title="Stock Chat Bot API",
    description="Agentic AI chat for inventory using LangGraph + GPT-4o-mini",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    tool_calls_made: list[str] = []


@app.get("/")
def root():
    return {"status": "running", "app": "Stock Chat Bot", "model": "gpt-4o-mini"}


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    return {"status": "ok", "database": db_status}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        history = get_conversation(req.session_id)
        history.append(HumanMessage(content=req.message))

        result = await agent_graph.ainvoke({"messages": history})

        all_messages = result["messages"]

        reply = ""
        tool_calls_made = []
        for msg in reversed(all_messages):
            if isinstance(msg, AIMessage) and msg.content:
                reply = msg.content
                break

        for msg in all_messages:
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
                for tc in (msg.tool_calls or []):
                    tool_calls_made.append(tc["name"])

        save_conversation(req.session_id, all_messages)

        return ChatResponse(
            reply=reply or "Sorry, I couldn't process that request.",
            session_id=req.session_id,
            tool_calls_made=list(set(tool_calls_made))
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat/{session_id}")
def clear_session(session_id: str):
    conversation_store.pop(session_id, None)
    return {"message": f"Session {session_id} cleared"}


@app.get("/inventory/summary")
async def inventory_summary():
    """Quick inventory summary endpoint"""
    try:
        with engine.connect() as conn:
            total_items  = conn.execute(text("SELECT COUNT(*) FROM store_data")).scalar()
            total_stock  = conn.execute(text("SELECT SUM(CAST([Stock On Hand] AS BIGINT)) FROM store_data")).scalar()
            out_of_stock = conn.execute(text("SELECT COUNT(*) FROM store_data WHERE CAST([Stock On Hand] AS BIGINT) = 0")).scalar()
            low_stock    = conn.execute(text("SELECT COUNT(*) FROM store_data WHERE CAST([Stock On Hand] AS BIGINT) > 0 AND CAST([Stock On Hand] AS BIGINT) <= 10")).scalar()
        return {
            "total_items":    total_items,
            "total_stock":    int(total_stock or 0),
            "out_of_stock":   out_of_stock,
            "low_stock_items": low_stock
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)


