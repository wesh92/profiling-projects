from __future__ import annotations

import pendulum

from airflow.models.dag import dag
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

# A small C program to be executed.
# Note the escaped newline character '\\n' for proper printing.
C_CODE_STRING = """
#include <stdio.h>

int main() {
    printf("Hello from a C program running in Airflow!\\n");
    return 0;
}
"""

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
    # This task launches a pod with the 'gcc' image, which contains a C compiler.
    # It then writes, compiles, and runs the C code defined above.
    compile_and_run_c_code = KubernetesPodOperator(
        task_id="compile_and_run_c_code",
        # The pod will be created in the same namespace as Airflow.
        namespace="airflow",
        # Use an official image that includes the GCC C compiler.
        image="gcc:latest",
        # Name for the pod that will be created.
        name="c-code-execution-pod",
        # These commands are executed sequentially in a shell inside the pod.
        cmds=["/bin/bash", "-c"],
        arguments=[
            """
            echo "--- Writing C code to file ---"
            # The C code is passed as an environment variable by Airflow.
            # We write it to a file named hello.c.
            echo "$C_CODE" > hello.c

            echo "--- Compiling C code ---"
            # Use gcc to compile the source code into an executable named 'hello_app'.
            # The '-o' flag specifies the output file name.
            gcc hello.c -o hello_app

            echo "--- Running compiled C code ---"
            # Execute the compiled binary. Its output will appear in the task logs.
            ./hello_app

            echo "--- C code execution finished ---"
            """
        ],
        # Pass the C code string into the pod as an environment variable.
        # This is a clean way to inject scripts or code into the operator.
        env_vars={"C_CODE": C_CODE_STRING},
        # Defines what happens to the pod after the task finishes.
        # 'on_success': pod is deleted automatically if the task succeeds.
        do_xcom_push=True,
        # Log all events from the Kubernetes pod to the Airflow task logs.
        log_events_on_failure=True,
    )
    start >> compile_and_run_c_code >> end

dag = c_k8s_example()
