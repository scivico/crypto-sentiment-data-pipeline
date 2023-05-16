# Fear and Greed Pipeline & Analysis for Crypto Market

This project aims to deliver an end-to-end ELT data pipeline in GCP to process sentiment and market data for over 500 different cryptocurrencies daily, load it into a staging area Cloud Storage datalake, create external tables out of it in BigQuery, run transformations with dbt, and finally present the findings in Superset.

## Tools used

- **Python**: Controls the data extraction, pre-processing, loading and transformation routines.
- **Prefect Cloud**: orchestrates all of the code flows and helps with monitoring how they perform in real-time.
- **Terraform**: sets up the GCP infrastructure and creates all the main services below.
- **Docker**: containerises the code in order to build Prefect agent VM and Cloud Run jobs.
- **Compute Engine**: runs the Prefect agent VM that fetches daily jobs and sends them to Cloud Run.
- **Artifact Registry**: stores the Docker images required to build Prefect agent VM and Cloud Run jobs.
- **Cloud Run**: receives daily jobs and executes them in a serveless environment.
- **Cloud Storage**: acts as a staging area for the raw market and token data.
- **BigQuery**: is a main data warehouse, creates external tables from the GCS bucket and the tables from dbt models.
- **dbt Core**: transforms data in BigQuery and makes it queryable for Superset.
- **GitHub**: hosts the source code and enables CI/CD with **GitHub Actions**.
- **Apache Superset**: builds analytics dashboards and visualisations for analysis.

## Data Pipeline Architecture

![ERD](https://github.com/kkuznets/crypto-fear-and-greed-analysis/assets/60260298/a9d52506-58d3-49d5-802e-ee99901e79e4)

## Why this project

As a fellow crypto enthusiast, I noticed how hard it is to fetch any detailed information about the historical market movements or news articles in the world of cryptocurrencies. There are several API providers that offer their services but most of them either don't have any free plans or have noticeable limitations on the information they can offer or the number of requests they can process.

To help combat this issue, I decided to create an automated data pipeline that would fetch the information requried to perform fear-and-greed analysis on any of the popular cryptocurrencies. It fetches current data daily by default and lets users fetch historical records for any time period.

## Tools used

- Python: Controls the data extraction, pre-processing, loading and transformation routines.
- Prefect Cloud: orchestrates all of the code flows and helps with monitoring how they perform in real-time.
- Terraform: sets up the GCP infrastructure and creates all the main services below.
- Docker: containerises the code in order to build Prefect agent VM and Cloud Run jobs.
- Compute Engine: runs the Prefect agent VM that fetches daily jobs and sends them to Cloud Run.
- Artifact Registry: stores the Docker images required to build Prefect agent VM and Cloud Run jobs.
- Cloud Run: receives daily jobs and executes them in a serveless environment.
- Cloud Storage: acts as a staging area for the raw market and token data.
- BigQuery: is a main data warehouse, creates external tables from the GCS bucket and the tables from dbt models.
- dbt Core: transforms data in BigQuery and makes it queryable for Superset by partitioning the table containing news sentiments.
- GitHub: hosts the source code and enables CI/CD with GitHub Actions.
- Apache Superset: builds analytics dashboards and visualisations for analysis.

## Dashboard Example

<img width="1438" alt="SH 2023-05-05 at 1 16 16 am" src="https://user-images.githubusercontent.com/60260298/236252056-0af255b0-18c6-475d-8a13-b6cddf7b0607.png">

## Some findings

- After investigating the correlation between public sentiment for a given token (I mostly looked at BTC, ETH and MATIC), I noticed that while positive news articles don't seem to impact the public opinion very quickly, negative press results in a very drastic decrease of the public's opinion about a cryptocurrency.
- There seems to be a delay of approximately a month between the overall token sentiment getting positive and public's opinion following it. It might be that there needs to be critical mass of positive news articles before people start paying attention to a given token again.
- Stablecoins, by their nature, were not affected by the negative press. However, several instances of failure of stablecoins to support their designed price resulted in horrible news sentiment in the past.

## To reproduce

This project aims to make it as easy as possible to copy the pipeline over and start playing with it.

- Fork this repository.
- Ensure you already have a Google Cloud project that you can use. If you don't you can create it using [this guide](https://cloud.google.com/resource-manager/docs/creating-managing-projects) from Google.
- Create a new service account with the required permissions.
  - In the Google Cloud Console, click to `Activate Cloud Shell`.
  - In the Cloud Shell, click to `Open Editor`.
  - Save the following code as a file **setup.sh**. Don't forget to edit the name of your project. Run this file with commans `sh setup.sh` from the Cloud Shell terminal it will generate a new service account key file **sa_key.json** for you.

```bash
# Create GCP account + project
export CLOUDSDK_CORE_PROJECT="YOUR-PROJECT-NAME"
export CLOUDSDK_COMPUTE_REGION=us-central1
export GCP_SA_NAME=binance-transactions
export GCP_AR_REPO=binance-transactions

# enable required GCP services:
gcloud services enable iamcredentials.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable compute.googleapis.com

# create service account named after GCP_SA_NAME variable:
gcloud iam service-accounts create $GCP_SA_NAME
export MEMBER=serviceAccount:"$GCP_SA_NAME"@"$CLOUDSDK_CORE_PROJECT".iam.gserviceaccount.com
gcloud projects add-iam-policy-binding $CLOUDSDK_CORE_PROJECT --member=$MEMBER --role="roles/run.admin"
gcloud projects add-iam-policy-binding $CLOUDSDK_CORE_PROJECT --member=$MEMBER --role="roles/compute.instanceAdmin.v1"
gcloud projects add-iam-policy-binding $CLOUDSDK_CORE_PROJECT --member=$MEMBER --role="roles/storage.admin"
gcloud projects add-iam-policy-binding $CLOUDSDK_CORE_PROJECT --member=$MEMBER --role="roles/bigquery.admin"
gcloud projects add-iam-policy-binding $CLOUDSDK_CORE_PROJECT --member=$MEMBER --role="roles/artifactregistry.admin"
gcloud projects add-iam-policy-binding $CLOUDSDK_CORE_PROJECT --member=$MEMBER --role="roles/iam.serviceAccountUser"

# create JSON credentials file as follows, then copy-paste its content into your GitHub Secret:
gcloud iam service-accounts keys create sa_key.json --iam-account="$GCP_SA_NAME"@"$CLOUDSDK_CORE_PROJECT".iam.gserviceaccount.com
```

- Copy the contents of the file **sa_key.json** that was generated in the previous step. Navigate to the Secrets & Actions section in yout GiHub repository settings and save the contents of this file as a secret **GCP_CREDENTIALS**.
- Navigate to Alpha Vantage [website](https://www.alphavantage.co/support/#api-key) and generate a free API key. Save this key as a secret **AV_API_KEY**.
- Create an Account in [Prefect Cloud 2.0](https://www.prefect.io/cloud/) if you haven't already. Create a new workspace, view your account's settings and create and copy the API url and API key for your new workspace. Save them as secrets **PREFECT_API_URL** and **PREFECT_API_KEY** respectively.
- Navigate to the GitHub Actions tab in your repository and click on action `Init Setup`. Start it with the variables that you prefer (or leave them default).
  - This step will prepare the GCP infrastructure for you, deploy the Python code to Prefect Cloud, and build and start the Prefect agent VM in order to run the Prefect flows.
  - If you edit the default variables, you might need to edit the dbt Core project settings and schema file in the folder to make sure they match all of the variables you edited.
- Once the previous step is finished, you can navigate back to your Prefect Cloud and view the flow deployments. Click on the deployment for the flow `Main Flow` and when its page opens, click to add a schedule that you prefer so that the data gets fetched regularly automatically.
  - You can also click to `Custom Run` this deployment and specify the **start_date** and **end_date** parameters in order to fetch historical data for a time period of your choice. Make sure you enter them in the format **%Y%m%d**, i.e **20221127**. This functionality requires the **sentiments_t** table to be partitioned by dbt in order to make queries on it from Superset more efficient.
- That's it! The transformed data will be available in BigQuery after the first deployment run. News sentiments data will be located in the table **sentiments_t** and token price information will be located in the table **prices_t**.
- If you make any changes to the Prefect flows, dbt Core models or GitHub Actions workflows, you should run the GitHub action `Reset Setup` that will re-build the Cloud Run jobs image and re-deploy Prefect flows.
- If you want to remove the whol setup for this project, you can run the GitHub action `Delete Setup` which will delete all GCP services that were created in the steps above.
