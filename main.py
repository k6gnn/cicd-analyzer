"""
CI/CD Pipeline Health Analyzer
Entry point — handles user input and launches the agent.
"""

import sys
from rich.console import Console
from agent import run

console = Console()


def main():
    console.print("\n[bold blue]CI/CD Pipeline Health Analyzer[/bold blue]")
    console.print("[dim]Analyzes GitHub Actions workflows for security, performance, and best practices[/dim]\n")

    # Accept URL from CLI argument or interactive prompt
    if len(sys.argv) > 1:
        repo_url = sys.argv[1].strip()
    else:
        repo_url = console.input("[bold]Enter GitHub repository URL:[/bold] ").strip()

    if not repo_url:
        console.print("[red]Error: No repository URL provided.[/red]")
        sys.exit(1)

    if "github.com" not in repo_url:
        console.print("[red]Error: Please provide a valid GitHub repository URL.[/red]")
        sys.exit(1)

    try:
        report_path = run(repo_url)
        console.print(f"[bold green]Analysis complete.[/bold green] Report: {report_path}")
    except FileNotFoundError as e:
        console.print(f"[red]Not found: {e}[/red]")
        sys.exit(1)
    except PermissionError as e:
        console.print(f"[red]Permission error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
