import hashlib
import tempfile
import zipfile
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REQUIRED_SUBDIRS = ("dblp_quad", "dblp_schema")

# Zenodo record with data.zip (DOI: 10.5281/zenodo.23991429).
ZENODO_RECORD_ID = "23991429"
DATA_URL = (
    f"https://zenodo.org/api/records/{ZENODO_RECORD_ID}/files/data.zip/content"
)
DATA_MD5 = "4a276c3f8b590a994368f2ca32d68da8"


def is_populated(path: Path) -> bool:
    return path.is_dir() and any(path.iterdir())


def download(url: str, dest: Path, expected_md5: str) -> None:
    md5 = hashlib.md5(usedforsecurity=False)
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        with dest.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                md5.update(chunk)
                done += len(chunk)
                if total:
                    print(
                        f"\r  {done / 1e6:.0f} / {total / 1e6:.0f} MB",
                        end="",
                        flush=True,
                    )
    print()
    if md5.hexdigest() != expected_md5:
        raise RuntimeError(
            f"Checksum mismatch for {url}: "
            f"expected {expected_md5}, got {md5.hexdigest()}"
        )


def extract(archive: Path, root: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            if not name.startswith("data/") or ".." in Path(name).parts:
                raise RuntimeError(f"Unexpected path in archive: {name}")
        zf.extractall(root)


def main() -> None:
    if all(is_populated(DATA_DIR / sub) for sub in REQUIRED_SUBDIRS):
        print(f"data/ already populated at {DATA_DIR}, skipping download.")
        return

    print(f"Downloading data.zip from Zenodo (record {ZENODO_RECORD_ID})...")
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "data.zip"
        download(DATA_URL, archive, DATA_MD5)
        print("Extracting...")
        extract(archive, PROJECT_ROOT)
    print("Done.")


if __name__ == "__main__":
    main()
