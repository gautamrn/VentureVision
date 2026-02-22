# Directory Tree

.
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI entry
│   │   ├── graph/              # LangGraph Workflow & State
│   │   ├── nodes/              # Agent Logic (planner, scout, critic, writer)
│   │   └── schemas/            # Pydantic Models
│   └── tests/                  # Logic validation
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js Routes
│   │   ├── components/         # High-density UI (Dashboard, Feed, Memo)
│   │   └── lib/                # API Client & Zod Schemas
├── CLAUDE.md
├── spec.md
├── tech-stack.md
└── .gitignore