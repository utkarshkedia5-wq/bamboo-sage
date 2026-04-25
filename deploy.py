"""
deploy.py — Upload generated demo pages to hosting
===================================================
Supports:
  - Vercel (recommended, free tier works)
  - AWS S3 + CloudFront
  - Local dev server

Usage:
    python deploy.py --provider vercel
    python deploy.py --provider s3
    python deploy.py --provider local
"""

import os
import sys
import subprocess
from pathlib import Path
import json

OUTPUT_DIR = Path("output")


def deploy_vercel():
    """Deploy output/ folder to Vercel as a static site."""
    print("🚀 Deploying to Vercel...")

    # Create vercel.json config
    vercel_config = {
        "version": 2,
        "builds": [{"src": "output/**", "use": "@vercel/static"}],
        "routes": [{"src": "/(.*)", "dest": "/output/$1"}]
    }

    with open("vercel.json", "w") as f:
        json.dump(vercel_config, f, indent=2)

    # Check if vercel CLI is installed
    result = subprocess.run(["vercel", "--version"], capture_output=True)
    if result.returncode != 0:
        print("  Installing Vercel CLI...")
        subprocess.run(["npm", "i", "-g", "vercel"], check=True)

    # Deploy
    result = subprocess.run(
        ["vercel", "--prod", "--yes"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        # Extract deployed URL
        url = result.stdout.strip().split('\n')[-1]
        print(f"  ✅ Deployed! Base URL: {url}")
        print(f"\n  Demo URLs will be: {url}/demo_<slug>.html")

        # Update .env with the base URL
        update_env("DEMO_BASE_URL", url)
        return url
    else:
        print(f"  ❌ Vercel deploy failed:\n{result.stderr}")
        return None


def deploy_s3():
    """Deploy output/ folder to AWS S3."""
    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        bucket = input("Enter your S3 bucket name: ").strip()

    print(f"🚀 Uploading to s3://{bucket}...")
    try:
        import boto3
        s3 = boto3.client('s3')
        for html_file in OUTPUT_DIR.glob("*.html"):
            s3.upload_file(
                str(html_file), bucket, html_file.name,
                ExtraArgs={'ContentType': 'text/html', 'ACL': 'public-read'}
            )
            print(f"  ✅ Uploaded {html_file.name}")

        region = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
        base_url = f"https://{bucket}.s3.{region}.amazonaws.com"
        print(f"\n  Base URL: {base_url}")
        update_env("DEMO_BASE_URL", base_url)
        return base_url

    except ImportError:
        print("  Install boto3: pip install boto3 --break-system-packages")
        return None


def deploy_local():
    """Start a local HTTP server for testing."""
    import http.server
    import socketserver
    import threading

    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    os.chdir(OUTPUT_DIR)

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🌐 Local server running at http://localhost:{PORT}")
        print(f"   Demo URLs: http://localhost:{PORT}/demo_<slug>.html")
        print("   Press Ctrl+C to stop\n")
        httpd.serve_forever()


def update_env(key: str, value: str):
    """Update a key in .env file."""
    env_file = Path(".env")
    if env_file.exists():
        content = env_file.read_text()
        if key in content:
            lines = content.split('\n')
            lines = [f"{key}={value}" if l.startswith(f"{key}=") else l for l in lines]
            env_file.write_text('\n'.join(lines))
        else:
            with open(env_file, 'a') as f:
                f.write(f"\n{key}={value}")
    print(f"  Updated {key} in .env")


def list_demos():
    """List all generated demo pages."""
    demos = list(OUTPUT_DIR.glob("demo_*.html"))
    if not demos:
        print("No demos generated yet. Run: python main.py --dry-run")
        return

    base_url = os.getenv("DEMO_BASE_URL", "http://localhost:8080")
    print(f"\n📋 Generated Demos ({len(demos)} total):")
    for d in demos:
        print(f"  {d.name}")
        print(f"  → {base_url}/{d.name}")


if __name__ == "__main__":
    provider = "local"
    if "--provider" in sys.argv:
        idx = sys.argv.index("--provider")
        provider = sys.argv[idx + 1]

    if "--list" in sys.argv:
        list_demos()
        sys.exit(0)

    if provider == "vercel":
        deploy_vercel()
    elif provider == "s3":
        deploy_s3()
    else:
        deploy_local()
