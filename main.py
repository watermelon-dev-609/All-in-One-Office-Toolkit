"""全能办公工具箱 - All-in-One Office Toolkit

A comprehensive local offline office tool collection for Windows.
"""

import sys
import os

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.app import App


def main():
    """Application entry point."""
    app = App(sys.argv)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
