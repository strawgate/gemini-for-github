
FROM python:3.12-slim

WORKDIR /app

# Install poetry
RUN pipx install poetry
RUN poetry config virtualenvs.create false && poetry install --no-interaction

# Copy the entrypoint script
COPY . .

ENTRYPOINT ["python", "/app/src/gemini_for_github/main.py"]