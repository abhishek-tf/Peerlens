<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# PeerLens Frontend

This frontend uploads a PDF to the backend orchestrator and displays extraction + agent review results.

## Run Locally

Prerequisites:
- Node.js
- Extraction API running on port `8000`
- Methodology agent running on port `8001`
- Orchestrator running on port `8080`

Steps:
1. Install dependencies:
   `npm install`
2. Optional: create `.env.local` and set backend URL if different from localhost:
   `VITE_ORCHESTRATOR_URL=http://localhost:8080`
3. Run frontend:
   `npm run dev`

## Backend flow used by the UI

Frontend upload -> `POST /api/v1/full-review` (orchestrator) -> extraction service -> agent services -> aggregated result returned to dashboard.
