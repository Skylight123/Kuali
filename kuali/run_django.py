import os
import sys
from decouple import RepositoryEnv
from daphne.cli import CommandLineInterface

def load_env():
    """
    Load .env file baik saat jalan normal (python run_django.py)
    maupun saat dibundle jadi PyInstaller exe.
    """
    if getattr(sys, 'frozen', False):
        # Kalau jalan dari PyInstaller exe
        base_path = os.path.dirname(sys.executable)
        env_candidates = [
            os.path.join(base_path, ".env"),
            os.path.join(os.path.dirname(base_path), ".env"),
            os.path.join(getattr(sys, "_MEIPASS", base_path), ".env"),
        ]
    else:
        # Kalau jalan dari source code biasa, .env ada di root project.
        app_path = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.dirname(app_path)
        env_candidates = [
            os.path.join(base_path, ".env"),
            os.path.join(app_path, ".env"),
        ]

    env_path = next((path for path in env_candidates if os.path.exists(path)), None)

    if env_path:
        env_repository = RepositoryEnv(env_path)
        for key, value in env_repository.data.items():
            os.environ[key] = value  # inject ke environment
        print(f"[INFO] Loaded environment from {env_path}")
    else:
        print(f"[WARNING] .env file not found. Checked: {', '.join(env_candidates)}")
        
if __name__ == "__main__":
    # Change working directory to the project root
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Add the project directory to Python's import path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

    # Load environment
    load_env()
    
    # Set Django settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projects.settings")

    bind_host = os.environ.get("DJANGO_BIND_HOST", "127.0.0.1")
    bind_port = os.environ.get("DJANGO_BIND_PORT", "3020")
    asgi_path = os.environ.get("DJANGO_ASGI_PATH", "projects.asgi:application")

    sys.argv = [
        "daphne",
        "-b",
        bind_host,
        "-p",
        str(bind_port),
        asgi_path,
    ]
    CommandLineInterface.entrypoint()
