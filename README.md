# Listenr Backend

FastAPI backend for the Listenr music logging and discovery platform.

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # Windows
   # or: source venv/bin/activate  # macOS/Linux
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and adjust as needed.

4. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

5. (Optional) Seed development data:
   ```bash
   python -m scripts.seed.py
   # Login: demo@listenr.com / demo123
   ```

6. (Optional) Seed albums with **real cover art** from MusicBrainz + iTunes:
   ```bash
   python -m scripts.seed_albums --clear --count 100
   ```

   **Album seeding options** (run from `backend/`):

   | Command | Description |
   |---------|-------------|
   | `python -m scripts.seed_albums` | Seed 100 albums (default) |
   | `python -m scripts.seed_albums --clear --count 200` | Clear existing, seed 200 albums |
   | `python -m scripts.seed_albums -g jazz --count 50` | 50 jazz albums |
   | `python -m scripts.seed_albums -g rock -n 75` | 75 rock albums |
   | `python -m scripts.seed_albums -g "hip hop" -n 30` | 30 hip hop albums |
   | `python -m scripts.seed_albums -g electronic` | 100 electronic albums |
   | `python -m scripts.seed_albums -g classical -n 25` | 25 classical albums |
   | `python -m scripts.seed_albums -a "Taylor Swift" -n 20` | 20 albums by Taylor Swift |
   | `python -m scripts.seed_albums -a "The Beatles" --clear -n 15` | Clear & seed 15 Beatles albums |
   | `python -m scripts.seed_albums -a "Drake" -n 10` | 10 Drake albums |
   | `python -m scripts.seed_albums -c US -n 50` | 50 albums from USA |
   | `python -m scripts.seed_albums -c GB` | 100 albums from UK |
   | `python -m scripts.seed_albums -g soul -c US` | Soul albums from USA |
   | `python -m scripts.seed_albums -g jazz -c JP -n 20` | 20 Japanese jazz albums |
   | `python -m scripts.seed_albums -b 25` | Smaller batches (25 per API call) |

   Flags: `-n/--count` albums, `-g/--genre`, `-a/--artist`, `-c/--country`, `-b/--batch`, `--clear`

7. **Backfill covers** for existing albums with placeholder images:
   ```bash
   python -m scripts.backfill_covers
   ```

8. **Backfill descriptions** (Wikipedia intro) for albums without one:
   ```bash
   python -m scripts.backfill_descriptions
   ```

9. **Backfill diary** (if you have reviews but empty diary):
   ```bash
   python -m scripts.backfill_diary
   ```

The API will be available at `http://127.0.0.1:8000`. Docs at `/docs`.

## Deploy to Railway

1. Create a [Railway](https://railway.app) project and add a **PostgreSQL** service.
2. Add a new service from your GitHub repo (or use `railway up` from the CLI).
3. Set the **root directory** to `backend` if deploying from the monorepo.
4. Railway will auto-detect `railway.json` and use it for the start command and health check.
5. Add the PostgreSQL service as a reference to your backend service—Railway injects `DATABASE_URL` automatically.
6. Set `JWT_SECRET` (and optionally `GEMINI_API_KEY`) in Variables. Use a strong random secret in production.
7. Generate a domain in **Networking** to make the API publicly accessible.

Tables are created automatically on first start via `init_db()`.

## API Endpoints

All routes are under `/api/v1`.

| Section | Endpoints |
|---------|-----------|
| **Auth** | register, login, refresh, logout, me, spotify, apple (OAuth stubs) |
| **Users** | get profile, favorites, update, follow/unfollow, following, recommended |
| **Albums** | search, get, trending, by-genre, create, ratings-distribution, reviews |
| **Reviews** | create, feed, get, update, delete, like, comments |
| **Diary** | get, create, update, delete, export |
| **Lists** | get, create, update, delete, add/remove albums, like |
| **Explore** | trending, popular-with-friends, genres, ai-discovery |
| **AI** | discovery, album-insight, polish-review |
| **Search** | global (albums, users) |
| **Notifications** | get, mark read, mark all read |
| **Integrations** | spotify/apple import, status |

## Project Structure

```
backend/
├── app/
│   ├── main.py         # FastAPI app
│   ├── config.py       # Settings
│   ├── database.py     # DB session
│   ├── routes/         # API route modules
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic (auth, AI)
│   └── middleware/     # Auth dependency
├── scripts/
│   ├── seed.py             # Basic dev seed
│   ├── seed_albums.py      # MusicBrainz albums (covers, descriptions)
│   ├── backfill_covers.py  # Fetch missing album art
│   ├── backfill_descriptions.py  # Fetch missing descriptions
│   └── backfill_diary.py         # Create diary entries from existing reviews
├── requirements.txt
└── .env.example
```
