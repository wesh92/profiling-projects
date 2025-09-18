import time
import os
import sys
import json
from functools import wraps
from datetime import datetime, timezone
import psutil

try:
    import pynvml
    pynvml.nvmlInit()
    GPU_ENABLED = True
except Exception:
    GPU_ENABLED = False

class Profile:
    """
    A class-based decorator to log, profile, and optionally send metrics to Kafka.
    It maintains a singleton Kafka producer instance to avoid reconnecting.
    """
    _kafka_producer = None
    _kafka_initialized = False

    def __init__(self, kafka_logging=True):
        self.kafka_logging = kafka_logging
        # Initialize Kafka producer only on the first instantiation
        # that requires it.
        if self.kafka_logging and not Profile._kafka_initialized:
            self._init_kafka_producer()

    def _init_kafka_producer(self):
        """Initializes the Kafka producer using environment variables."""
        if Profile._kafka_initialized:
            return

        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        if not bootstrap_servers:
            print("🔴 KAFKA_BOOTSTRAP_SERVERS env var not set. Kafka producer disabled.", file=sys.stderr)
            Profile._kafka_initialized = True
            return

        try:
            from kafka import KafkaProducer
            Profile._kafka_producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=3
            )
            print(f"📦 Successfully connected to Kafka at {bootstrap_servers}.")
        except Exception as e:
            print(f"🔴 Could not connect to Kafka: {e}", file=sys.stderr)
            Profile._kafka_producer = None
        finally:
            Profile._kafka_initialized = True

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"▶️  [START] Running step: '{func.__name__}'...")
            proc = psutil.Process(os.getpid())
            cpu_start = proc.cpu_times()
            mem_start = proc.memory_info()
            net_start = psutil.net_io_counters()
            gpu_handle, gpu_mem_start = None, None
            if GPU_ENABLED:
                try:
                    gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    gpu_mem_start = pynvml.nvmlDeviceGetMemoryInfo(gpu_handle)
                except Exception:
                    pass

            start_time = time.monotonic()
            result = func(*args, **kwargs)
            end_time = time.monotonic()

            duration = end_time - start_time
            cpu_end, mem_end, net_end = proc.cpu_times(), proc.memory_info(), psutil.net_io_counters()
            cpu_delta = (cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system)
            mem_delta = mem_end.rss - mem_start.rss
            net_delta_sent = net_end.bytes_sent - net_start.bytes_sent
            net_delta_recv = net_end.bytes_recv - net_start.bytes_recv
            gpu_mem_delta = None
            if gpu_handle:
                gpu_mem_end = pynvml.nvmlDeviceGetMemoryInfo(gpu_handle)
                gpu_mem_delta = gpu_mem_end.used - gpu_mem_start.used

            print(f"✅ [DONE]  Finished step: '{func.__name__}'. Took {duration:.4f} seconds.")

            if self.kafka_logging and Profile._kafka_producer:
                task_instance = kwargs.get('ti') or kwargs.get('task_instance')
                if task_instance:
                    run_id, namespace, step_name = task_instance.run_id, task_instance.dag_id, task_instance.task_id
                else:
                    run_id = os.getenv("RUN_ID", "local_run")
                    namespace = os.getenv("NAMESPACE", "unknown")
                    step_name = func.__name__

                topic = os.getenv("KAFKA_TOPIC", "performance-metrics")
                payload = {
                    "time": datetime.now(timezone.utc).isoformat(),
                    "run_id": run_id, "namespace": namespace, "step_name": step_name,
                    "duration_s": duration, "cpu_time_s": cpu_delta,
                    "mem_change_bytes": mem_delta, "net_sent_bytes": net_delta_sent,
                    "net_recv_bytes": net_delta_recv, "gpu_mem_change_bytes": gpu_mem_delta
                }
                try:
                    key = f"{payload['namespace']}:{payload['run_id']}:{payload['step_name']}".encode('utf-8')
                    Profile._kafka_producer.send(topic, value=payload, key=key)
                except Exception as e:
                    print(f"🔴 Failed to send message to Kafka: {e}", file=sys.stderr)
            return result
        return wrapper
