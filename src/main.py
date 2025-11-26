"""Main entry point for the SoftLight UI workflow capture system."""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core import WorkflowOrchestrator
from adapters import get_adapter
from utils import log, config, console, create_progress
from rich.table import Table


async def run_single_task(
    app_name: str,
    task_query: str,
    task_id: Optional[str] = None,
    start_url: Optional[str] = None,
    max_steps: Optional[int] = None,
    headless: bool = False,
    llm_provider: str = "openai"
):
    """
    Run a single task workflow.
    
    Args:
        app_name: Name of the app (e.g., "linear", "notion")
        task_query: Natural language task query
        task_id: Optional task ID (will be generated if not provided)
        start_url: Optional starting URL
        max_steps: Maximum steps to take
        headless: Run browser in headless mode
        llm_provider: LLM provider to use
    """
    # Get app config
    app_config = config.get_app_config(app_name)
    if not app_config:
        console.print(f"[red]Error: Unknown app '{app_name}'[/red]")
        console.print(f"[yellow]Available apps: {', '.join(config.apps.keys())}[/yellow]")
        return None
    
    # Generate task ID if not provided
    if not task_id:
        task_id = task_query.lower().replace(" ", "_")[:50]
    
    console.print(f"\n[bold]🎯 Task:[/bold] {task_query}")
    console.print(f"[bold]📱 App:[/bold] {app_name}")
    console.print(f"[bold]🤖 LLM:[/bold] {llm_provider}\n")
    
    # Create orchestrator
    async with WorkflowOrchestrator(
        app_config=app_config,
        llm_provider=llm_provider,
        headless=headless,
        browser_type=config.browser_type
    ) as orchestrator:
        # Execute workflow
        dataset = await orchestrator.execute_workflow(
            task_query=task_query,
            task_id=task_id,
            start_url=start_url,
            max_steps=max_steps
        )
        
        return dataset


async def run_task_from_config(
    task_id: str,
    headless: bool = False,
    llm_provider: str = "openai"
):
    """
    Run a task from the config file.
    
    Args:
        task_id: Task ID from config/tasks.yaml
        headless: Run browser in headless mode
        llm_provider: LLM provider to use
    """
    task_config = config.get_task_config(task_id)
    if not task_config:
        console.print(f"[red]Error: Task '{task_id}' not found in config[/red]")
        console.print(f"[yellow]Available tasks: {', '.join(config.tasks.keys())}[/yellow]")
        return None
    
    app_config = config.get_app_config(task_config.app)
    if not app_config:
        console.print(f"[red]Error: Unknown app '{task_config.app}'[/red]")
        return None
    
    # Create orchestrator
    async with WorkflowOrchestrator(
        app_config=app_config,
        llm_provider=llm_provider,
        headless=headless,
        browser_type=config.browser_type
    ) as orchestrator:
        # Execute workflow
        dataset = await orchestrator.execute_task_config(task_config)
        return dataset


async def run_multiple_tasks(
    task_ids: List[str],
    headless: bool = False,
    llm_provider: str = "openai"
):
    """
    Run multiple tasks sequentially.
    
    Args:
        task_ids: List of task IDs from config
        headless: Run browser in headless mode
        llm_provider: LLM provider to use
    """
    results = []
    
    with create_progress() as progress:
        task = progress.add_task(
            f"Running {len(task_ids)} tasks...",
            total=len(task_ids)
        )
        
        for i, task_id in enumerate(task_ids):
            console.print(f"\n[bold cyan]═══ Task {i+1}/{len(task_ids)}: {task_id} ═══[/bold cyan]\n")
            
            result = await run_task_from_config(task_id, headless, llm_provider)
            results.append(result)
            
            progress.update(task, advance=1)
    
    return results


def list_tasks():
    """List all available tasks from config."""
    table = Table(title="Available Tasks", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("App", style="magenta")
    table.add_column("Query", style="green")
    table.add_column("Max Steps", justify="right")
    
    for task_id, task_config in config.tasks.items():
        table.add_row(
            task_id,
            task_config.app,
            task_config.query,
            str(task_config.max_steps)
        )
    
    console.print(table)


def list_apps():
    """List all configured apps."""
    table = Table(title="Available Apps", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Base URL", style="green")
    table.add_column("Workspace", style="yellow")
    
    for app_name, app_config in config.apps.items():
        table.add_row(
            app_name,
            app_config.base_url,
            app_config.workspace or "N/A"
        )
    
    console.print(table)


def show_summary(datasets):
    """Show summary of completed workflows."""
    if not datasets:
        return
    
    console.print("\n[bold cyan]═══ Execution Summary ═══[/bold cyan]\n")
    
    table = Table(show_header=True)
    table.add_column("Task", style="cyan")
    table.add_column("Steps", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Status", justify="center")
    
    for dataset in datasets:
        if dataset:
            status = "✅" if dataset.success else "❌"
            table.add_row(
                dataset.task_query[:50],
                str(dataset.total_steps),
                f"{dataset.duration_seconds:.1f}s",
                status
            )
    
    console.print(table)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SoftLight - AI UI Workflow Capture System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a task with natural language query
  python src/main.py --app linear --task "How do I create a project?"
  
  # Run a task from config
  python src/main.py --task-id linear_create_project
  
  # Run multiple tasks
  python src/main.py --task-ids linear_create_project linear_filter_issues
  
  # Run all tasks for an app
  python src/main.py --run-all --app linear
  
  # List available tasks and apps
  python src/main.py --list-tasks
  python src/main.py --list-apps
        """
    )
    
    # Task specification
    parser.add_argument("--app", type=str, help="App name (e.g., linear, notion)")
    parser.add_argument("--task", type=str, help="Task query in natural language")
    parser.add_argument("--task-id", type=str, help="Task ID from config")
    parser.add_argument("--task-ids", nargs="+", help="Multiple task IDs from config")
    parser.add_argument("--run-all", action="store_true", help="Run all configured tasks")
    
    # Optional parameters
    parser.add_argument("--start-url", type=str, help="Starting URL")
    parser.add_argument("--max-steps", type=int, help="Maximum steps")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--llm-provider", type=str, default="openai", 
                       choices=["openai", "anthropic"], help="LLM provider")
    
    # Info commands
    parser.add_argument("--list-tasks", action="store_true", help="List all tasks")
    parser.add_argument("--list-apps", action="store_true", help="List all apps")
    
    args = parser.parse_args()
    
    # Info commands
    if args.list_tasks:
        list_tasks()
        return
    
    if args.list_apps:
        list_apps()
        return
    
    # Validate API keys
    if args.llm_provider == "openai" and not config.openai_api_key:
        console.print("[red]Error: OPENAI_API_KEY not set in environment[/red]")
        return
    
    if args.llm_provider == "anthropic" and not config.anthropic_api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not set in environment[/red]")
        return
    
    # Run workflows
    datasets = []
    
    try:
        if args.run_all:
            # Run all tasks
            task_ids = list(config.tasks.keys())
            if args.app:
                task_ids = [
                    tid for tid, tc in config.tasks.items()
                    if tc.app == args.app
                ]
            datasets = asyncio.run(run_multiple_tasks(
                task_ids,
                headless=args.headless,
                llm_provider=args.llm_provider
            ))
        
        elif args.task_ids:
            # Run multiple tasks
            datasets = asyncio.run(run_multiple_tasks(
                args.task_ids,
                headless=args.headless,
                llm_provider=args.llm_provider
            ))
        
        elif args.task_id:
            # Run single task from config
            dataset = asyncio.run(run_task_from_config(
                args.task_id,
                headless=args.headless,
                llm_provider=args.llm_provider
            ))
            if dataset:
                datasets = [dataset]
        
        elif args.app and args.task:
            # Run single task with natural language
            dataset = asyncio.run(run_single_task(
                app_name=args.app,
                task_query=args.task,
                start_url=args.start_url,
                max_steps=args.max_steps,
                headless=args.headless,
                llm_provider=args.llm_provider
            ))
            if dataset:
                datasets = [dataset]
        
        else:
            parser.print_help()
            return
        
        # Show summary
        show_summary(datasets)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        log.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()

