FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY . /app
RUN python -m pip install uv && uv install .
CMD ["python", "-m", "my_first_bot.runner"]