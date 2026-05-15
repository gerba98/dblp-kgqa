from pathlib import Path

import gdown

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REQUIRED_SUBDIRS = ("dblp_quad", "dblp_schema")

# Google Drive folder ID. Replace with your own.
DRIVE_FOLDER_ID = "1ziMWqe1RkERwEQRotKWYfushMp5bE998"


def is_populated(path: Path) -> bool:
    return path.is_dir() and any(path.iterdir())


def main() -> None:
    if all(is_populated(DATA_DIR / sub) for sub in REQUIRED_SUBDIRS):
        print(f"data/ already populated at {DATA_DIR}, skipping download.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading data folder from Google Drive...")
    gdown.download_folder(
        url=f"https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}",
        output=str(DATA_DIR),
    )
    print("Done.")


if __name__ == "__main__":
    main()
