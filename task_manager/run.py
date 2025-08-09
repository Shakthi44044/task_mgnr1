try:
    from .app import create_app  # package context
except ImportError:  # pragma: no cover
    from app import create_app  # fallback when run directly

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)