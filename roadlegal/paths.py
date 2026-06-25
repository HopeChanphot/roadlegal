from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SEED_DIR = DATA_DIR / "seed"
RAW_DIR = DATA_DIR / "raw" / "downloads"
PROCESSED_DIR = DATA_DIR / "processed"
WEB_DIR = ROOT / "web"
MODELS_DIR = ROOT / "models"
FEEDBACK_LOG = DATA_DIR / "feedback.log"
