"""Produce a self-contained submission archive without virtual environments or secrets."""
from pathlib import Path
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
output=ROOT/'output/BatteryTwin_CAT_II.zip'
excluded={'scripts/build_lab_record.py','scripts/build_editable_lab_record.py',
          'output/pdf/BatteryTwin_IEEE_Report.pdf'}
files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
files=sorted(name for name in files if name and name not in excluded)
for required in ['SUBMISSION.md','report/BatteryTwin_IEEE_Project_Report_SriRam_Sasi.pdf',
                 'report/BatteryTwin_IEEE_Project_Report_SriRam_Sasi.docx']:
    if required not in files or not (ROOT/required).is_file():
        raise RuntimeError(f'Missing tracked deliverable: {required}')
output=ROOT/'output/BatteryTwin_CAT_II_Submission.zip'
with ZipFile(output,'w',ZIP_DEFLATED,compresslevel=6) as archive:
    for name in files:
        archive.write(ROOT/name,'BatteryTwin/'+name)
with ZipFile(output) as archive:
    bad=archive.testzip()
    if bad:
        raise RuntimeError(f'Archive verification failed: {bad}')
    print(f'Archive: {output} ({len(archive.namelist())} files, {output.stat().st_size/1024/1024:.1f} MiB)')
