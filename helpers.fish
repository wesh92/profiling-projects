#!/usr/bin/fish

# ==============================================================================
#
#           `./local_k8s.fish` -- k3s management utility for FISH!
#
#   This script automates the setup and management of a local k3s cluster.
#   It provides functions to install dependencies,
#   configure the cluster, deploy Airflow, and manage the
#   environment with a set of convenient flags.
#
#   ** Author: Wes H.
#   ** Version: 1.2025.9-a
#   ** Version Syntax: ver.year.month-release_letter
#
# ==============================================================================

# --- Configuration Constants ---
set -g AIRFLOW_NAMESPACE "airflow"
set -g HELM_RELEASE_NAME "airflow"
set -g KAFKA_NAMESPACE "kafka"
set -g STRIMZI_RELEASE_NAME "strimzi-cluster-operator"
set -g LOCAL_REGISTRY "localhost:5001"
set -g DOCKER_IMAGE_NAME "local-airflow"
set -g DOCKER_IMAGE_TAG "latest"
set -g TAR_FILE_NAME "./k8s-defaults/airflow/local-airflow.tar"

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#   setup_local_registry
#
#   Sets up a local Docker registry to store the custom Airflow image. This
#   is necessary to make the image available to k3s without pushing it to a
#   public registry.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
function setup_local_registry
    _log "INFO" "Setting up local Docker registry..."
    if not docker ps -a --format '{{.Names}}' | grep -q "^local-registry\$"
        _log "INFO" "Starting local registry container..."
        docker run -d --name local-registry -p 5001:5000 --restart always registry:2
    else
        _log "INFO" "Local registry is already running."
    end

    if not test -f /etc/rancher/k3s/registries.yaml
        _log "INFO" "Configuring k3s to use the local registry..."
        echo "mirrors:
    \"$LOCAL_REGISTRY\":
        endpoint:
            - \"http://$LOCAL_REGISTRY\"" | sudo tee /etc/rancher/k3s/registries.yaml >/dev/null
        _log "INFO" "Restarting k3s to apply registry configuration..."
        sudo systemctl restart k3s
    end
end

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#   build_and_push_image
#
#   Builds the custom Airflow Docker image, creates a tarball, and pushes
#   it to the k3s container runtime.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
function build_and_push_image
    _log "INFO" "Building Docker image..."
    docker build -t "$DOCKER_IMAGE_NAME:$DOCKER_IMAGE_TAG" -f "./k8s-defaults/airflow/Dockerfile" .

    _log "INFO" "Creating tar file from Docker image..."
    docker save "$DOCKER_IMAGE_NAME:$DOCKER_IMAGE_TAG" -o "$TAR_FILE_NAME"

    _log "INFO" "Importing image into k3s..."
    sudo k3s ctr images import "$TAR_FILE_NAME"
end

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#   deploy_kafka
#
#   Deploys the Strimzi Kafka operator and a Kafka cluster.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
function deploy_kafka
    _log "INFO" "Creating the Kafka namespace..."
    sudo k3s kubectl create namespace $KAFKA_NAMESPACE --dry-run=client -o yaml | sudo k3s kubectl apply -f -

    _log "INFO" "Deploying Strimzi Kafka Operator from OCI..."
    helm install $STRIMZI_RELEASE_NAME oci://quay.io/strimzi-helm/strimzi-kafka-operator \
        --namespace $KAFKA_NAMESPACE --wait

    _log "INFO" "Deploying Kafka cluster..."
    sudo k3s kubectl apply -f k8s-defaults/kafka/kafka-cluster.yaml -n $KAFKA_NAMESPACE

    _log "INFO" "Waiting for Kafka cluster to be ready..."
    sudo k3s kubectl wait kafka/my-cluster --for=condition=Ready --timeout=300s -n $KAFKA_NAMESPACE

    _log "INFO" "Deploying Kafka topic..."
    sudo k3s kubectl apply -f k8s-defaults/kafka/kafka-topic.yaml -n $KAFKA_NAMESPACE

    _log "INFO" "Proxying Kafka..."
    proxy_kafka_bootstrap_server
end

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#   proxy_kafka_bootstrap_server
#
#   Forwards the Kafka External Boostrap Servers to localhost for easy access.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
function proxy_kafka_bootstrap_server
    _log "INFO" "Proxying Kafka to localhost:9094..."
    proxy_with_cleanup "svc/my-cluster-kafka-external-bootstrap" "kafka" "9094:9094"
end

function proxy_with_cleanup
    set -l service_name $argv[1]
    set -l namespace $argv[2]
    set -l port_mapping $argv[3]

    # Extract just the service name for the log file
    set -l log_name (echo $service_name | sed 's/svc\///')

    # Ensure log directory exists
    mkdir -p /tmp/k8s-proxy-logs

    # Kill existing port-forward if running
    set -l port (echo $port_mapping | cut -d':' -f1)
    pkill -f "port-forward.*$port" 2>/dev/null

    _log "INFO" "Starting $service_name proxy on port $port_mapping..."
    nohup kubectl port-forward -n $namespace $service_name $port_mapping > /tmp/k8s-proxy-logs/$log_name.log 2>&1 &

    # Store the PID
    echo $last_pid > /tmp/k8s-proxy-logs/$log_name.pid
end



# --- SSH Key Management Functions ---

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#   setup_git_ssh_key
#
#   Creates a Kubernetes secret containing the SSH key for git-sync to access
#   the private repository. This function will prompt for the SSH key path if
#   not provided.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
function setup_git_ssh_key
    set -l ssh_key_path $argv[1]

    # If no path provided, try common locations
    if test -z "$ssh_key_path"
        if test -f ~/.ssh/id_rsa
            set ssh_key_path ~/.ssh/id_rsa
            _log "INFO" "Using default SSH key: $ssh_key_path"
        else if test -f ~/.ssh/id_ed25519
            set ssh_key_path ~/.ssh/id_ed25519
            _log "INFO" "Using default SSH key: $ssh_key_path"
        else
            _log "ERROR" "No SSH key found. Please provide path as argument."
            _log "INFO" "Usage: setup_git_ssh_key /path/to/ssh/key"
            return 1
        end
    end

    # Verify the SSH key exists
    if not test -f "$ssh_key_path"
        _log "ERROR" "SSH key not found at: $ssh_key_path"
        return 1
    end

    _log "INFO" "Creating SSH secret for git-sync in Airflow namespace..."

    # Create the secret
    kubectl create secret generic airflow-git-ssh-secret \
        --namespace $AIRFLOW_NAMESPACE \
        --from-file=gitSshKey=$ssh_key_path \
        --dry-run=client -o yaml | kubectl apply -f -

    if test $status -eq 0
        _log "INFO" "SSH secret 'airflow-git-ssh-secret' created successfully"

        # Also add known hosts to avoid SSH host key verification issues
        setup_git_known_hosts
    else
        _log "ERROR" "Failed to create SSH secret"
        return 1
    end
end

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#   setup_git_known_hosts
#
#   Creates or updates the known_hosts entry for GitHub in the git-sync secret.
#   This prevents SSH host key verification failures.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
function setup_git_known_hosts
    _log "INFO" "Setting up GitHub known hosts..."

    # Create a temporary known_hosts file with GitHub's SSH keys
    set -l temp_known_hosts (mktemp)

    # Get GitHub's SSH keys
    ssh-keyscan -t rsa,ed25519 github.com > $temp_known_hosts 2>/dev/null

    if test -s $temp_known_hosts
        # Update the existing secret to include known_hosts
        kubectl create secret generic airflow-git-ssh-secret \
            --namespace $AIRFLOW_NAMESPACE \
            --from-file=gitSshKey=(kubectl get secret airflow-git-ssh-secret -n $AIRFLOW_NAMESPACE -o jsonpath='{.data.gitSshKey}' | base64 -d | psub) \
            --from-file=known_hosts=$temp_known_hosts \
            --dry-run=client -o yaml | kubectl apply -f -

        _log "INFO" "GitHub known hosts added to secret"
    else
        _log "WARN" "Could not fetch GitHub SSH keys. You may need to add them manually."
    end

    # Clean up
    rm -f $temp_known_hosts
end
