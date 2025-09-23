from logging import log, INFO
import typer
from .helm import apply_helm_values
from .docker import DockerInterface

app = typer.Typer()
LOCAL_AIRFLOW_VERSION = "1.0.7"

class AirflowK8s:
    def __init__(self, verbosity: bool = True, k8s_namespace: str = "airflow") -> None:
        self.verbosity = verbosity
        self.k8s_namespace = k8s_namespace

k8s_instance = AirflowK8s()
docker = DockerInterface(
    version = LOCAL_AIRFLOW_VERSION,
    dockerfile_path="../../airflow/Dockerfile",
    image_name="local-airflow",
    tar_path="../../airflow"
)

# Private Functions
# ==============================================================================

# ==============================================================================
# End Private Functions

# Command Functions
# ==============================================================================
@app.command()
def apply_airflow_values(
    values_file: str = "../../airflow/airflow-values.yaml",
    release_name: str = "airflow",
    chart: str = "apache-airflow/airflow",
    namespace: str = k8s_instance.k8s_namespace
):
    """
    Deploys or upgrades an Airflow release using Helm.
    """
    log(INFO, f"🌬 Attempting to deploy Airflow to namespace {namespace}")
    apply_helm_values(
        values_file=values_file,
        release_name=release_name,
        chart=chart,
        namespace=namespace
    )

@app.command()
def build_and_load_image():
    """
    Calls the core logic to build, save, and import a custom Airflow image into k3s.
    """

    # Step 1: Build the Docker image
    _ = docker.build_docker_image()

    # Step 2: Save the Docker image to a .tar file
    _ = docker.save_docker_image()

    # Step 3: Import the image into the K3s container runtime (requires sudo)
    _ = docker.import_docker_image()
    print(f"\n✨ Successfully built and loaded image '{docker.image_name}:{docker.version}' into K3s.")


if __name__ == "__main__":
    app()
