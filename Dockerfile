
FROM python:3.12

ENV CONFIG_FILE="/app/src/gemini_for_github/config/default.yaml"

ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=1

ENV PATH="$POETRY_HOME/bin:$PATH"

RUN curl -sSL https://install.python-poetry.org | python3 -

RUN mkdir -p /github/workspace

RUN git config --global --add safe.directory /github/workspace

WORKDIR /app
# Copy the entrypoint script
COPY src src
COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock
COPY README.md README.md

RUN poetry install

ENTRYPOINT ["python", "/app/src/gemini_for_github/main.py"]