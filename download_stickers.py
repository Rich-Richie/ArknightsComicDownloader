import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm
from urllib.parse import urlparse

# Constants
API_URL = "https://arknights.global/api/resource/stickers/list"
OUTPUT_DIR = "stickers"
BATCH_SIZE = 50

def get_session():
    """Create a requests session with retry logic for network interruptions."""
    session = requests.Session()
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
    """Remove invalid characters for Windows filenames/folders."""
    return re.sub(r'[\\/*?:"<>|]', '_', filename).strip()

def get_extension(url):
    """Extract extension from URL, defaulting to .png if not found."""
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1]
    if not ext:
        return ".png"
    return ext

def extract_original_filename(url):
    """Extract the original basename from the URL."""
    parsed = urlparse(url)
    basename = os.path.basename(parsed.path)
    if not basename:
        return "unknown"
    return basename

def extract_url(image_field):
    """Helper to extract a single URL if it's in a list or string."""
    if isinstance(image_field, list):
        if not image_field:
            return None
        return image_field[0]
    return image_field

def fetch_all_stickers(session):
    """Fetch the metadata for all stickers handling pagination."""
    all_stickers = []
    index = 1
    
    print("Fetching sticker metadata from API...")
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
                
            all_stickers.extend(rows)
            
            total_count = data.get("data", {}).get("count", 0)
            if len(all_stickers) >= total_count:
                break
                
            index += 1
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch metadata at index {index}: {e}")
            break
            
    print(f"Found {len(all_stickers)} sticker sets to process.")
    return all_stickers

def download_file(session, url, filepath):
    """Downloads a file if it doesn't already exist."""
    if not url:
        return False
        
    if os.path.exists(filepath):
        return True
        
    try:
        response = session.get(url, stream=True, timeout=15)
        response.raise_for_status()
        
        temp_filepath = filepath + ".tmp"
        with open(temp_filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    
        os.rename(temp_filepath, filepath)
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"\nNetwork error downloading {filepath}: {e}")
        if os.path.exists(filepath + ".tmp"):
            os.remove(filepath + ".tmp")
        return False
    except Exception as e:
        print(f"\nUnexpected error downloading {filepath}: {e}")
        if os.path.exists(filepath + ".tmp"):
            os.remove(filepath + ".tmp")
        return False

def process_sticker_set(session, sticker_set):
    """Process and download a single sticker set."""
    wid = sticker_set.get("id")
    title = sticker_set.get("title", "Untitled")
    
    safe_title = sanitize_filename(title)
    set_folder = os.path.join(OUTPUT_DIR, f"{wid} - {safe_title}")
    
    if not os.path.exists(set_folder):
        os.makedirs(set_folder)
        
    # Download Thumbnail
    thumb_url = extract_url(sticker_set.get("smallImage")) or extract_url(sticker_set.get("smallImageM"))
    if thumb_url:
        ext = get_extension(thumb_url)
        thumb_path = os.path.join(set_folder, f"thumbnail{ext}")
        download_file(session, thumb_url, thumb_path)
        
    # Process Stickers
    images = sticker_set.get("image", [])
    if isinstance(images, str):
        images = [images]
        
    mapping_lines = []
    
    for i, img_url in enumerate(images, 1):
        if not img_url:
            continue
            
        ext = get_extension(img_url)
        seq_name = f"sticker_{i:02d}{ext}"
        original_name = extract_original_filename(img_url)
        
        mapping_lines.append(f"{seq_name} -> {original_name}")
        
        filepath = os.path.join(set_folder, seq_name)
        download_file(session, img_url, filepath)
        
    # Save mapping file
    if mapping_lines:
        mapping_path = os.path.join(set_folder, "original_names.txt")
        with open(mapping_path, "w", encoding="utf-8") as f:
            f.write("Sequential Name -> Original Filename\n")
            f.write("=" * 40 + "\n")
            f.write("\n".join(mapping_lines))

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    session = get_session()
    stickers = fetch_all_stickers(session)
    
    if not stickers:
        print("No sticker sets found or failed to fetch metadata.")
        return
        
    print(f"Downloading stickers to '{OUTPUT_DIR}' directory...")
    
    with tqdm(total=len(stickers), desc="Downloading Sets", unit="set") as pbar:
        for s in stickers:
            process_sticker_set(session, s)
            pbar.update(1)
            
    print(f"\nFinished! Processed {len(stickers)} sticker sets.")

if __name__ == "__main__":
    main()
