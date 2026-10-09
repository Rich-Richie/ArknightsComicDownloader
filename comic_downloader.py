import os
import sys
import json
import re
import argparse
import time
import socket
import urllib.request
import urllib.parse
import urllib.error
import http.client

API_BASE = "https://arknights.global/api"

def sanitize_folder_name(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

def get_yostar_opener():
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
    return opener

def robust_api_request(url, retries=5, backoff_factor=2, timeout=15):
    attempt = 0
    wait = 1
    while True:
        try:
            opener = get_yostar_opener()
            with opener.open(url, timeout=timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            # Permanent client errors should not retry (e.g. 400, 404), unless it's 408 or 429
            if 400 <= e.code < 500 and e.code not in (408, 429):
                print(f"Permanent HTTP Error {e.code}: {e.reason}")
                raise e
            attempt += 1
            if attempt > retries:
                print(f"\n[Warning] Persistent HTTP Error {e.code} detected: {e.reason}")
                print("Waiting 10 seconds before retrying...")
                time.sleep(10)
                attempt = retries
                continue
            print(f"\n[Retry {attempt}/{retries}] HTTP Error {e.code}. Retrying in {wait}s...")
            time.sleep(wait)
            wait *= backoff_factor
        except (urllib.error.URLError, socket.timeout, ConnectionResetError, http.client.HTTPException) as e:
            attempt += 1
            if attempt > retries:
                print(f"\n[Warning] Network issue detected: {e}")
                print("Checking internet connection... Will retry in 10 seconds. (Press Ctrl+C to abort)")
                time.sleep(10)
                attempt = retries
                continue
            print(f"\n[Retry {attempt}/{retries}] Connection failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)
            wait *= backoff_factor

def download_file(url, filepath, retries=5, backoff_factor=2, timeout=15):
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        print(f"  Skipping {filepath} (already exists)")
        return

    temp_filepath = filepath + ".tmp"
    attempt = 0
    wait = 1
    opener = get_yostar_opener()
    
    while True:
        try:
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass
            
            with opener.open(url, timeout=timeout) as response:
                with open(temp_filepath, 'wb') as f:
                    while True:
                        chunk = response.read(16 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
            
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            os.rename(temp_filepath, filepath)
            print(f"  Successfully downloaded: {filepath}")
            return
            
        except urllib.error.HTTPError as e:
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass
            # Don't retry permanent client errors
            if 400 <= e.code < 500 and e.code not in (408, 429):
                print(f"  Permanent HTTP Error {e.code}: {e.reason}")
                return
            attempt += 1
            if attempt > retries:
                print(f"  [Warning] HTTP Error {e.code} on download: {e.reason}. Retrying in 10s...")
                time.sleep(10)
                attempt = retries
                continue
            print(f"  [Retry {attempt}/{retries}] HTTP Error {e.code}. Retrying in {wait}s...")
            time.sleep(wait)
            wait *= backoff_factor
            
        except Exception as e:
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass
            attempt += 1
            if attempt > retries:
                print(f"  [Warning] Network error on download: {e}. Retrying in 10s...")
                time.sleep(10)
                attempt = retries
                continue
            print(f"  [Retry {attempt}/{retries}] Download failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)
            wait *= backoff_factor

def list_online_comics():
    url = f"{API_BASE}/resource/comic/list?index=1&size=999"
    print(f"Fetching comic list from: {url} ...")
    try:
        res = robust_api_request(url)
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
    params = {"index": 1, "size": 999, "name": comic_name}
    query_str = urllib.parse.urlencode(params)
    url = f"{API_BASE}/resource/comic/details?{query_str}"
    
    print(f"Fetching chapters for '{comic_name}' from: {url} ...")
    try:
        res = robust_api_request(url)
        if res.get("code") == 0 and "data" in res:
            rows = res["data"].get("rows", [])
            if not rows:
                print(f"No chapters found for comic: '{comic_name}'")
                return
            print(f"Found {len(rows)} chapters. Starting downloads...")
            
            opener = get_yostar_opener()
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

    series_name = sanitize_folder_name(row.get("name", "ArknightsComics"))
    chapter_folder = sanitize_folder_name(details_name)
    
    output_dir = os.path.join(series_name, chapter_folder)
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nProcessing: {series_name} -> {details_name} (Saving to: {output_dir})")

    if details_image:
        images_to_download = []
        if isinstance(details_image, list):
            images_to_download = [img for img in details_image if isinstance(img, str) and img.strip()]
        elif isinstance(details_image, str) and details_image.strip():
            images_to_download = [details_image.strip()]

        for idx, img_url in enumerate(images_to_download):
            parsed_detail = urllib.parse.urlparse(img_url)
            _, ext = os.path.splitext(parsed_detail.path)
            if not ext:
                ext = ".jpg"
            suffix = f"_{idx + 1}" if len(images_to_download) > 1 else ""
            detail_filename = os.path.join(output_dir, f"detailsImage{suffix}{ext}")
            download_file(img_url, detail_filename)

    if comic_describe:
        desc_filename = os.path.join(output_dir, "comicDescribe.txt")
        try:
            with open(desc_filename, "w", encoding="utf-8") as f:
                f.write(comic_describe)
        except Exception as e:
            print(f"  Failed to write comicDescribe: {e}")

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
