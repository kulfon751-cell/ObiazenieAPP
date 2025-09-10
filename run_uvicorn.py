import os
import sys
import uvicorn


def load_app_module():
    # Try standard import first
    try:
        import app.main as m
        return m
    except Exception:
        pass

    # Try importing top-level main (when PyInstaller flattens modules)
    try:
        import main as m
        return m
    except Exception:
        pass

    # As a last resort, try loading main.py by path. When frozen, sys.executable
    # points to the exe; otherwise use this file's dir.
    try:
        import importlib.util
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(__file__)

        # look for app/main.py or main.py
        candidates = [os.path.join(base, 'app', 'main.py'), os.path.join(base, 'main.py')]
        for p in candidates:
            if os.path.exists(p):
                spec = importlib.util.spec_from_file_location('main_from_path', p)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
    except Exception:
        pass

    raise ImportError('Could not locate app.main or main module')


if __name__ == '__main__':
    mod = load_app_module()
    # expect the ASGI app instance to be named `app` inside module
    asgi_app = getattr(mod, 'app', None)
    if asgi_app is None:
        # fallback to string notation if available
        uvicorn.run('app.main:app', host='127.0.0.1', port=8000, log_level='info')
    else:
        uvicorn.run(asgi_app, host='127.0.0.1', port=8000, log_level='info')
