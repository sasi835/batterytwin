"""Validate saved artifacts before launching Streamlit; never train at startup."""
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from api.services import BatteryService
from src.utils.config import ROOT

BatteryService(Path(os.environ.get('BATTERYTWIN_MODEL_DIR',str(ROOT/'models'))))
print('BatteryTwin saved artifacts validated; starting Streamlit.',flush=True)
os.execv(sys.executable,[sys.executable,'-m','streamlit','run',str(ROOT/'streamlit_app.py'),
                        '--server.address','0.0.0.0','--server.port',os.environ.get('PORT','7860')])
