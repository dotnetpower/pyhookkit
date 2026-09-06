FROM python:3.12-slim AS builder

WORKDIR /build
COPY examples/python/ ./
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.12-slim

RUN groupadd --gid 10001 pyhookkit \
    && useradd --uid 10001 --gid pyhookkit --create-home pyhookkit \
    && mkdir /data \
    && chown pyhookkit:pyhookkit /data
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels

USER 10001:10001
WORKDIR /data
EXPOSE 8080 8081
ENTRYPOINT ["python", "-m", "pyhookkit.entrypoints.notification_router"]
