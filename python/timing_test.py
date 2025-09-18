import time
import os
import sys
import json
import uuid
from functools import wraps
from datetime import datetime, timezone

import psutil

# --- Kafka Producer ---
kafka_producer = None

# --- GPU Setup ---
try:
    import pynvml
    pynvml.nvmlInit()
    GPU_ENABLED = True
except Exception:
    GPU_ENABLED = False

def init_kafka_producer():
    """Initializes the Kafka producer using environment variables."""
    global kafka_producer
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if not bootstrap_servers:
        print("🔴 KAFKA_BOOTSTRAP_SERVERS environment variable not set. Kafka producer disabled.", file=sys.stderr)
        return

    try:
        from kafka import KafkaProducer
        # Serialize messages as JSON, encoded to UTF-8 bytes
        kafka_producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(','),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=3
        )
        print(f"📦 Successfully connected to Kafka at {bootstrap_servers}.")
    except Exception as e:
        print(f"🔴 Could not connect to Kafka: {e}", file=sys.stderr)
        kafka_producer = None

def format_bytes(byte_count):
    # (This helper function is unchanged)
    if byte_count is None: return "N/A"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while byte_count >= power and n < len(power_labels):
        byte_count /= power
        n += 1
    return f"{byte_count:.2f}{power_labels[n]}B"

def log_step(func):
    """A decorator to log, profile, and send metrics to Kafka."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"▶️  [START] Running step: '{func.__name__}'...")
        proc= psutil.Process(os.getpid())
        cpu_start = proc.cpu_times()
        mem_start = proc.memory_info()
        net_start = psutil.net_io_counters()
        gpu_handle, gpu_mem_start = None, None
        if GPU_ENABLED:
            try:
                gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                gpu_mem_start = pynvml.nvmlDeviceGetMemoryInfo(gpu_handle)
            except Exception: pass

        start_time = time.monotonic()
        result = func(*args, **kwargs) # Execute function
        end_time = time.monotonic()

        # --- Calculate Deltas (Unchanged) ---
        duration = end_time - start_time
        cpu_end, mem_end, net_end = proc.cpu_times(), proc.memory_info(), psutil.net_io_counters()
        cpu_delta = (cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system)
        mem_delta, net_delta_sent, net_delta_recv = mem_end.rss - mem_start.rss, net_end.bytes_sent - net_start.bytes_sent, net_end.bytes_recv - net_start.bytes_recv
        gpu_mem_delta = None
        if gpu_handle:
            gpu_mem_end = pynvml.nvmlDeviceGetMemoryInfo(gpu_handle)
            gpu_mem_delta = gpu_mem_end.used - gpu_mem_start.used

        # --- Print Results (Unchanged) ---
        print(f"✅ [DONE]  Finished step: '{func.__name__}'. Took {duration:.4f} seconds.")

        # --- SEND TO KAFKA ---
        if kafka_producer:
            topic = os.getenv("KAFKA_TOPIC", "performance-metrics")
            payload = {
                "time": datetime.now(timezone.utc).isoformat(),
                "run_id": os.getenv("RUN_ID", "local_run"),
                "namespace": os.getenv("NAMESPACE", "unknown"),
                "step_name": func.__name__,
                "duration_s": duration,
                "cpu_time_s": cpu_delta,
                "mem_change_bytes": mem_delta,
                "net_sent_bytes": net_delta_sent,
                "net_recv_bytes": net_delta_recv,
                "gpu_mem_change_bytes": gpu_mem_delta
            }
            try:
                kafka_producer.send(topic, value=payload)
            except Exception as e:
                print(f"🔴 Failed to send message to Kafka: {e}", file=sys.stderr)
        return result
    return wrapper

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
