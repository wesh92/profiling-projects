from __future__ import annotations

import asyncio
import pendulum
from airflow.decorators import dag, task
from airflow.models.param import Param
from openfga_sdk import OpenFgaApi, ApiClient, Configuration
from openfga_sdk.models.check_request import CheckRequest
from openfga_sdk.models.tuple_key import TupleKey

@dag(
    dag_id="open_fga_check_tuple",
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    schedule=None,
    tags=["openfga"],
    params={
        "user": Param(
            type="string",
            default="pid:123",
            title="User",
            description="The user part of the tuple (e.g., 'pid:123').",
        ),
        "relation": Param(
            type="string",
            default="can_read",
            title="Relation",
            description="The relation part of the tuple (e.g., 'can_read').",
        ),
        "object": Param(
            type="string",
            default="internalId:abc",
            title="Object",
            description="The object part of the tuple (e.g., 'internalId:abc').",
        ),
    },
)
def check_openfga_tuple_dag():
    """
    ### Check OpenFGA Tuple
    This DAG checks if a specific tuple exists in your OpenFGA store.
    """

    @task
    def check_tuple(**context):
        """
        Checks for the existence of a tuple in OpenFGA.
        """
        user = context["params"]["user"]
        relation = context["params"]["relation"]
        obj = context["params"]["object"]

        async def _check_tuple_async():
            """
            Asynchronously checks for the tuple in OpenFGA.
            """
            configuration = Configuration(
                api_scheme="http",
                api_host="openfga.default:8088",  # Your OpenFGA service and port
                store_id="01K4T7VNNPX4AGCASBVAAMWWPM"
            )

            try:
                async with ApiClient(configuration) as api_client:
                    api_instance = OpenFgaApi(api_client)

                    # Get the store ID for "Kafka-Airflow-Store"
                    stores_response = await api_instance.list_stores()
                    store_id = None
                    for store in stores_response.stores:
                        if store.name == "Kafka-Airflow-Store":
                            store_id = store.id
                            break

                    if not store_id:
                        print("Store 'Kafka-Airflow-Store' not found.")
                        return

                    # Create a TupleKey for the check
                    tuple_key = TupleKey(user=user, relation=relation, object=obj)

                    # Create a CheckRequest
                    body = CheckRequest(tuple_key=tuple_key)

                    # Perform the check
                    response = await api_instance.check(body)

                    if response.allowed:
                        print(f"Tuple {tuple_key.to_dict()} exists and is allowed.")
                    else:
                        print(f"Tuple {tuple_key.to_dict()} does not exist or is not allowed.")

                    return response.allowed

            except Exception as e:
                print(f"Error communicating with OpenFGA...: {e}")
                raise

        return asyncio.run(_check_tuple_async())

    check_tuple()

check_openfga_tuple_dag()
