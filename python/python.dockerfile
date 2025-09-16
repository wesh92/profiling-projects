FROM python:3.12-slim as builder

# Install uv first (rarely changes)
RUN pip install --no-cache-dir uv

WORKDIR /build

COPY ./pyproject.toml .
RUN uv pip compile pyproject.toml

COPY ./python/timing_test.py .

CMD ["uv", "run", "timing_test.py"]
