from fastmcp import FastMCP
import os
import aiosqlite
import asyncio
import tempfile
import json

# Use safe writable temporary directory
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")

# Handle __file__ safely
try:
    BASE_DIR = os.path.dirname(__file__)
except NameError:
    BASE_DIR = os.getcwd()

CATEGORIES_PATH = os.path.join(BASE_DIR, "categories.json")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")

# -------------------- INITIALIZATION --------------------

async def init_db():
    """Initialize the SQLite database asynchronously."""
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)
            # Test write access
            await db.execute("INSERT INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')")
            await db.execute("DELETE FROM expenses WHERE category = 'test'")
            await db.commit()
            print("✅ Database initialized successfully with write access")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        raise

# Run initialization synchronously at startup
asyncio.run(init_db())

# -------------------- MCP TOOLS --------------------

@mcp.tool()
async def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = "") -> dict:
    """Add a new expense entry to the database."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
                (date, amount, category, subcategory, note)
            )
            await db.commit()
            expense_id = cur.lastrowid
            return {"status": "success", "id": expense_id, "message": "Expense added successfully"}
    except aiosqlite.OperationalError as e:
        msg = str(e).lower()
        if "readonly" in msg:
            return {"status": "error", "message": "Database is read-only. Check file permissions."}
        return {"status": "error", "message": f"Database operational error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}


@mcp.tool()
async def list_expenses(start_date: str, end_date: str) -> dict:
    """List expense entries within an inclusive date range."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date)
            ) as cur:
                rows = await cur.fetchall()
                return {"status": "success", "expenses": [dict(row) for row in rows]}
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}


@mcp.tool()
async def summarize(start_date: str, end_date: str, category: str = None) -> dict:
    """Summarize expenses by category within an inclusive date range."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            query = """
                SELECT category, SUM(amount) AS total_amount, COUNT(*) as count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " GROUP BY category ORDER BY total_amount DESC"

            async with db.execute(query, params) as cur:
                rows = await cur.fetchall()
                return {"status": "success", "summary": [dict(row) for row in rows]}
    except Exception as e:
        return {"status": "error", "message": f"Error summarizing expenses: {str(e)}"}


@mcp.resource("expense://categories", mime_type="application/json")
async def categories() -> str:
    """Get available expense categories."""
    default_categories = {
        "categories": [
            "Food & Dining",
            "Transportation",
            "Shopping",
            "Entertainment",
            "Bills & Utilities",
            "Healthcare",
            "Travel",
            "Education",
            "Business",
            "Other"
        ]
    }

    try:
        if os.path.exists(CATEGORIES_PATH):
            async with await asyncio.to_thread(open, CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return await asyncio.to_thread(f.read)
        else:
            return json.dumps(default_categories, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Could not load categories: {str(e)}"})

# -------------------- SERVER ENTRY --------------------

if __name__ == "__main__":
    mcp.run(transport="http", port=8000)
