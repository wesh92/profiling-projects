"""
==============================================================================

          `uv run manage_k8s.py <OPTIONS>` -- k8s management utility!

  This Typer application helps manage the setup, teardown, and general maintenance
  of your local Kubernetes running on k3s.

  ** Author: Wes H.
  ** Version: 1.2025.9-1
  ** Version Syntax: ver.year.month-release

==============================================================================
"""

from typer import Typer
import command_groups.airflow as airflow

app = Typer()
app.add_typer(airflow.app, name="airflow")

if __name__ == "__main__":
    app()
