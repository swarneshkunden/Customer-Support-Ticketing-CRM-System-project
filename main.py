import os
import sqlite3
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_PATH = os.getenv("DB_PATH", "tickets.db")

app = FastAPI()


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


with db() as con:
    con.executescript("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id),
            note_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)


class NewTicket(BaseModel):
    customer_name: str
    customer_email: str
    subject: str
    description: str


class TicketUpdate(BaseModel):
    status: Literal["Open", "In Progress", "Closed"]
    notes: str = ""


@app.post("/api/tickets", status_code=201)
def create_ticket(t: NewTicket):
    created = now()
    with db() as con:
        cur = con.execute(
            "INSERT INTO tickets (customer_name, customer_email, subject, description, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 'Open', ?, ?)",
            (t.customer_name, t.customer_email, t.subject, t.description, created, created),
        )
        ticket_id = f"TKT-{cur.lastrowid:03d}"
        con.execute("UPDATE tickets SET ticket_id = ? WHERE id = ?", (ticket_id, cur.lastrowid))
    return {"ticket_id": ticket_id, "created_at": created}


@app.get("/api/tickets")
def list_tickets(status: str = "", search: str = "", limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    sql = "SELECT ticket_id, customer_name, subject, status, created_at FROM tickets WHERE 1=1"
    args = []
    if status:
        sql += " AND status = ?"
        args.append(status)
    if search:
        sql += " AND (customer_name LIKE ? OR ticket_id LIKE ? OR customer_email LIKE ? OR description LIKE ?)"
        args += [f"%{search}%"] * 4
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    args += [limit, offset]
    with db() as con:
        return [dict(r) for r in con.execute(sql, args)]


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    with db() as con:
        row = con.execute(
            "SELECT ticket_id, customer_name, customer_email, subject, description, status, created_at, updated_at "
            "FROM tickets WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Ticket not found")
        notes = con.execute(
            "SELECT note_text, created_at FROM notes WHERE ticket_id = ? ORDER BY id DESC", (ticket_id,)
        ).fetchall()
    return {**dict(row), "notes": [dict(n) for n in notes]}


@app.put("/api/tickets/{ticket_id}")
def update_ticket(ticket_id: str, u: TicketUpdate):
    ts = now()
    with db() as con:
        cur = con.execute(
            "UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?", (u.status, ts, ticket_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Ticket not found")
        if u.notes.strip():
            con.execute(
                "INSERT INTO notes (ticket_id, note_text, created_at) VALUES (?, ?, ?)",
                (ticket_id, u.notes.strip(), ts),
            )
    return {"success": True, "updated_at": ts}


@app.delete("/api/tickets/{ticket_id}")
def delete_ticket(ticket_id: str):
    with db() as con:
        cur = con.execute("DELETE FROM tickets WHERE ticket_id = ?", (ticket_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Ticket not found")
        con.execute("DELETE FROM notes WHERE ticket_id = ?", (ticket_id,))
    return {"success": True}


app.mount("/", StaticFiles(directory="static", html=True))
