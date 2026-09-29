# Customer Support Ticketing CRM

A small web app for managing customer support tickets. You can create tickets, search and filter them, open a ticket to see the details, and update its status or add notes.

Built with FastAPI, SQLite and plain HTML/CSS/JS.

## Run locally

```
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open http://localhost:8000. The database file is created automatically on first run.

Copy `.env.example` to `.env` if you want to change where the database file is stored (`DB_PATH`).

## API

- `POST /api/tickets` creates a ticket. Body: `customer_name`, `customer_email`, `subject`, `description`
- `GET /api/tickets` lists tickets. Optional query params: `status`, `search`, `limit` (default 20, max 100), `offset`
- `GET /api/tickets/{ticket_id}` returns one ticket with its notes
- `PUT /api/tickets/{ticket_id}` updates the status and optionally adds a note. Body: `status`, `notes`
- `DELETE /api/tickets/{ticket_id}` deletes a ticket and its notes

## Deploy

Works on Railway or Render. Start command:

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

The free tiers reset the disk on redeploy, so set `DB_PATH` to a path on a mounted volume if you want tickets to survive.
