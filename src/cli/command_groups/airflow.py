from logging import log, INFO, WARNING, ERROR
from pathlib import Path
import subprocess
import typer

app = typer.Typer()

class AirflowK8s:
    def __init__(self, verbosity: bool = True, k8s_namespace: str = "airflow") -> None:
        self.verbosity = verbosity
        self.k8s_namespace = k8s_namespace

k8s_instance = AirflowK8s()

@app.command()
def apply_airflow_values(
    values_file: str = "../../airflow/airflow-values.yaml",
    release_name: str = "airflow",
    chart: str = "apache-airflow/airflow"
):
    """
    Deploys or upgrades an Airflow release using Helm.
    """
    # Ensure the values file exists before proceeding
    if not Path(values_file).is_file():
        log(ERROR, f"Values file not found at: {values_file}")
        raise typer.Exit(code=1)

    # Construct the Helm command
    command = [
        "helm", "upgrade",
        "--install", release_name,
        chart,
        "--namespace", k8s_instance.k8s_namespace,
        "--create-namespace", # Creates the namespace if it doesn't exist
        "-f", values_file
    ]

    print(f"🚀 Executing Helm command: {' '.join(command)}")

    try:
        # Execute the command and capture output
        result = subprocess.run(
            command,
            check=True,          # Raise an exception if the command fails
            capture_output=True, # Capture stdout and stderr
            text=True            # Decode output as text
        )
        print("✅ Helm command successful!")
        print(result.stdout)
    except FileNotFoundError:
        log(ERROR, "The 'helm' command was not found. Is the Helm CLI installed and in your PATH?")
    except subprocess.CalledProcessError as e:
        log(ERROR, f"Helm command failed with exit code {e.returncode}.")
        log(ERROR, f"STDERR:\n{e.stderr}")
    except Exception as e:
        log(ERROR, f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    app()
