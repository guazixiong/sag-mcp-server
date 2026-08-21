FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY src/ ./src/

EXPOSE 9003

ENTRYPOINT ["sag-mcp-server"]
CMD ["http", "9003"]
