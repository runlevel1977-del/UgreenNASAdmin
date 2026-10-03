"""Read-only release checks and export of committed public sources."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
import subprocess

PUBLIC_REPOSITORY = 'https://github.com/runlevel1977-del/UgreenNASAdmin.git'

RUNTIME_NAMES = frozenset({
    'app_settings.json','nas_admin_connection.json','telegram_notify.json',
    'nas_watch_local.json','nas_daily_report_local.json','qnap_smb_prefs.json',
    'ssh_known_hosts.json','ugos_tls_certs.json','transfer_log.txt','transfer.log',
    'last_github_update_check.txt','last_github_update_prompt.txt','.env',
})


def runtime_name(name):
    lower = name.lower()
    return any(lower == item or lower.startswith(item + '.') for item in RUNTIME_NAMES) or lower.startswith('release_ed25519_private')
SOURCE_ROOTS = frozenset({'ugreen_app','tools','packaging','installer','assets','docs','tests'})
SOURCE_FILES = frozenset({'ugreen_nas_admin.py','nas_ssh.py','nas_utils.py',
                         'requirements.txt','LICENSE','README.md','CHANGELOG.md'})


def git_bytes(root, *args):
    return subprocess.run(['git','-C',str(root),*args],capture_output=True,check=True).stdout


def release_source_state(root, version):
    commit=git_bytes(root,'rev-parse','HEAD').decode().strip()
    if git_bytes(root,'status','--porcelain','--untracked-files=no').strip():
        raise ValueError('Release sources contain uncommitted tracked changes')
    tag='v'+version
    exists=subprocess.run(['git','-C',str(root),'show-ref','--verify','--quiet','refs/tags/'+tag],capture_output=True)
    if exists.returncode not in (0,1):
        raise ValueError('Cannot inspect release tag')
    if exists.returncode == 0:
        target=git_bytes(root,'rev-parse','refs/tags/'+tag+'^{commit}').decode().strip()
        if target != commit:
            raise ValueError('Release tag does not point to the source commit')
    return {'source_commit':commit,'version':version,'tag':tag,'tag_exists':exists.returncode==0}


def public_release_state(root, version):
    """Require the actual public tag, including peeled annotated tags, before publishing."""
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Invalid release version')
    state = release_source_state(root, version)
    if not state['tag_exists']:
        raise ValueError('Create and publish the reviewed release tag before packaging/signing')
    ref = 'refs/tags/' + state['tag']
    result = subprocess.run(['git', 'ls-remote', PUBLIC_REPOSITORY, ref, ref + '^{}'],
                            capture_output=True, check=True, timeout=30)
    refs = {}
    for line in result.stdout.decode('ascii').splitlines():
        sha, name = line.split()
        if name not in (ref, ref + '^{}') or name in refs or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', sha):
            raise ValueError('Invalid public tag response')
        refs[name] = sha
    if ref not in refs or refs.get(ref + '^{}', refs[ref]) != state['source_commit']:
        raise ValueError('Public release tag does not identify this source commit; private-only commits cannot be release provenance')
    return state


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Read-only check of local source and public release tag; no fetch or tag changes')
    parser.add_argument('version')
    arguments = parser.parse_args()
    print(json.dumps(public_release_state(Path(__file__).resolve().parents[1], arguments.version), indent=2))


def reject_runtime_files(directory):
    for path in Path(directory).rglob('*'):
        if path.is_symlink():
            raise ValueError('Release tree contains a symbolic link: '+str(path.relative_to(directory)))
        if runtime_name(path.name):
            raise ValueError('Release tree contains local runtime/secret data: '+str(path.relative_to(directory)))


def export_committed_sources(root, destination, state):
    entries=git_bytes(root,'ls-tree','-rz',state['source_commit']).split(b'\0')
    hashes={}
    for entry in entries:
        if not entry:
            continue
        meta,raw_path=entry.split(b'\t',1)
        mode,kind,oid=meta.decode().split()
        relative=PurePosixPath(raw_path.decode('utf-8'))
        if relative.parts[0] not in SOURCE_ROOTS and str(relative) not in SOURCE_FILES:
            continue
        if relative.is_absolute() or '..' in relative.parts or '\\' in str(relative) or ':' in str(relative):
            raise ValueError('Invalid source path')
        if kind != 'blob' or mode not in ('100644','100755'):
            raise ValueError('Non-regular source entry: '+str(relative))
        if runtime_name(relative.name):
            raise ValueError('Tracked runtime settings cannot be published')
        content=git_bytes(root,'cat-file','blob',oid)
        target=Path(destination).joinpath(*relative.parts)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(content)
        hashes[str(relative)]=hashlib.sha256(content).hexdigest()
    manifest=dict(state,source_sha256=hashes,
                  provenance='Committed source export; does not attest to binary reproducibility')
    (Path(destination)/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest
