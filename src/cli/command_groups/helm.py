from logging import log, ERROR
from pathlib import Path
import subprocess
import typer

def apply_helm_values(
    values_file: str,
    release_name: str,
    chart: str,
    namespace: str = "default"
):
    """
    Deploys or upgrades a release using Helm.

    :values_file:: STRING (REQUIRED)
        String path (relative to execution) to the helm values yaml related to this deployment
    :release_name:: STRING (REQUIRED)
        The helm release name. Use Artifact Hub to find Helm Releases.
    :chart :: STRING (REQUIRED)
        The helm chart location. Use Artifcat Hub to find Helm Charts.
    :namespace :: STRING (OPTIONAL, default = default)
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
        "--namespace", namespace,
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
