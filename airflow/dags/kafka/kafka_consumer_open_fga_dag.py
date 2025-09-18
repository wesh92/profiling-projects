from __future__ import annotations

import asyncio
import json
import pendulum

from airflow.decorators import dag
from airflow.providers.apache.kafka.operators.consume import ConsumeFromTopicOperator
from airflow.providers.standard.operators.empty import EmptyOperator

from openfga_sdk import OpenFgaClient, ApiClient, ClientConfiguration
from openfga_sdk.client.models import ClientTuple, ClientWriteRequest


def process_kafka_message(message):
    """
    Processes a message from Kafka, formats it as an OpenFGA tuple object,
    and writes the tuple to the OpenFGA store.
    """
    data = json.loads(message.value().decode("utf-8"))
    pid = data.get("pid")
    pid2 = data.get("pid2")
    internalId = data.get("data", {}).get("internalId")

    if pid and pid2 and internalId:
        user = f"pid:{pid}"
        relation = pid2
        obj = f"internalId:{internalId}"

        openfga_tuple_key = ClientTuple(user=user, relation=relation, object=obj)

        async def _write_tuple_async():
            """
            Asynchronously writes the tuple to the OpenFGA store.
            """
            configuration = ClientConfiguration(
                api_scheme="http",
                api_host="openfga.default:8088",  # OpenFGA service and port
                store_id="01K4T7VNNPX4AGCASBVAAMWWPM"
            )

            try:
                async with OpenFgaClient(configuration) as ofga_client:

                    # Get the store ID for "Kafka-Airflow-Store"
                    stores_response = await ofga_client.list_stores()
                    store_id = None
                    for store in stores_response.stores:
                        if store.name == "Kafka-Airflow-Store":
                            store_id = store.id
                            break

                    if not store_id:
                        print("Store 'Kafka-Airflow-Store' not found.")
                        return

                    # Create a WriteRequest
                    body = ClientWriteRequest(
                        writes=[openfga_tuple_key]
                    )

                    # Write the tuple to the store
                    response = await ofga_client.write(body)

                    print(f"Successfully wrote tuple: {openfga_tuple_key.__dict__}")
                    print(f"Response: {response}")

            except Exception as e:
                print(f"Error communicating with OpenFGA: {e}")
                raise

        asyncio.run(_write_tuple_async())

    else:
        print(f"Skipping message due to missing data: {data}")


@dag(
    dag_id="kafka_consumer_open_fga_dag",
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    schedule=None,
    tags=["kafka", "consumer", "openfga", "example"],
)
def kafka_consumer_open_fga_dag():
    """
    ### Kafka Consumer DAG with OpenFGA Integration
    This DAG consumes messages from a Kafka topic, creates an OpenFGA tuple,
    and writes it to an OpenFGA store.
    """

    consume_from_topic = ConsumeFromTopicOperator(
        task_id="consume_from_topic",
        kafka_config_id="kafka_default",
        topics=["my-topic"],
        apply_function=process_kafka_message,
        poll_timeout=60,
        max_messages=10,
    )

    end = EmptyOperator(task_id="end", trigger_rule="none_failed_min_one_success")

    consume_from_topic >> end


# Instantiate the DAG
kafka_consumer_dag_instance = kafka_consumer_open_fga_dag()
