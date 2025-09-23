import subprocess
import typer
from logging import log, ERROR

def run_command(command: list[str], sudo: bool = False):
    """A helper function to run a generic command, log it, and handle errors."""
    if sudo:
        command.insert(0, "sudo")

    print(f"🏃 Running command: {' '.join(command)}")
    try:
        # We use capture_output=True to hide the command's output unless there's an error
        result = subprocess.run(
            command,
            check=True,          # Exit with an error if the command fails
            capture_output=True, # Capture stdout/stderr
            text=True            # Decode output as text
        )
        print("✅ Command successful.")
        return result.stdout
    except FileNotFoundError:
        log(ERROR, f"Command not found: '{command[0]}'. Is it installed and in your PATH?")
        raise typer.Exit(code=1)
    except subprocess.CalledProcessError as e:
        log(ERROR, f"Command failed with exit code {e.returncode}.")
        log(ERROR, f"stderr:\n{e.stderr}")
        raise typer.Exit(code=1)
    except Exception as e:
        log(ERROR, f"An unexpected error occurred: {e}")
        raise typer.Exit(code=1)
