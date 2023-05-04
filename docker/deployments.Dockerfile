FROM python3.10

ENV PATH="/root/.local/bin:${PATH}"

ARG PREFECT_API_KEY
ENV PREFECT_API_KEY=$PREFECT_API_KEY

ARG PREFECT_API_URL
ENV PREFECT_API_URL=$PREFECT_API_URL

ARG PREFECT_BLOCK
ENV PREFECT_BLOCK=$PREFECT_BLOCK

ARG DATASET_NAME
ENV DATASET_NAME=$DATASET_NAME

ARG BUCKET_NAME
ENV BUCKET_NAME=$BUCKET_NAME

ENV PYTHONUNBUFFERED True

WORKDIR pipeline

COPY pyproject.toml poetry.lock /

RUN apt-get update -qq && \
    apt-get -qq install \
    curl

RUN curl -sSL https://install.python-poetry.org | python - \
    && poetry config virtualenvs.create false --local \
    && poetry install --without dev --no-root

# RUN touch profiles.yml && \
#     echo "fear_and_greed_crypto_analysis:" >> profiles.yml && \
#     echo "  outputs:" >> profiles.yml && \
#     echo "    dev:" >> profiles.yml && \
#     echo "      dataset: ${GCP_DATASET_NAME}" >> profiles.yml && \
#     echo "      job_execution_timeout_seconds: 300" >> profiles.yml && \
#     echo "      job_retries: 1" >> profiles.yml && \
#     echo "      keyfile: ${PWD}/gcp-credentials.json" >> profiles.yml && \
#     echo "      location: ${GCP_RESOURCE_REGION}" >> profiles.yml && \
#     echo "      method: service-account" >> profiles.yml && \
#     echo "      priority: interactive" >> profiles.yml && \
#     echo "      project: ${GCP_PROJECT_ID}" >> profiles.yml && \
#     echo "      threads: 4" >> profiles.yml && \
#     echo "      type: bigquery" >> profiles.yml && \
#     echo "  target: dev" >> profiles.yml
