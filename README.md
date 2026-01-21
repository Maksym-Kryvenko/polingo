# Language Learning App
Author: Maksym Kryvenko

## Overview
Polingo is a minimalist Polish vocabulary trainer for beginners. The web experience lets you curate a personal deck of the most common Polish words (with English or Ukrainian translations) and immediately switch into structured translation or writing practice. Every manually entered word is validated against the curated database so you catch typos before they become study liabilities.

## Features
- **Language-set toggle:** Switch between Polish ↔ English and Polish ↔ Ukrainian study sets before practice.
- **Manual validation:** The backend endpoint `/api/words/check` confirms each hand-typed entry, identifies which language field matched, and rejects inputs that do not yet exist in the database.
- **Starter deck:** Load the first 10 seeded words to practice immediately without typing anything.
- **Practice modes:** Choose translation (read Polish, write the translation) or writing (read the translation, write Polish) for targeted drills.
- **Progress tracking:** A dedicated `practice_record` table stores every attempt so daily and overall accuracy can be computed. The top-right stats pill shows today’s percentage, the trend vs. yesterday, and the overall correct-answer percentage.

### Flow
1. Either validate a manually entered word or import the starter list.
2. Lock the selection once the deck feels right.
3. Choose translation or writing mode.
4. Respond to prompts and submit; every answer updates today’s score instantly.

## Technology
- **Frontend:** React with Vite (ESM module build)
- **Backend:** FastAPI + SQLModel + SQLite
- **Database:** Local SQLite file seeded with the 100 most common Polish words plus their English and Ukrainian counterparts
- **Runtime:** Docker Compose (frontend + backend services)

## Installation
### Backend setup
```bash
cd backend-app
python -m pip install -r requirements.txt
uvicorn main:app --reload
```
FastAPI serves the `/api` surface, seeds the vocabulary if the database is empty, and exposes `/words/initial`, `/words/check`, `/practice/submit`, and `/stats`.

### Frontend setup
```bash
cd frontend-app
npm install
npm run dev
```
The Vite app hits the backend base URL defined by `VITE_API_BASE_URL` (defaults to `http://localhost:8000/api`). The UI includes the manual validation flow, word preview, practice controls, and the stats pill.

### Docker
```bash
docker compose up --build
```
The Docker Compose file builds separate frontend and backend images and exposes ports `5173` (Vite) and `8000` (FastAPI). The frontend container injects `VITE_API_BASE_URL=http://backend:8000/api` so it can reach the backend within the shared network.

## Usage
1. Enter a word/phrase in the manual input field and click **Validate & add**; the UI will show whether the word exists and which column matched.
2. Alternatively, click **Load starter set** to pull the first ten words from the database.
3. When the deck contains the vocabulary you want, select either **Translation practice** or **Writing practice** and answer the prompt.
4. Every submission records the result and refreshes the daily/overall percentages shown in the top-right pill.

## Contributing
Pull requests should update the seed list, enhance practice logic, or add new practice modalities. Run the backend tests (`uvicorn` endpoints) and `npm run build` for the frontend before submitting changes.

## License
TDB
