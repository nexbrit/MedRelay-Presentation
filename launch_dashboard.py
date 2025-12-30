#!/usr/bin/env python3
"""
Launch script for F&O Trading Web Dashboard
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Launch the Streamlit web dashboard"""

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║        F&O TRADING PLATFORM - WEB DASHBOARD              ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Get the dashboard directory
    dashboard_dir = Path(__file__).parent / "web_dashboard"
    app_file = dashboard_dir / "app.py"

    if not app_file.exists():
        print("❌ Error: Dashboard app not found!")
        print(f"   Looking for: {app_file}")
        return 1

    print("🚀 Starting web dashboard...")
    print(f"📂 Dashboard directory: {dashboard_dir}")
    print(f"🌐 Opening browser at: http://localhost:8501")
    print()
    print("💡 Tips:")
    print("   - Press Ctrl+C to stop the server")
    print("   - Refresh browser to see code changes")
    print("   - Dashboard will auto-reload on file changes")
    print()

    # Launch Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(app_file),
            "--server.port=8501",
            "--server.address=localhost",
            "--browser.gatherUsageStats=false",
            "--theme.base=light"
        ], check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down dashboard...")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error launching dashboard: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
