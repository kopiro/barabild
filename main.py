from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
import requests
from bs4 import BeautifulSoup
import urllib.parse
import os
import hashlib
import json
from datetime import datetime, timedelta

app = FastAPI(title="BaraBild Images Search API")

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
    return os.path.join(CACHE_DIR, f"{query_hash}.html")

def save_to_cache(query: str, html_content: str):
    """Save HTML content to cache"""
    ensure_cache_dir()
    cache_path = get_cache_path(query)
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "html": html_content
    }
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False)

def load_from_cache(query: str) -> str:
    """Load HTML content from cache if available and not expired"""
    cache_path = get_cache_path(query)
    if not os.path.exists(cache_path):
        return None
        
    with open(cache_path, 'r', encoding='utf-8') as f:
        cache_data = json.load(f)
        
    # Check if cache is expired
    cache_time = datetime.fromisoformat(cache_data["timestamp"])
    if datetime.now() - cache_time > CACHE_EXPIRY:
        os.remove(cache_path)  # Remove expired cache
        return None
        
    return cache_data["html"]

def parse_html_for_image(html_content: str):
    """Parse HTML content to extract image information"""
    soup = BeautifulSoup(html_content, 'lxml')
    images = soup.find_all('picture')
    image = images[0]
    link = image.find('img')['src'] # Get Image Url
    return link

@app.get("/")
async def root():
    return {"message": "Welcome to BaraBild Images Search API"}

@app.get("/search/{query}")
async def search_image(query: str):
    """
    Search for an image on Getty Images website and return the first result's URL
    """
    # Check cache first
    cached_html = load_from_cache(query)
    
    if cached_html:
        # Parse the cached HTML
        try:
            result = parse_html_for_image(cached_html)
            return RedirectResponse(url=result)
        except HTTPException:
            # If parsing fails, we'll fetch fresh data
            pass
    
    # Encode the query for URL
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://www.gettyimages.com/search/2/image?phrase={encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        # Save the raw HTML to cache
        save_to_cache(query, response.text)
        
        # Parse the HTML to extract image information
        result = parse_html_for_image(response.text)
        
        return RedirectResponse(result)
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching image: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 