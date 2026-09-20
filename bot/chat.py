import os
import json
from groq import Groq
from dotenv import load_dotenv

from bot.tools import (
    get_movie_details,
    get_trending_movies,
    search_movies_by_genre
)

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)


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


def chat_with_bot(messages: list) -> str:
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
        messages.append({"role": "assistant", "content": answer})
        return answer
    
    answer = msg.content
    messages.append({"role": "assistant", "content": answer})
    return answer


def get_system_message():
    return {"role": "system", "content": SYSTEM_PROMPT}