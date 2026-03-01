# Public Frontend Deployment

This frontend is static and can be published to GitHub Pages or Vercel.

## GitHub Pages

- The workflow `.github/workflows/frontend-pages.yml` deploys `chatgpt/frontend/` on pushes to `main`.
- After deploy, open your pages URL and pass backend URL:
  - `https://<your-pages-domain>/?backend=https://<public-backend-domain>`

The UI stores the `backend` value in local storage for future visits.

## Vercel

- Import `chatgpt/frontend` as a static project.
- Keep `vercel.json` rewrites or set your backend URL in project config.
- Open deployed URL with:
  - `?backend=https://<public-backend-domain>`

## Notes

- WebSocket endpoint is derived automatically from the backend URL (`https` -> `wss`).
- Ensure CORS on backend allows your frontend domain.
- This frontend shows per-interaction model, latency, tokens, and grounding score metadata.

