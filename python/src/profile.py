import time
import os
import sys
import json
from functools import wraps
from datetime import datetime, timezone
import psutil
import tracemalloc
import cProfile
import pstats
import io
from logging import log, INFO, WARNING
from typing import TypeVar, ParamSpec, Callable

try:
    import pynvml
    pynvml.nvmlInit()
    GPU_ENABLED = True
except Exception:
    GPU_ENABLED = False

# Define generic type variables to preserve function signatures
P = ParamSpec("P")
R = TypeVar("R")

class Profile:
    """
    A class-based decorator to log, profile, and optionally send metrics to Kafka.
    It maintains a singleton Kafka producer instance to avoid reconnecting.
    """
    _kafka_producer = None
    _kafka_initialized = False

    def __init__(self, kafka_logging=True, tracemalloc_enabled=False, cprofile_enabled=False):
        """
        Initializes the profiler decorator.

        Args:
            kafka_logging (bool): Enable/disable sending metrics to Kafka.
            tracemalloc_enabled (bool): Enable/disable tracemalloc for memory profiling.
            cprofile_enabled (bool): Enable/disable cProfile for function time profiling.
        """
        self.kafka_logging = kafka_logging
        self.tracemalloc_enabled = tracemalloc_enabled
        self.cprofile_enabled = cprofile_enabled

        # Initialize Kafka producer only on the first instantiation that requires it.
        if self.kafka_logging and not Profile._kafka_initialized:
            self._init_kafka_producer()

    def _init_kafka_producer(self):
        """Initializes the Kafka producer using environment variables."""
        if Profile._kafka_initialized:
            return

        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        if not bootstrap_servers:
            log(WARNING, "🔴 KAFKA_BOOTSTRAP_SERVERS env var not set. Kafka producer disabled.")
            Profile._kafka_initialized = True
            return

        try:
            from kafka import KafkaProducer
            Profile._kafka_producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=3
            )
            log(INFO, f"📦 Successfully connected to Kafka at {bootstrap_servers}.")
        except Exception as e:
            log(WARNING, f"🔴 Could not connect to Kafka: {e}")
            Profile._kafka_producer = None
        finally:
            Profile._kafka_initialized = True

    def __call__(self, func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            log(INFO, f"▶️  [START] Running step: '{func.__name__}'...")

            # Profiling Setup
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

            # Deep Profiling Setup
            if self.tracemalloc_enabled:
                if not tracemalloc.is_tracing():
                    tracemalloc.start()
                tracemalloc_start_snapshot = tracemalloc.take_snapshot()

            if self.cprofile_enabled:
                profiler = cProfile.Profile()
                profiler.enable()

            # Execute Function
            start_time = time.monotonic()
            result = func(*args, **kwargs)
            end_time = time.monotonic()

            # Deep Profiling Capture & Report
            cprofile_stats_str = None
            if self.cprofile_enabled:
                profiler.disable()
                s = io.StringIO()
                ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
                ps.print_stats(15) # Report top 15 functions by cumulative time
                cprofile_stats_str = s.getvalue()
                log(INFO, f"\n--- cProfile for '{func.__name__}' (top 15) ---")
                log(INFO, cprofile_stats_str)
                log(INFO, "------------------------------------------\n")

            tracemalloc_stats_list = None
            if self.tracemalloc_enabled:
                tracemalloc_end_snapshot = tracemalloc.take_snapshot()
                top_stats = tracemalloc_end_snapshot.compare_to(tracemalloc_start_snapshot, 'lineno')
                tracemalloc_stats_list = [str(s) for s in top_stats[:10]]
                log(INFO, f"--- tracemalloc for '{func.__name__}' (top 10 diffs) ---")
                for stat in tracemalloc_stats_list:
                    log(INFO, stat)
                log(INFO, "------------------------------------------\n")

            # Standard Profiling Capture
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

            log(INFO, f"✅ [DONE]  Finished step: '{func.__name__}'. Took {duration:.4f} seconds.")

            # Kafka Logging
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
                    "net_recv_bytes": net_delta_recv, "gpu_mem_change_bytes": gpu_mem_delta,
                    "deep_profiling_data": {},
                }

                # Add deep profiling metrics if they were captured
                if cprofile_stats_str:
                    payload['deep_profiling_data']['cprofile_stats'] = cprofile_stats_str
                if tracemalloc_stats_list:
                    payload['deep_profiling_data']['tracemalloc_top_10_diff'] = tracemalloc_stats_list

                try:
                    key = f"{payload['namespace']}:{payload['run_id']}:{payload['step_name']}".encode('utf-8')
                    Profile._kafka_producer.send(topic, value=payload, key=key)
                except Exception as e:
                    log(WARNING, f"🔴 Failed to send message to Kafka: {e}")

            return result
        return wrapper
