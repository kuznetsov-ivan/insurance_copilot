# Demo Script

## Setup
1. Run `uv run uvicorn insurance_copilot.app:app --reload`.
2. Open `http://127.0.0.1:8000`.
3. Confirm the UI shows claim intake, observer console, and SMS panel.

## Walkthrough (5-7 minutes)
1. Pick **Flat battery, drivable** scenario.
2. Click **Process Transcript** to extract fields.
3. Point out missing fields and next prompt behavior.
4. Click **Evaluate Claim** and explain:
   - coverage status,
   - recommended repair van dispatch,
   - generated SMS update,
   - observer console transparency.
5. Reset and run **Engine failure, not drivable** to show tow flow.
6. Reset and run **Out of coverage** to show manual review escalation path.

## Talking Points
- This prototype focuses on functional workflow over UI polish.
- Decision logic is deterministic and auditable by design.
- Service boundaries are ready for replacing rules with LLM components.
- First production release should remain human-in-the-loop.
