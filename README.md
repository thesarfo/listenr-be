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