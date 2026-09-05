from __future__ import annotations

import json
from dataclasses import asdict

import typer

from envora.analyzer.analyzer import analyze as analyze_repo
from envora.cloner import CloneError, clone

app = typer.Typer(help="Envora: deterministic repository analysis.")


@app.command()
def analyze(
    repo_url: str = typer.Argument(..., help="GitHub repo URL to analyze"),
) -> None:
    try:
        with clone(repo_url) as cloned:
            result = analyze_repo(cloned.path)
    except CloneError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    app()
