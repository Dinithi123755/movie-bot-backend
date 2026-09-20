import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OMDB_KEY = os.getenv("OMDB_API_KEY")
TMDB_KEY = os.getenv("TMDB_API_KEY")


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