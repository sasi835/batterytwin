"""Publish an explicit runtime allowlist using the authenticated Hugging Face account."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from huggingface_hub import HfApi
from src.utils.config import ROOT
from scripts.prepare_space import stage

def publish(repo_id,update=False):
    api=HfApi()
    account=api.whoami()['name']
    if not update and repo_id.split('/')[0]!=account:
        raise ValueError(f'Target must belong to signed-in account {account}; organization publishing requires explicit workflow.')
    if update:
        api.space_info(repo_id)
        api.auth_check(repo_id,repo_type='space',write=True)
    folder=stage()
    manifest=json.loads((ROOT/'artifacts/results/space_manifest.json').read_text())
    url=(f'https://huggingface.co/spaces/{repo_id}' if update else
         api.create_repo(repo_id,repo_type='space',space_sdk='docker',private=False))
    print(f'Space repository ready: {url}',flush=True)
    commit=api.upload_folder(repo_id=repo_id,repo_type='space',folder_path=folder,
        allow_patterns=manifest['files'],commit_message='Deploy BatteryTwin Streamlit dashboard in Docker')
    info=api.space_info(repo_id)
    record={'repo_id':repo_id,'repository_url':str(url),'commit':commit.oid,'commit_url':commit.commit_url,
            'sdk':info.sdk,'runtime_stage':str(api.get_space_runtime(repo_id).stage),
            'publication':'Uploaded; live build and browser verification pending','file_count':len(manifest['files'])}
    (ROOT/'artifacts/results/huggingface_deployment.json').write_text(json.dumps(record,indent=2),encoding='utf8')
    print(json.dumps(record,indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',required=True)
    parser.add_argument('--update',action='store_true',help='Update an explicitly named existing BatteryTwin Space')
    args=parser.parse_args()
    publish(args.repo,args.update)
