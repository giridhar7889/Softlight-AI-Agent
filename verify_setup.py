#!/usr/bin/env python3
"""
Verification script to check if SoftLight is set up correctly.
Run this after installation to verify everything works.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def check_python_version():
    """Check Python version."""
    import sys
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        return True, f"{version.major}.{version.minor}.{version.micro}"
    return False, f"{version.major}.{version.minor}.{version.micro}"


def check_dependencies():
    """Check if all required packages are installed."""
    required = [
        "playwright",
        "openai",
        "PIL",
        "yaml",
        "loguru",
        "rich"
    ]
    
    results = {}
    for package in required:
        try:
            if package == "PIL":
                import PIL
                results[package] = True, PIL.__version__
            elif package == "yaml":
                import yaml
                results[package] = True, yaml.__version__
            else:
                mod = __import__(package)
                results[package] = True, getattr(mod, "__version__", "Unknown")
        except ImportError:
            results[package] = False, "Not installed"
    
    return results


def check_config():
    """Check configuration."""
    try:
        from utils import config
        
        checks = {
            "Config loaded": config is not None,
            "OpenAI API key": bool(config.openai_api_key),
            "Apps configured": len(config.apps) > 0,
            "Tasks configured": len(config.tasks) > 0,
            "Dataset dir exists": config.dataset_dir.exists()
        }
        
        return checks
    except Exception as e:
        return {"Error": str(e)}


def check_playwright():
    """Check if Playwright browsers are installed."""
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
                browser.close()
                return True, "Chromium installed"
            except Exception as e:
                return False, str(e)
    except Exception as e:
        return False, str(e)


def main():
    console.print(Panel.fit(
        "[bold blue]SoftLight Setup Verification[/bold blue]\n"
        "Checking if everything is installed correctly...",
        border_style="blue"
    ))
    console.print()
    
    # Check Python version
    console.print("[bold]1. Python Version[/bold]")
    success, version = check_python_version()
    if success:
        console.print(f"   ✅ Python {version} (OK)")
    else:
        console.print(f"   ❌ Python {version} (Need 3.9+)")
    console.print()
    
    # Check dependencies
    console.print("[bold]2. Dependencies[/bold]")
    deps = check_dependencies()
    for package, (installed, version) in deps.items():
        if installed:
            console.print(f"   ✅ {package}: {version}")
        else:
            console.print(f"   ❌ {package}: {version}")
    console.print()
    
    # Check Playwright
    console.print("[bold]3. Playwright Browsers[/bold]")
    success, message = check_playwright()
    if success:
        console.print(f"   ✅ {message}")
    else:
        console.print(f"   ❌ {message}")
        console.print("   💡 Run: playwright install chromium")
    console.print()
    
    # Check configuration
    console.print("[bold]4. Configuration[/bold]")
    config_checks = check_config()
    for check, status in config_checks.items():
        if status:
            console.print(f"   ✅ {check}")
        else:
            console.print(f"   ❌ {check}")
            if "API key" in check:
                console.print("      💡 Add OPENAI_API_KEY to .env file")
    console.print()
    
    # Summary
    all_passed = all([
        check_python_version()[0],
        all(installed for installed, _ in check_dependencies().values()),
        check_playwright()[0],
        all(config_checks.values())
    ])
    
    if all_passed:
        console.print(Panel.fit(
            "[bold green]✅ All checks passed![/bold green]\n"
            "You're ready to use SoftLight.\n\n"
            "Try: [cyan]python src/main.py --list-apps[/cyan]",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            "[bold yellow]⚠️  Some checks failed[/bold yellow]\n"
            "Please address the issues above.\n\n"
            "See SETUP_GUIDE.md for help.",
            border_style="yellow"
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()

