# syntax=docker/dockerfile:1.4
FROM python:3.12.10-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl git libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/huggingface/hub \
    /opt/venv/bin/pip install -r requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

RUN mkdir -p app/models/trocr-base-handwritten-local && \
    cd app/models/trocr-base-handwritten-local && \
    if [ ! -f pytorch_model.bin ]; then \
      curl -fSL https://huggingface.co/microsoft/trocr-base-handwritten/resolve/main/config.json -o config.json && \
      curl -fSL https://huggingface.co/microsoft/trocr-base-handwritten/resolve/main/preprocessor_config.json -o preprocessor_config.json && \
      curl -fSL https://huggingface.co/microsoft/trocr-base-handwritten/resolve/main/pytorch_model.bin -o pytorch_model.bin; \
    fi

COPY . .

ENV FLASK_APP=run:app \
    FLASK_ENV=development \
    FLASK_RUN_HOST=0.0.0.0 

EXPOSE 5000

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["flask", "run"]