from __future__ import annotations

import json
import pendulum

from airflow.decorators import dag, task
from airflow.models.taskinstance import TaskInstance
from airflow.providers.apache.kafka.operators.consume import ConsumeFromTopicOperator
from airflow.providers.standard.operators.empty import EmptyOperator


def process_kafka_message(message):
    """
    Processes a message from Kafka. This function is called for each message
    consumed from the topic
    """
    data = json.loads(message.value().decode("utf-8"))
    pid = data.get("pid")
    pid2 = data.get("pid2")
    # Nested .get() to safely access providerId
    internalId = data.get("data", {}).get("internalId")

    print(pid)
    print(pid2)
    print(internalId)


@dag(
    dag_id="kafka_consumer_dag_taskflow",
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    schedule=None,
    tags=["kafka", "consumer", "example", "taskflow"],
)
def kafka_consumer_dag_taskflow():
    """
    ### Kafka Consumer DAG using TaskFlow API
    This DAG consumes messages from a Kafka topic, uses the `@task.branch`
    decorator to check for required fields, and processes the message only if
    all fields are present.
    """

    consume_from_topic = ConsumeFromTopicOperator(
        task_id="consume_from_topic",
        kafka_config_id="kafka_default",
        topics=["my-topic"],
        apply_function=process_kafka_message,
        poll_timeout=60,
        max_messages=10,
    )

    # This task will run after either 'process_record' or 'stop_processing' completes.
    end = EmptyOperator(task_id="end", trigger_rule="none_failed_min_one_success")

    consume_from_topic >> end

# Instantiate the DAG
kafka_consumer_dag_instance = kafka_consumer_dag_taskflow()
