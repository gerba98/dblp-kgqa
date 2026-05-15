import subprocess
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
DUMP_DIR = SCRIPT_DIR / "dump"
DUMP_FILE = DUMP_DIR / "dblp.nt.gz"
DUMP_URL = "https://zenodo.org/api/records/7638511/files/dblp.nt.gz/content"
CONTAINER_NAME = "dblp-dump-virtuoso-1"


def isql(sql: str) -> None:
    subprocess.run(
        ["docker", "exec", "-i", CONTAINER_NAME,
         "isql", "-U", "dba", "-P", "admin", f"exec={sql}"],
        check=True,
    )


def download_dump() -> None:
    if DUMP_FILE.exists():
        print("0. DBLP dump already present, skipping download.")
        return
    print("0. Downloading DBLP dump from Zenodo...")
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    with requests.get(DUMP_URL, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with DUMP_FILE.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    print("   Download complete.")


def main() -> None:
    download_dump()

    print("1. Registering the directory...")
    isql("ld_dir ('/import', '*.gz', 'https://dblp.org');")

    print("2. Starting the data load (this might take a while)...")
    isql("rdf_loader_run();")

    print("3. Saving to disk (checkpoint)...")
    isql("checkpoint;")

    print("4. Checking the status...")
    isql("select * from DB.DBA.load_list;")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(f"isql command failed: {e}")
