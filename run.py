import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(help="LLM-based software engineering agent.")
console = Console()


@app.command()
def build(
    prompt: str = typer.Argument(..., help="Plain-English description of the software to build."),
    output_dir: str = typer.Option("./outputs", help="Directory to write output files."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show the full final output."),
    no_test: bool = typer.Option(False, "--no-test", help="Skip the testing agent (Agent C)."),
):
    """Build a software project from a plain-English description."""
    # Imported here (not at top) so `run.py --help`, `doctor`, and `stats`
    # work even when crewai isn't installed. Building the crew is a side effect
    # we only want when the user actually runs `build`.
    from orchestrator.pipeline import run_pipeline

    console.print(Panel.fit(f"[bold]Building:[/bold] {prompt}", border_style="purple"))

    with console.status(
        "[bold purple]Agents working (this can take 30-60s)...", spinner="dots"
    ):
        result = run_pipeline(prompt, output_dir=output_dir, run_test=not no_test)

    console.print(
        f"[green]Done.[/green] Output written to: [bold]{result['run_dir']}[/bold]"
    )
    if verbose:
        console.print(Panel(result["result"], title="Final Output", border_style="green"))

    console.print("\n[dim]Run `python run.py stats` for token/cost totals.[/dim]")


@app.command()
def doctor():
    """Run environment checks."""
    import subprocess
    subprocess.run(["python", "scripts/doctor.py"])


@app.command()
def stats():
    """Show a summary of all logged LLM calls (tokens, time, per-agent)."""
    import subprocess
    subprocess.run(["python", "scripts/stats.py"])


if __name__ == "__main__":
    app()
