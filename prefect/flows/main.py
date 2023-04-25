"""
This module contains a Prefect flow for fetching news articles sentiment data from an API for a
specified time range, and storing the data in a Pandas DataFrame.
"""
import time
from datetime import timedelta, date, datetime, timezone
from platform import node, platform
import pandas as pd
import requests

from prefect_gcp.cloud_storage import GcsBucket
from prefect.artifacts import create_table_artifact
from prefect import flow, task, get_run_logger


@task(name="Get Sentiment Data", retries=3, retry_delay_seconds=61, log_prints=True)
def get_sentiment_data(time_from: str, time_to: str, api_key: str) -> pd.DataFrame:
    """
    Fetches sentiment data for crypto news articles for a specified time range from the
    Alpha Vantage API.

    Args:
        time_from: The start time of the time range to retrieve, in the format "YYYYMMDDTHHMM".
        time_to: The end time of the time range to retrieve, in the format "YYYYMMDDTHHMM".
        apikey: The API key required to access the data.

    Returns:
        pd.DataFrame: A Pandas dataframe containing the extracted data for each news article.
    """

    # Define the API endpoint URL with the necessary parameters
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "topics": "blockchain",
        "apikey": api_key,
        "time_from": time_from,
        "time_to": time_to,
        "sort": "RELEVANCE",
        "limit": "200",
    }

    # Send a GET request to the API endpoint and parse the JSON response
    print("Requesting data for %s", params)
    response = requests.get(
        url,
        params=params,
        timeout=10,
    )

    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: Request failed with status code {response.status_code}")
    else:
        print(f"Successfully retrieved data with status code {response.status_code}")

    # Extract the relevant data for each article and store it in a list of dictionaries
    data = response.json()
    articles_data = [
        {
            "title": article["title"],
            "url": article["url"],
            "published_at": datetime.strptime(
                article["time_published"],
                "%Y%m%dT%H%M%S",
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "source": article["source"],
            "source_domain": article["source_domain"],
            "relevance_score": next(
                (
                    t["relevance_score"]
                    for t in article["topics"]
                    if t["topic"] == "Blockchain"
                ),
                None,
            ),
            "overall_sentiment_score": article["overall_sentiment_score"],
            "overall_sentiment_label": article["overall_sentiment_label"],
            "ticker_sentiment": article["ticker_sentiment"],
        }
        for article in data["feed"]
    ]

    # Send the extracted data to Prefect Cloud as an artifact
    create_table_artifact(
        key="sentiment-data",
        table=articles_data,
        description=f"Alpha Vantage API response for {params}",
    )

    # Convert the sentiment data to a Pandas dataframe
    sentiment_df = pd.DataFrame(articles_data).astype(
        {
            "published_at": "datetime64[ns]",
            "relevance_score": "float64",
            "overall_sentiment_score": "float64",
        }
    )

    # Return the Pandas dataframe from the extracted data
    return sentiment_df


@flow(name="Process Sentiment Data", log_prints=True)
def process_sentiment_data(
    start_date: date,
    end_date: date,
    av_api_key: str,
) -> None:
    """
    Orchestrates the daily sentiment data collection for the given time range.

    Args:
        start_date (str): The start date of the time range to retrieve.
        end_date (str): The end date of the time range to retrieve.
        av_api_key (str): The API key required to access the data.

    Returns:
        pd.DataFrame: A Pandas dataframe containing the extracted data for each news article.
    """

    # Convert the start and end dates to datetime objects if they are not already
    start_date = (
        start_date
        if isinstance(start_date, date)
        else datetime.strptime(start_date, "%Y%m%d")
    )
    end_date = (
        end_date
        if isinstance(end_date, date)
        else datetime.strptime(end_date, "%Y%m%d")
    )

    # Load the GCS bucket
    gcs_bucket = GcsBucket.load("default")

    # Iterate through each day in the time range, and fetch and upload the sentiment data
    while start_date < end_date:
        sentiment_df = get_sentiment_data(
            start_date.strftime("%Y%m%d") + "T0000",
            start_date.strftime("%Y%m%d") + "T2359",
            av_api_key,
        )

        gcs_bucket.upload_from_dataframe(
            sentiment_df,
            f'sentiment/{start_date.strftime("%Y%m%d")}',
            "parquet_gzip",
        )

        start_date += timedelta(days=1)

        time.sleep(12)


@flow(name="Main Flow", log_prints=True)
def main(
    start_date: date = datetime.now(timezone.utc).date() - timedelta(days=1),
    end_date: date = datetime.now(timezone.utc).date(),
    av_api_key: str = "SAMPLE_KEY",
) -> None:
    """
    Sets up Prefect flows for fetching sentiment and market data for a specified time
    and uploading it to a GCS bucket.
    """

    logger = get_run_logger()
    logger.info("Network: %s. Instance: %s. Agent is healthy ✅️", node(), platform())

    process_sentiment_data(start_date, end_date, av_api_key)


if __name__ == "__main__":

    main()
