"""Hugging Face Spaces Entry Point for तात्या (Tatya) — Marathi Search Engine.

Compatible with 100% Free Gradio SDK on Hugging Face Spaces.
Zero external dependencies required.
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Satisfy Hugging Face ZeroGPU runtime check if enabled on space
try:
    import spaces
    @spaces.GPU
    def init_spaces_gpu():
        return True
    init_spaces_gpu()
except Exception:
    pass

# Ensure database is uncompressed if only .gz is present
db_file = BASE_DIR / "marathi_web.db"
gz_file = BASE_DIR / "marathi_web.db.gz"

if not db_file.exists():
    parts = sorted(list(BASE_DIR.glob("marathi_web.db.gz.part_*")))
    if parts and not gz_file.exists():
        print(f"🧩 Reassembling {len(parts)} split database parts...")
        import shutil
        with open(gz_file, "wb") as f_out:
            for part in parts:
                with open(part, "rb") as f_in:
                    shutil.copyfileobj(f_in, f_out)
        print("✅ Archive assembled.")

    if gz_file.exists():
        print(f"📦 Extracting {gz_file.name} to {db_file.name}...")
        import gzip
        import shutil
        with gzip.open(gz_file, "rb") as f_in, open(db_file, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        print("✅ Database extraction complete.")

from praman.crawler.db import CrawlerDB
from praman.search.server import start_server

if __name__ == "__main__":
    # Hugging Face Spaces routes web traffic to port 7860
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 Starting तात्या (Tatya) on port {port}...")
    start_server(db_or_path=str(db_file), port=port)
