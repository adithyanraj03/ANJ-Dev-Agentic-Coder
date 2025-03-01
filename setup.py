#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def setup_environment():
    """Set up development environment."""
    print("Setting up ANJ DEV Terminal environment...")

    # Create required directories
    directories = ['apps', 'logs']
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"Created directory: {dir_name}")

    # Install dependencies
    print("\nInstalling dependencies...")
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ])
        print("Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False

    # Create default config if not exists
    config_path = Path('config.json')
    if not config_path.exists():
        import json
        default_config = {
            "llm_studio_url": "http://localhost:1234/v1",
            "max_retries": 3,
            "timeout": None,
            "models": ["gpt-3.5-turbo"],
            "deployment": {
                "backup_before_deploy": True,
                "auto_cleanup": False,
                "max_deployments": 10
            },
            "ui": {
                "enable_animations": True,
                "animation_speed": 0.05,
                "symbols": {
                    "success": "(✓)",
                    "error": "(✗)",
                    "warning": "(!)",
                    "info": "(>)",
                    "bullet": "•",
                    "arrow": "->"
                },
                "colors": {
                    "title": "cyan",
                    "prompt": "green",
                    "success": "green",
                    "error": "red",
                    "warning": "yellow",
                    "info": "blue"
                }
            }
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        print("Created default config.json")

    print("\nSetup complete! You can now run:\n")
    print("  python launch_terminal.py")
    return True

if __name__ == "__main__":
    setup_environment()
