# ArknightsComicDownloader
Download comics from Arknights.global automatically.

## Features
The script can figure out what comics are available or not.

## Prerequisites
You need **Python 3** installed on your system. The script uses only built-in standard Python libraries (`urllib`, `json`, `argparse`, `re`, `os`, `sys`), so **no external packages or dependencies are required**.

## Usage Guide

Run the script using `python downloader.py` with one of the following arguments:

### 1. List Available Comics Online

Query the live API to retrieve the exact titles of all official comics currently available to download:

```powershell
python downloader.py --list
```

**Example Output:**
```text
Fetching comic list from: https://arknights.global/api/resource/comic/list?index=1&size=999 ...

Found 14 comics available:
 1. Elite Operator: Departure
 2. Sui's Daily Slices: Mundane Mortal Life
 3. Prelude Suite: Blood Diamond
 ...
```

---

### 2. Download a Comic Series by Name

Download all chapters, covers, descriptions, and pages of a specific comic series by passing its full title inside quotes:

```powershell
python downloader.py --download "<Comic Name>"
```

**Examples:**

```powershell
# Download the Departure series
python downloader.py --download "Elite Operator: Departure"

# Download Sui's Daily Slices
python downloader.py --download "Sui's Daily Slices: Wanna Shoot a Picture?"
```

---

### 3. Parse and Download from a Local JSON File

If you have pre-saved JSON response data (e.g., from network inspection or API dumps), you can feed it directly:

```powershell
python downloader.py --file path/to/file.json
```

---

## Output Folder Structure

Downloads are organized inside folders named after the sanitized series name and chapter title:

```text
ArknightsComicDownloader/
├── Elite Operator_ Departure/               <-- Series Folder
│   ├── Departure - Episode 01/              <-- Chapter Folder
│   │   ├── detailsImage.png                 <-- Cover/Details Image
│   │   ├── comicDescribe.txt                <-- Summary Text
│   │   ├── 1.png                            <-- Page 1
│   │   ├── 2.jpeg                           <-- Page 2
│   │   └── ...
│   └── Departure - Episode 02/
│       ├── detailsImage.png
│       ├── comicDescribe.txt
│       └── ...
└── downloader.py
```
