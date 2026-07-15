import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.parse

API_BASE = "https://arknights.global/api"

def sanitize_folder_name(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

def download_file(url, filepath):
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        print(f"  Skipping {filepath} (already exists)")
        return
    print(f"  Downloading {url} -> {filepath}")
    try:
        urllib.request.urlretrieve(url, filepath)
    except Exception as e:
        print(f"  Failed to download {url}: {e}")

def get_yostar_opener():
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
    return opener

def list_online_comics():
    url = f"{API_BASE}/resource/comic/list?index=1&size=999"
    print(f"Fetching comic list from: {url} ...")
    try:
        opener = get_yostar_opener()
        with opener.open(url) as response:
            res = json.loads(response.read().decode('utf-8'))
            if res.get("code") == 0 and "data" in res:
                rows = res["data"].get("rows", [])
                print(f"\nFound {len(rows)} comics available:")
                for i, row in enumerate(rows, 1):
                    print(f"{i:2d}. {row.get('name')}")
            else:
                print("Error fetching comic list:", res.get("message"))
    except Exception as e:
        print("API Error:", e)

def download_comic_by_name(comic_name):
    # urlencode the name parameter
    params = {"index": 1, "size": 999, "name": comic_name}
    query_str = urllib.parse.urlencode(params)
    url = f"{API_BASE}/resource/comic/details?{query_str}"
    
    print(f"Fetching chapters for '{comic_name}' from: {url} ...")
    try:
        opener = get_yostar_opener()
        with opener.open(url) as response:
            res = json.loads(response.read().decode('utf-8'))
            if res.get("code") == 0 and "data" in res:
                rows = res["data"].get("rows", [])
                if not rows:
                    print(f"No chapters found for comic: '{comic_name}'")
                    return
                print(f"Found {len(rows)} chapters. Starting downloads...")
                
                # Setup installation of opener globally for urllib.request.urlretrieve
                urllib.request.install_opener(opener)
                
                for row in rows:
                    process_row(row)
            else:
                print("Error fetching comic details:", res.get("message"))
    except Exception as e:
        print("API Error:", e)

def process_row(row):
    details_name = row.get("detailsName", "ComicChapter")
    details_image = row.get("detailsImage")
    details_content = row.get("detailsContent", [])
    comic_describe = row.get("comicDescribe")

    # Group chapters under a parent folder named after the comic series name (sanitized)
    series_name = sanitize_folder_name(row.get("name", "ArknightsComics"))
    chapter_folder = sanitize_folder_name(details_name)
    
    output_dir = os.path.join(series_name, chapter_folder)
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nProcessing: {series_name} -> {details_name} (Saving to: {output_dir})")

    # Download detailsImage
    if details_image:
        parsed_detail = urllib.parse.urlparse(details_image)
        _, ext = os.path.splitext(parsed_detail.path)
        if not ext:
            ext = ".jpg"
        detail_filename = os.path.join(output_dir, f"detailsImage{ext}")
        download_file(details_image, detail_filename)

    # Write comicDescribe to txt file
    if comic_describe:
        desc_filename = os.path.join(output_dir, "comicDescribe.txt")
        try:
            with open(desc_filename, "w", encoding="utf-8") as f:
                f.write(comic_describe)
        except Exception as e:
            print(f"  Failed to write comicDescribe: {e}")

    # Download chapter content images
    for i, url in enumerate(details_content, 1):
        parsed = urllib.parse.urlparse(url)
        _, ext = os.path.splitext(parsed.path)
        if not ext:
            ext = ".jpg"
        
        filename = os.path.join(output_dir, f"{i}{ext}")
        download_file(url, filename)

def main():
    parser = argparse.ArgumentParser(description="Arknights Comic Downloader CLI Tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all available official comics online")
    group.add_argument("--download", help="Download an official comic series by its full name")
    group.add_argument("--file", help="Path to a local JSON file to parse and download")
    
    args = parser.parse_args()

    if args.list:
        list_online_comics()
    elif args.download:
        download_comic_by_name(args.download)
    elif args.file:
        if not os.path.exists(args.file):
            print(f"Error: File '{args.file}' not found.")
            sys.exit(1)
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error parsing JSON file: {e}")
            sys.exit(1)
            
        opener = get_yostar_opener()
        urllib.request.install_opener(opener)
        
        rows = []
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            if "data" in data and isinstance(data["data"], dict) and "rows" in data["data"]:
                rows = data["data"]["rows"]
            elif "rows" in data:
                rows = data["rows"]
            else:
                rows = [data]

        if not rows:
            print("No chapter rows found to process.")
            sys.exit(0)

        for row in rows:
            process_row(row)

if __name__ == "__main__":
    main()
