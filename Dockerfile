FROM python:3.12.14-slim-bookworm

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 easy-verifier \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin easy-verifier \
    && mkdir -p /workspace/reports \
    && chown -R 10001:10001 /workspace \
    && git config --system --add safe.directory '*'

# The engine runs git with GIT_CONFIG_NOSYSTEM=1 and no HOME, so the system
# setting above never reaches it; command-line config does. The mounted
# repositories belong to the host user, not UID 10001 (T101).
RUN printf '#!/bin/sh\nexec /usr/bin/git -c "safe.directory=*" "$@"\n' > /usr/local/bin/git \
    && chmod 0755 /usr/local/bin/git

WORKDIR /opt/easy-verifier
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install "mcp==1.29.1" .

USER 10001:10001
WORKDIR /workspace

ENTRYPOINT ["easy-verifier-mcp"]
