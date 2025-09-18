-- 1. Create the table for performance metrics
CREATE TABLE performance_metrics (
    time TIMESTAMPTZ NOT NULL,
    run_id VARCHAR(64) NOT NULL,
    step_name TEXT NOT NULL,
    duration_s DOUBLE PRECISION NOT NULL,
    cpu_time_s DOUBLE PRECISION,
    mem_change_bytes BIGINT,
    net_sent_bytes BIGINT,
    net_recv_bytes BIGINT,
    gpu_mem_change_bytes BIGINT
);

-- 2. Convert it into a TimescaleDB hypertable, partitioned by the 'time' column
SELECT create_hypertable('performance_metrics', by_range('time'));

-- 3. Create an index for faster queries on step_name and run_id
CREATE INDEX ix_step_run ON performance_metrics (step_name, run_id, time DESC);
