import subprocess
import sys

# === List of required packages with versions ===
packages = [
    "aiohttp==3.13.1",
    "cryptography==46.0.3",
    "eth_account==0.13.7",
    "eth_keys==0.7.0",
    "fastapi==0.121.0",
    "fastapi_mail==1.5.8",
    "passlib==1.7.4",
    "pycryptodome",
    "pydantic==2.12.3",
    "python-dotenv==1.2.1",
    "bcrypt>=4.0.1",
    "python_jose==3.5.0",
    "SQLAlchemy==2.0.44",
    "sqlmodel==0.0.27",
    "uvicorn==0.38.0",
    "eciespy==0.4.6",
    "asyncpg==0.30.0",
    "python-multipart",
    "mailjet_rest==1.5.1",
    "eciespy",
    "hypercorn==0.14.4"
    "deepace",
    "azure-identity",
    "azure-ai-vision-face"
]

def install(package):
    """Install a Python package using pip."""
    try:
        print(f"📦 Installing {package} ...")
        # Use sys.executable to ensure pip is from the correct virtual env
        # Using list for arguments is safer for subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Successfully installed {package}\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}\n")

if __name__ == "__main__":
    print("--- Starting package installation ---")
    for pkg in packages:
        install(pkg)
    print("--- All packages processed ---")
