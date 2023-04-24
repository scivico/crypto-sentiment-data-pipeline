"""
This module contains a Prefect flow for fetching news articles sentiment data from an API for a
specified time range, and storing the data in a Pandas DataFrame.
"""
import time
import pandas as pd
import requests
from datetime import timedelta, date, datetime
from platform import node, platform
from prefect import flow, task, get_run_logger


@task(
    name="Get Daily Sentiment Data", retries=3, retry_delay_seconds=61, log_prints=True
)
def get_sentiment_data(time_from: str, time_to: str, api_key: str) -> pd.DataFrame:
    """
    Fetches news articles sentiment data for a specified time range from an API.

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
        print("Error: Request failed with status code %s", response.status_code)
    else:
        print("Successfully retrieved data")

    # Extract the relevant data for each article and store it in a list of dictionaries
    data = response.json()
    print(data)

    articles_data = [
        {
            "title": article["title"],
            "url": article["url"],
            "published_at": pd.to_datetime(article["time_published"]),
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

    # Return a Pandas dataframe from the extracted data
    return pd.DataFrame(articles_data)


@flow(name="Sentiment Data", log_prints=True)
def sentiment(time_from: str, time_to: str, av_api_key: str) -> pd.DataFrame:
    """
    Orchestrates the daily sentiment data collection for the given time range.

    Args:
        time_from (str): The start time of the time range to retrieve.
        time_to (str): The end time of the time range to retrieve.
        av_api_key (str): The API key required to access the data.

    Returns:
        pd.DataFrame: A Pandas dataframe containing the extracted data for each news article.
    """
    sentiment_df = pd.DataFrame()
    current_date = (
        datetime.strptime(time_from, "%Y%m%d")
        if isinstance(time_from, str)
        else time_from
    )
    end_date = (
        datetime.strptime(time_to, "%Y%m%d") if isinstance(time_to, str) else time_to
    )

    while current_date < end_date:
        next_date = current_date + timedelta(days=1)
        daily_sentiment = get_sentiment_data(
            current_date.strftime("%Y%m%d") + "T0000",
            next_date.strftime("%Y%m%d") + "T0000",
            av_api_key,
        )
        sentiment_df = sentiment_df.append(daily_sentiment, ignore_index=True)
        current_date += timedelta(days=1)
        time.sleep(12)

    print(sentiment_df.head())


def main(
    time_from: date = date.today() - timedelta(days=1),
    time_to: date = date.today(),
    av_api_key: str = "SAMPLE_KEY",
) -> None:
    """
    One flow to rule them all. Call the sub-flows to get daily sentiment and market
    data for the selected time range, then the sub-flows to upload the data to the
    GCS bucket, then the sub-flows to load the data into BigQuery and finally the
    sub-flows to run the DBT models and generate the analytics-ready data.
    """

    sentiment(time_from, time_to, av_api_key)


if __name__ == "__main__":

    logger = get_run_logger()
    logger.info("Network: %s. Instance: %s. Agent is healthy ✅️", node(), platform())

    main()
