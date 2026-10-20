venv:
	uv venv

install:
	uv sync

run:
	uv run python -m my_first_bot.runner

index:
	uv run python scripts/index_pdf.py

docker-build:
	docker build -t my_first_bot:local .

docker-run:
	docker run --rm --env-file .env -v ./data:/app/data my_first_bot:local

clean:
	uv run python -c "import shutil; shutil.rmtree('.venv', ignore_errors=True)"
