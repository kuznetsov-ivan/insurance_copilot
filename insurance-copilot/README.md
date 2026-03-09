# Insurance Co-Pilot Prototype

Single-app `uv` project that demonstrates a roadside assistance insurance co-pilot workflow:
- voice-like conversation intake (browser speech API + manual fallback),
- structured claim extraction,
- policy coverage decision,
- next-best action dispatch recommendation,
- fake SMS customer updates,
- observer console for human auditability.

## Run

```bash
uv sync
uv run uvicorn insurance_copilot.app:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Test

```bash
uv run pytest
```

## Repository Layout

- `src/insurance_copilot/app.py`: FastAPI app entrypoint
- `src/insurance_copilot/routes/`: web and API routes
- `src/insurance_copilot/services/`: extraction, coverage, dispatch, notification logic
- `src/insurance_copilot/data/`: synthetic fixtures
- `src/insurance_copilot/templates/`: demo page
- `src/insurance_copilot/static/`: JS/CSS frontend assets
- `docs/prd.md`: concise PRD
- `docs/demo-script.md`: interview walkthrough script
- `tests/`: API and service tests
