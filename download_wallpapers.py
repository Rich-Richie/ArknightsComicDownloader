import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm
from urllib.parse import urlparse

# Constants
API_URL = "https://arknights.global/api/resource/gallery/list"
OUTPUT_DIR = "wallpapers"
BATCH_SIZE = 50

def get_session():
    """Create a requests session with retry logic for network interruptions."""
    session = requests.Session()
    # Retry on specific status codes or connection errors
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def sanitize_filename(filename):
    """Remove invalid characters for Windows filenames."""
    # Replace invalid chars with underscore
    return re.sub(r'[\\/*?:"<>|]', '_', filename).strip()

def get_extension(url):
    """Extract extension from URL, defaulting to .png if not found."""
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1]
    if not ext:
        return ".png"
    return ext

def fetch_all_wallpapers(session):
    """Fetch the metadata for all wallpapers handling pagination."""
    all_wallpapers = []
    index = 1
    
    print("Fetching wallpaper metadata from API...")
    while True:
        try:
            response = session.get(API_URL, params={"index": index, "size": BATCH_SIZE}, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                print(f"API Error: {data.get('message')}")
                break
                
            rows = data.get("data", {}).get("rows", [])
            if not rows:
                break
                
            all_wallpapers.extend(rows)
            
            # Check if we have fetched all of them
            total_count = data.get("data", {}).get("count", 0)
            if len(all_wallpapers) >= total_count:
                break
                
            index += 1
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch metadata at index {index}: {e}")
            break
            
    print(f"Found {len(all_wallpapers)} wallpapers to process.")
    return all_wallpapers

def download_wallpaper(session, wallpaper):
    """Download a single wallpaper if it doesn't already exist."""
    wid = wallpaper.get("id")
    title = wallpaper.get("title", "Untitled")
    image_url = wallpaper.get("image1")
    
    if isinstance(image_url, list):
        if not image_url:
            return False
        image_url = image_url[0]
        
    if not image_url:
        return False
        
    safe_title = sanitize_filename(title)
    ext = get_extension(image_url)
    filename = f"{wid} - {safe_title}{ext}"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # Check if file already exists
    if os.path.exists(filepath):
        # We assume if the file exists, it's fully downloaded. 
        return True
        
    # Download with retries
    try:
        response = session.get(image_url, stream=True, timeout=15)
        response.raise_for_status()
        
        # Write to a temporary file first, then rename, to avoid partial downloads on interruption
        temp_filepath = filepath + ".tmp"
        with open(temp_filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    
        os.rename(temp_filepath, filepath)
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"\nNetwork error downloading {filename}: {e}")
        # Clean up partial temp file
        if os.path.exists(filepath + ".tmp"):
            os.remove(filepath + ".tmp")
        return False
    except Exception as e:
        print(f"\nUnexpected error downloading {filename}: {e}")
        if os.path.exists(filepath + ".tmp"):
            os.remove(filepath + ".tmp")
        return False

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    session = get_session()
    wallpapers = fetch_all_wallpapers(session)
    
    if not wallpapers:
        print("No wallpapers found or failed to fetch metadata.")
        return
        
    print(f"Downloading wallpapers to '{OUTPUT_DIR}' directory...")
    
    success_count = 0
    artists_info = []
    
    with tqdm(total=len(wallpapers), desc="Downloading", unit="img") as pbar:
        for wp in wallpapers:
            title = wp.get("title", "Untitled")
            author = wp.get("author", "Unknown")
            wid = wp.get("id")
            
            # Store artist and artwork mapping
            artists_info.append(f"ID: {wid} | Artwork: {title} | Artist: {author}")
            
            if download_wallpaper(session, wp):
                success_count += 1
            pbar.update(1)
            
    # Save the artists and artworks to a text file
    txt_path = os.path.join(OUTPUT_DIR, "artists_and_artworks.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Arknights Wallpapers - Artists and Artworks\n")
        f.write("=" * 45 + "\n\n")
        f.write("\n".join(artists_info))
        
    print(f"\nCreated artist info list at '{txt_path}'")
    print(f"Finished! Successfully processed {success_count}/{len(wallpapers)} wallpapers.")

if __name__ == "__main__":
    main()
