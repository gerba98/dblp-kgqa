# BASE STAGE ------------------------------------------------------------------
FROM python:3.12-slim-trixie AS base

COPY --from=ghcr.io/astral-sh/uv:0.10.2 /uv /uvx /bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        apt-transport-https ca-certificates gnupg curl \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
        | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
        > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-cloud-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && chown $USERNAME:$USERNAME /app


# DEV STAGE -------------------------------------------------------------------
FROM base AS dev

RUN ln -sf /bin/bash /bin/sh

RUN apt-get update \
    && apt-get install -y git sudo curl bash-completion \
    && rm -rf /var/lib/apt/lists/*

ARG USERNAME=devuser

RUN echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

USER $USERNAME

COPY --chown=$USERNAME:$USERNAME pyproject.toml uv.lock ruff.toml ./

RUN uv sync --locked --no-install-project

CMD ["bash", "-c", "uv sync --locked && sleep infinity"]


# PROD STAGE ------------------------------------------------------------------
FROM base AS prod

ARG USERNAME=devuser

USER $USERNAME

COPY --chown=$USERNAME:$USERNAME pyproject.toml uv.lock ./
COPY --chown=$USERNAME:$USERNAME src/ src/
COPY --chown=$USERNAME:$USERNAME scripts/init_data.py scripts/

RUN uv sync --frozen --no-dev

CMD ["sleep", "infinity"]
