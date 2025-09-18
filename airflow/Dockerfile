# Better version with more efficient layering
FROM python:3.12-slim as builder

# Install uv first (rarely changes)
RUN pip install --no-cache-dir uv

WORKDIR /build

# Copy and compile requirements (changes less frequently)
ARG AIRFLOW_VERSION=3.0.6
ARG CONSTRAINT_PYTHON_VERSION=3.9
COPY ./k8s-defaults/airflow/pyproject.toml .
RUN uv pip compile pyproject.toml \
    -c https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${CONSTRAINT_PYTHON_VERSION}.txt \
    -o requirements.txt

# Final stage
FROM apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}
USER root
COPY --from=builder /build/requirements.txt /
USER airflow
RUN pip install --no-cache-dir -r /requirements.txt
