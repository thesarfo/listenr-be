"""AI service - Gemini API proxy."""
from app.config import settings


def discovery(query: str) -> str:
    """Vibe-based album suggestions."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key or "")
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"""You are a music discovery guru. A user is looking for music with this vibe: "{query}". Suggest 3 distinct albums with a brief 1-sentence explanation for each. Format nicely."""
        resp = model.generate_content(prompt)
        return resp.text or ""
    except Exception as e:
        return f"AI unavailable: {e}"


def album_insight(album_title: str, artist: str) -> str:
    """Generate a short "about" description for an album."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key or "")
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = f"""Write a 2–3 sentence "About" description for the album "{album_title}" by {artist}. Cover the sound, themes, and why it matters. Tone: knowledgeable but accessible, like a music critic's intro."""
        resp = model.generate_content(prompt)
        return resp.text.strip() if resp.text else ""
    except Exception as e:
        return f"AI unavailable: {e}"


def polish_review(content: str) -> str:
    """Polish rough notes into a review."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key or "")
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = 'You are a world-class music critic. Transform these rough notes into a polished, insightful album review. Keep it around 100 words. Rough notes: "' + content + '"'
        resp = model.generate_content(prompt)
        return resp.text.strip() if resp.text else ""
    except Exception as e:
        return f"AI unavailable: {e}"
