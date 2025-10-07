from __future__ import annotations

import pendulum

from airflow.sdk import dag
from airflow.providers.standard.operators.empty import EmptyOperator
from src.local.kubernetes.operators.pod import (
    ProfiledKubernetesPodOperator as KubernetesPodOperator,
)
from src.profiler import Profile
from kubernetes.client import models as k8s

profile = Profile(cprofile_enabled=True, tracemalloc_enabled=True)


@dag(
    dag_id="c_code_execution_dag",
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    schedule=None,
    tags=["kubernetes", "c-code", "example"],
)
def c_k8s_example():
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    kpo = KubernetesPodOperator(
        task_id="prime_calculator_pod",
        # Ensure this namespace is correct for your Airflow deployment
        namespace="airflow",
        image="cpp-math-app:latest",
        image_pull_policy="Never",
        name="cpu-intensive-pod",
        do_xcom_push=False,
        log_events_on_failure=True,
        env_vars={
            # Adjust this value to make the task run longer or shorter.
            # 1,500,000 should take < 1 minute on modern hardware.
            "MAX_PRIME": "1500000"
        },
        # Optional: Define resource requests and limits for the pod
        container_resources=k8s.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "64Mi", "ephemeral-storage": "1Gi"},
            limits={"cpu": "200m", "memory": "420Mi", "ephemeral-storage": "2Gi"},
        ),
    )

    start >> kpo >> end


dag = c_k8s_example()
