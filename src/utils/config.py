from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]

def load_config() -> dict:
    """Read the versioned project configuration."""
    return yaml.safe_load((ROOT / 'configs/config.yaml').read_text())
