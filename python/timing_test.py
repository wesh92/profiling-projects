import time
import os
import sys
import json
from functools import wraps
from datetime import datetime, timezone
from src.profile import Profile

import psutil

log_step = Profile()

@log_step
def initialize_settings():
    time.sleep(0.5)
    return {"version": "1.0", "mode": "production"}

@log_step
def fetch_data(source: str):
    time.sleep(1)
    return [i for i in range(10)]

@log_step
def process_data(data: list):
    processed_sum = sum(data * 1000)
    time.sleep(1.5)
    return {"records_processed": len(data), "sum": processed_sum}

@log_step
def save_results(results: dict):
    time.sleep(0.75)
    return "Save operation successful."

def main():
    """Main entrypoint: connect to Kafka, run pipeline, flush messages."""
    init_kafka_producer()

    _ = initialize_settings()
    raw_data = fetch_data(source="database")
    final_results = process_data(data=raw_data)
    _ = save_results(results=final_results)

    if kafka_producer:
        print("📦 Flushing final messages to Kafka...")
        kafka_producer.flush() # Block until all async messages are sent
        kafka_producer.close()
        print("📦 Kafka producer closed.")

if __name__ == "__main__":
    print("🚀 Starting the Python application pipeline...")
    main()
    print("🏁 Pipeline finished.")
    if GPU_ENABLED:
        pynvml.nvmlShutdown()
