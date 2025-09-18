from __future__ import annotations

import asyncio
import pendulum
from airflow.decorators import dag, task
from airflow.models.param import Param
from openfga_sdk import OpenFgaApi, ApiClient, Configuration
from openfga_sdk.models.create_store_request import CreateStoreRequest

@dag(
    dag_id="open_fga_create_store",
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    schedule=None,
    tags=["openfga"],
    params={
        "store_name": Param(
            type="string",
            default="Kafka-Airflow-Store",
            title="OpenFGA Store Name",
            description="The name for the new OpenFGA store.",
        ),
    },
)
def create_openfga_store_dag():
    """
    ### Create OpenFGA Store
    This DAG creates a new store in your OpenFGA instance using the
    provided 'store_name' parameter.
    """

    @task
    def create_store(**context):
        """
        Creates a new store in OpenFGA.
        """
        store_name = context["params"]["store_name"]

        async def _create_store_async():
            """
            Asynchronously creates a new store in OpenFGA.
            """
            configuration = Configuration(
                api_scheme="http",
                api_host="openfga.default:8088",  # Your OpenFGA service and port
            )

            try:
                async with ApiClient(configuration) as api_client:
                    api_instance = OpenFgaApi(api_client)

                    # 1. Check if a store with the same name already exists
                    existing_stores_response = await api_instance.list_stores()

                    # The response object has a `.stores` attribute which is a list.
                    # Iterate over this list directly.
                    for store in existing_stores_response.stores:
                        if store.name == store_name:
                            print(f"Store '{store_name}' already exists with ID: {store.id}")
                            return store.id

                    # 2. If the loop completes without finding the store, create a new one.
                    print(f"Store '{store_name}' not found. Creating it now.")
                    body = CreateStoreRequest(name=store_name)
                    response = await api_instance.create_store(body)

                    print(f"Successfully created store '{store_name}' with ID: {response.id}")
                    return response.id

            except Exception as e:
                print(f"Error communicating with OpenFGA: {e}")
                raise

        return asyncio.run(_create_store_async())

    create_store()

create_openfga_store_dag()
