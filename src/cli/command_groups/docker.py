from .commander import run_command

class DockerInterface:
    def __init__(
        self,
        version: str,
        dockerfile_path: str,
        image_name: str,
        tar_path: str) -> None:
            self.version: str = version
            self.dockerfile_path: str = dockerfile_path
            self.image_name: str = image_name
            self.tar_path: str = tar_path


    def build_docker_image(self) -> str:
        """
        Handles the core logic for building the Docker image.
        """
        image_tag = f"{self.image_name}:{self.version}"

        # Build the Docker image
        print("\n🛠 Building Docker image")
        build_command = [
            "docker", "build",
            "-f", self.dockerfile_path,
            "-t", image_tag,
            "../../"  # Build context
        ]
        return run_command(build_command)

    def save_docker_image(self) -> str:
        """
        Handles the core logic for saving the Docker image.
        """
        image_tag = f"{self.image_name}:{self.version}"
        tar_file = f"{self.tar_path}/{self.image_name}.tar"

        # Save the Docker image to a .tar file
        print("\n🛢 Saving image to tarball")
        save_command = [
            "docker", "save",
            image_tag,
            "-o", tar_file
        ]
        return run_command(save_command)

    def import_docker_image(self) -> str:
        """
        Handles the core logic for importing the Docker image to k3s.
        """
        tar_file = f"{self.tar_path}/{self.image_name}.tar"
        # Import the image into the K3s container runtime (requires sudo)
        print("\n🚛 Importing image into K3s")
        import_command = [
            "k3s", "ctr",
            "image", "import",
            tar_file
        ]
        return run_command(import_command, sudo=True)
