"""Produce a self-contained submission archive without virtual environments or secrets."""
from pathlib import Path
import os
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
output=ROOT/'output/BatteryTwin_CAT_II.zip'
excluded={'.venv','node_modules','.git','__pycache__','.pytest_cache','tmp','huggingface-space'}
with ZipFile(output,'w',ZIP_DEFLATED,compresslevel=6) as archive:
    for directory,dirs,files in os.walk(ROOT):
        dirs[:]=sorted(name for name in dirs if name not in excluded)
        for name in sorted(files):
            path=Path(directory)/name
            relative=path.relative_to(ROOT)
            if path.suffix=='.zip' or path.name=='.env' or path.suffix=='.part':
                continue
            archive.write(path,'BatteryTwin/'+relative.as_posix())
with ZipFile(output) as archive:
    bad=archive.testzip()
    if bad:
        raise RuntimeError(f'Archive verification failed: {bad}')
    print(f'Archive: {output} ({len(archive.namelist())} files, {output.stat().st_size/1024/1024:.1f} MiB)')
