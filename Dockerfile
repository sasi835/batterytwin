FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=7860 HOME=/home/battery MPLCONFIGDIR=/tmp/matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 battery
WORKDIR /home/battery/app
COPY requirements-runtime.txt requirements-streamlit.txt ./
RUN pip install --no-cache-dir torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r requirements-streamlit.txt
COPY --chown=battery:battery api/ api/
COPY --chown=battery:battery src/ src/
COPY --chown=battery:battery configs/ configs/
COPY --chown=battery:battery models/ models/
COPY --chown=battery:battery data/processed/ data/processed/
COPY --chown=battery:battery artifacts/plots/ artifacts/plots/
COPY --chown=battery:battery artifacts/results/ artifacts/results/
COPY --chown=battery:battery output/pdf/BatteryTwin_IEEE_Report.pdf output/pdf/BatteryTwin_IEEE_Report.pdf
COPY --chown=battery:battery .streamlit/ .streamlit/
COPY --chown=battery:battery streamlit_app.py ./
COPY --chown=battery:battery scripts/container_start.py scripts/smoke_inference.py scripts/
USER battery
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','7860')+'/_stcore/health')"
CMD ["python", "-u", "scripts/container_start.py"]
