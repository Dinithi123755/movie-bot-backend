import os
import json
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ============================================
# CONFIG
# ============================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OMDB_KEY = os.getenv("OMDB_API_KEY")
TMDB_KEY = os.getenv("TMDB_API_KEY")

client = Groq(api_key=GROQ_API_KEY)
MODEL = "openai/gpt-oss-20b"

# ============================================
# FASTAPI APP
# ============================================
app = FastAPI(title="Movie Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# MODELS
# ============================================
class ChatRequest(BaseModel):
    message: str
    history: list = []


# ============================================
# TOOLS (OMDb + TMDB)
# ============================================
def get_movie_details(movie_name: str) -> dict:
    url = f"https://www.omdbapi.com/?t={movie_name}&apikey={OMDB_KEY}&plot=full"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        if data.get("Response") == "True":
            return {
                "success": True,
                "data": {
                    "title": data.get("Title"),
                    "year": data.get("Year"),
                    "genre": data.get("Genre"),
                    "director": data.get("Director"),
                    "actors": data.get("Actors"),
                    "plot": data.get("Plot"),
                    "imdb_rating": data.get("imdbRating"),
                    "awards": data.get("Awards"),
                }
            }
        return {"success": False, "error": data.get("Error", "Not found")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_trending_movies() -> dict:
    url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={TMDB_KEY}"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        movies = [
            {
                "title": m.get("title"),
                "year": m.get("release_date", "")[:4],
                "rating": m.get("vote_average"),
                "overview": m.get("overview", "")[:120]
            }
            for m in data.get("results", [])[:5]
        ]
        return {"success": True, "data": movies}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_movies_by_genre(genre_name: str, year: str = "2024") -> dict:
    genre_map = {
        "action": 28, "comedy": 35, "horror": 27, "sci-fi": 878,
        "science fiction": 878, "romance": 10749, "thriller": 53,
        "animation": 16, "drama": 18, "fantasy": 14
    }
    genre_id = genre_map.get(genre_name.lower().strip(), 878)
    url = (
        f"https://api.themoviedb.org/3/discover/movie?"
        f"api_key={TMDB_KEY}&with_genres={genre_id}"
        f"&primary_release_year={year}&sort_by=vote_average.desc&vote_count.gte=100"
    )
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        movies = [
            {
                "title": m.get("title"),
                "rating": m.get("vote_average"),
                "overview": m.get("overview", "")[:120]
            }
            for m in data.get("results", [])[:5]
        ]
        return {"success": True, "data": movies}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================
# GROQ TOOLS
# ============================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_movie_details",
            "description": "Get details about a specific movie (plot, actors, rating).",
            "parameters": {
                "type": "object",
                "properties": {"movie_name": {"type": "string"}},
                "required": ["movie_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_trending_movies",
            "description": "Get today's trending movies.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_movies_by_genre",
            "description": "Search top-rated movies by genre and year.",
            "parameters": {
                "type": "object",
                "properties": {
                    "genre_name": {"type": "string"},
                    "year": {"type": "string"}
                },
                "required": ["genre_name"]
            }
        }
    }
]

AVAILABLE_FUNCTIONS = {
    "get_movie_details": get_movie_details,
    "get_trending_movies": get_trending_movies,
    "search_movies_by_genre": search_movies_by_genre
}

SYSTEM_PROMPT = """You are 🎬 Movie Info Bot. Respond in user's language (Sinhala/English).
Use tools to get accurate info. Format with emojis."""


# ============================================
# API ENDPOINTS
# ============================================
@app.get("/")
def root():
    return {"status": "ok", "message": "Movie Bot API is running!"}


@app.post("/chat")
def chat(request: ChatRequest):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(request.history)
    messages.append({"role": "user", "content": request.message})
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1200
        )
        
        msg = response.choices[0].message
        
        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                fn = tc.function.name
                args = json.loads(tc.function.arguments)
                result = AVAILABLE_FUNCTIONS[fn](**args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": fn,
                    "content": json.dumps(result)
                })
            
            final = client.chat.completions.create(
                model=MODEL, messages=messages, temperature=0.7, max_tokens=1200
            )
            answer = final.choices[0].message.content
        else:
            answer = msg.content
        
        return {"success": True, "reply": answer}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)