#!/usr/bin/env python3
import os
import sys
import subprocess
import importlib.util


def check_package(package_name):
    """Check if a package is installed."""
    return importlib.util.find_spec(package_name) is not None


def install_package(package_name):
    """Install a package using pip."""
    print(f"Installing {package_name}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])


def check_dependencies():
    """Check and install required dependencies."""
    required_packages = ["streamlit", "openai", "python-dotenv"]
    missing_packages = []

    for package in required_packages:
        if not check_package(package):
            missing_packages.append(package)

    if missing_packages:
        print("Missing required packages. Installing...")
        for package in missing_packages:
            install_package(package)
        print("All dependencies installed!")
    else:
        print("All dependencies already installed.")


def check_env_file():
    """Check if .env file exists and contains OPENAI_API_KEY."""
    if not os.path.exists(".env"):
        print("Warning: .env file not found.")
        api_key = input("Enter your OpenAI API key: ").strip()
        if api_key:
            with open(".env", "w") as f:
                f.write(f"OPENAI_API_KEY={api_key}\n")
                f.write("OPENAI_MODEL=gpt-4o-mini\n")
            print(".env file created with API key.")
        else:
            print("No API key provided. The app may not function correctly.")
    else:
        with open(".env", "r") as f:
            content = f.read()
            if "OPENAI_API_KEY" not in content:
                print("Warning: OPENAI_API_KEY not found in .env file.")
                api_key = input("Enter your OpenAI API key: ").strip()
                if api_key:
                    with open(".env", "a") as f:
                        f.write(f"OPENAI_API_KEY={api_key}\n")
                    print("API key added to .env file.")
            if "OPENAI_MODEL" not in content:
                with open(".env", "a") as f:
                    f.write("OPENAI_MODEL=gpt-4o-mini\n")
                print("Default model added to .env file.")


def run_app():
    """Run the Streamlit app."""
    print("Starting Streamlit app...")
    subprocess.run(["streamlit", "run", "app.py"])


if __name__ == "__main__":
    print("==== AI Chat Assistant Setup ====")
    check_dependencies()
    check_env_file()
    run_app()
