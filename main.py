from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
import requests
import os
import hashlib
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="BaraBild Images Search API")

# Unsplash API configuration
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
if not UNSPLASH_ACCESS_KEY:
    raise ValueError("UNSPLASH_ACCESS_KEY environment variable is required")

# Cache configuration
CACHE_DIR = "./cache"
CACHE_EXPIRY = timedelta(hours=24)  # Cache expires after 24 hours

def ensure_cache_dir():
    """Ensure the cache directory exists"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def get_cache_path(query: str) -> str:
    """Generate a cache file path for a query"""
    # Create a hash of the query to use as filename
    query_hash = hashlib.md5(query.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{query_hash}.json")

def save_to_cache(query: str, data: dict):
    """Save API response to cache"""
    ensure_cache_dir()
    cache_path = get_cache_path(query)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def load_from_cache(query: str) -> dict:
    """Load API response from cache if available and not expired"""
    cache_path = get_cache_path(query)
    if not os.path.exists(cache_path):
        return None
        
    # Check if cache is expired using file modification time
    mtime = os.path.getmtime(cache_path)
    if datetime.now().timestamp() - mtime > CACHE_EXPIRY.total_seconds():
        os.remove(cache_path)  # Remove expired cache
        return None
        
    with open(cache_path, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"\n[{datetime.now()}] {request.method} {request.url}")
    response = await call_next(request)
    return response

@app.get("/")
async def root():
    return {"message": "Welcome to BaraBild Images Search API"}

@app.get("/search/{query}")
async def search_image(query: str):
    """
    Search for a random image on Unsplash based on the query
    """
    # Check cache first
    cached_data = load_from_cache(query)
    if cached_data and cached_data.get("urls", {}).get("regular"):
        return RedirectResponse(url=cached_data["urls"]["regular"])
    
    try:
        response = requests.get(
            "https://api.unsplash.com/photos/random",
            params={
                "query": query,
                "client_id": UNSPLASH_ACCESS_KEY
            },
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        if not data.get("urls", {}).get("regular"):
            raise HTTPException(status_code=404, detail="No image found")
        
        # Save to cache
        save_to_cache(query, data)
            
        return RedirectResponse(url=data["urls"]["regular"])
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching image: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 