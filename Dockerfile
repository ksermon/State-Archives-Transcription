FROM python:3.12.1-slim

WORKDIR /app

RUN apt-get update 

RUN apt-get install -y curl

RUN mkdir -p app/models/trocr-base-handwritten-local && \
    echo "Downloading model files..." && \
    curl -L https://huggingface.co/microsoft/trocr-base-handwritten/resolve/main/config.json -o app/models/trocr-base-handwritten-local/config.json && \
    curl -L https://huggingface.co/microsoft/trocr-base-handwritten/resolve/main/preprocessor_config.json -o app/models/trocr-base-handwritten-local/preprocessor_config.json && \
    curl -L https://huggingface.co/microsoft/trocr-base-handwritten/resolve/main/pytorch_model.bin -o app/models/trocr-base-handwritten-local/pytorch_model.bin && \
    echo "Model files downloaded."

RUN apt-get install -y git

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get install -y libgl1 libglib2.0-0

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=development 
ENV FLASK_RUN_HOST=0.0.0.0 

EXPOSE 5000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["flask", "run"]