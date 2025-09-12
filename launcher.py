import os
import sys
import uvicorn


def main():
    # Ensure the package dir is on sys.path when PyInstaller bundles the app
    base = os.path.dirname(__file__)
    if base not in sys.path:
        sys.path.insert(0, base)

    try:
        import app.main as mod
        asgi_app = getattr(mod, 'app', None)
    except Exception as e:
        print('Error importing app.main:', e)
        asgi_app = None

    port = int(os.environ.get('PORT', os.environ.get('APP_PORT', '8000')))
    if asgi_app is None:
        # fallback to string notation
        uvicorn.run('app.main:app', host='127.0.0.1', port=port, log_level='info')
    else:
        uvicorn.run(asgi_app, host='127.0.0.1', port=port, log_level='info')


if __name__ == '__main__':
    main()
