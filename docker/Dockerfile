# Production/release builds MUST pass an immutable digest, for example:
# --build-arg NAKEURI_BASE_IMAGE=python:3.12-slim@sha256:<64-hex-digest>
ARG NAKEURI_BASE_IMAGE
FROM ${NAKEURI_BASE_IMAGE}
ARG NAKEURI_BASE_IMAGE

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH=/opt/nakeuri/bin:$PATH

RUN test -n "$NAKEURI_BASE_IMAGE" || (echo "NAKEURI_BASE_IMAGE must be digest pinned" >&2; exit 2)

WORKDIR /opt/src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m venv /opt/nakeuri \
 && /opt/nakeuri/bin/python -m pip install --upgrade pip \
 && /opt/nakeuri/bin/python -m pip install --no-cache-dir .

RUN groupadd --gid 65532 nakeuri 2>/dev/null || true \
 && useradd --uid 65532 --gid 65532 --no-create-home --shell /usr/sbin/nologin nakeuri 2>/dev/null || true
USER 65532:65532
WORKDIR /workspace
ENTRYPOINT ["nakeuri"]
CMD ["doctor"]
