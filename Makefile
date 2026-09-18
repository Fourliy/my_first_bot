venv:
    python -m venv .venv

install:
    .venv/bin/python -m pip install uv
    .venv/bin/uv install .

run:
    .venv/bin/python -m my_first_bot.runner

docker-build:
    docker build -t my_first_bot:local .

docker-run:
    docker run --rm --env-file .env my_first_bot:local

clean:
    rm -rf .venv