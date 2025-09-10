import subprocess,sys
try:
    import psutil
except Exception:
    psutil=None
out=[]
if psutil:
    for p in psutil.process_iter(['pid','name','cmdline']):
        try:
            cmd=' '.join(p.info.get('cmdline') or [])
            if 'uvicorn' in cmd or 'run_uvicorn.py' in cmd:
                out.append((p.info['pid'], p.info['name'], cmd))
        except Exception:
            pass
else:
    # fallback: use wmic
    try:
        res = subprocess.check_output(['wmic','process','get','ProcessId,CommandLine','/FORMAT:LIST'], stderr=subprocess.DEVNULL, text=True)
        blocks = [b for b in res.split('\n\n') if b.strip()]
        for b in blocks:
            lines = [l for l in b.splitlines() if l.strip()]
            cmd=''; pid=''
            for l in lines:
                if l.startswith('CommandLine='):
                    cmd=l.split('=',1)[1]
                if l.startswith('ProcessId='):
                    pid=l.split('=',1)[1]
            if 'uvicorn' in cmd or 'run_uvicorn.py' in cmd:
                out.append((pid,'process',cmd))
    except Exception as e:
        print('ERR',e,file=sys.stderr)

for o in out:
    print(o)
