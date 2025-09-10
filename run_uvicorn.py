import os
import sys
import uvicorn
import importlib.util


def load_app_module():
    """Locate and load the application's main module.

    Tries (in order):
    - import app.main
    - import main
    - load app/main.py or main.py from this script's directory
    """
    try:
        import app.main as m
        return m
    import os
    import sys
    import uvicorn
    import importlib.util


    def load_app_module():
        """Locate and load the application's main module.

        Tries (in order):
        - import app.main
        - import main
        - load app/main.py or main.py from this script's directory
        """
        try:
            import app.main as m
            return m
        except Exception:
            pass

        try:
            import main as m
            return m
        except Exception:
            pass

        try:
            if getattr(sys, 'frozen', False):
                base = os.path.dirname(sys.executable)
            else:
                base = os.path.dirname(__file__)

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
        asgi_app = getattr(mod, 'app', None)
        if asgi_app is None:
            uvicorn.run('app.main:app', host='127.0.0.1', port=8000, log_level='info', reload=True)
        else:
            uvicorn.run(asgi_app, host='127.0.0.1', port=8000, log_level='info', reload=True)
    try:
