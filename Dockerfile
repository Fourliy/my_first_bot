FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY bot ./bot
COPY scripts ./scripts
RUN uv sync --frozen --no-dev
CMD ["uv", "run", "--no-dev", "python", "-m", "my_first_bot.runner"]
