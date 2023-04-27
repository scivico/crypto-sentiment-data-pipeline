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
def get_news_sentiments(time_from: str, time_to: str, api_key: str) -> pd.DataFrame:
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
    print(f"Requesting data for {params}")
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
                article["time_published"], "%Y%m%dT%H%M%S"
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
        description="Alpha Vantage API response for sentiment data request",
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
def process_news_sentiments(start_date: date, end_date: date, av_api_key: str) -> None:
    """
    Orchestrates the daily sentiment data collection for the given time range.

    Args:
        start_date (str): The start date of the time range to retrieve.
        end_date (str): The end date of the time range to retrieve.
        av_api_key (str): The API key required to access the data.

    Returns:
        pd.DataFrame: A Pandas dataframe containing the extracted data for each news article.
    """

    # Load the GCS bucket
    gcs_bucket = GcsBucket.load("default")

    # Iterate through each day in the time range, and fetch and upload the daily sentiment data
    while start_date < end_date:
        sentiment_df = get_news_sentiments(
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

        time.sleep(13)

    return


@task(name="Get Tokens List", retries=3, retry_delay_seconds=61, log_prints=True)
def get_tokens() -> pd.DataFrame:
    """
    Fetches a list of cryptocurrency tokens from the CoinGecko API.

    Returns:
        List[str]: A list of cryptocurrency tokens.
    """

    # Send a GET request to the API endpoint and parse the JSON response
    print("Requesting tokens from CoinGecko")
    response = requests.get(
        url="https://api.coingecko.com/api/v3/coins/list",
        timeout=10,
    )

    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: Request failed with status code {response.status_code}")
    else:
        print(f"Successfully retrieved data with status code {response.status_code}")

    data = response.json()

    # Tranform the CoinGecko data and clean it
    token_ids_df = pd.DataFrame(data)
    token_ids_df = token_ids_df.rename(columns={"id": "coingecko_id"})
    token_ids_df = token_ids_df.drop_duplicates(subset=["symbol"])
    token_ids_df["symbol"] = token_ids_df["symbol"].str.upper().dropna()

    # Get the list of supported tokens from Alpha Vantage and clean it
    token_list_df = pd.read_csv(
        filepath_or_buffer="http://www.alphavantage.co/digital_currency_list/",
        storage_options={"User-Agent": "Mozilla/5.0"},
    )
    token_list_df = token_list_df.rename(columns={"currency code": "symbol"})
    token_list_df = token_list_df.drop_duplicates(subset=["symbol"])
    token_list_df = token_list_df.drop(columns={"currency name"})
    token_list_df["symbol"] = token_list_df["symbol"].str.upper().dropna()

    # Merge the two dataframes
    tokens_df = pd.merge(
        token_ids_df,
        token_list_df,
        how="inner",
        on="symbol",
    )

    # Send the extracted data to Prefect Cloud as an artifact
    create_table_artifact(
        key="sentiment-data",
        table=tokens_df.to_dict(),
        description="List of tokens to get price data for",
    )

    return tokens_df


@task(name="Get Token Prices", retries=3, retry_delay_seconds=61, log_prints=True)
def get_token_prices(start_date: date, end_date: date) -> None:
    """
    Fetches the price data from CoinGecko API for each token in the given list for
    a given time period.
    """
    # Send a GET request to the API endpoint and parse the JSON response
    print("Requesting prices from CoinGecko")
    response = requests.get(
        url="https://api.coingecko.com/api/v3/coins/list",
        timeout=10,
    )

    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: Request failed with status code {response.status_code}")
    else:
        print(f"Successfully retrieved data with status code {response.status_code}")

    data = response.json()

    # Tranform the CoinGecko data and clean it
    token_ids_df = pd.DataFrame(data)

    return


@flow(name="Process Token List", log_prints=True)
def process_token_prices(start_date: date) -> None:

    # Load the GCS bucket
    gcs_bucket = GcsBucket.load("default")

    tokens_df = get_tokens()

    gcs_bucket.upload_from_dataframe(
        tokens_df,
        f'tokens/{start_date.strftime("%Y%m%d")}',
        "parquet_gzip",
    )

    token_ids = tokens_df["coingecko_id"].tolist()

    return


@flow(name="Main Flow", log_prints=True)
def main(
    start_date: date = datetime.now(timezone.utc).date() - timedelta(days=1),
    end_date: date = datetime.now(timezone.utc).date(),
    av_api_key: str = "NDFLAIZ6VJKH5GIJ",
) -> None:
    """
    Sets up Prefect flows for fetching sentiment and market data for a specified time
    and uploading it to a GCS bucket.
    """

    # logger = get_run_logger()
    # logger.info("Network: %s. Instance: %s. Agent is healthy ✅️", node(), platform())

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

    process_news_sentiments(start_date, end_date, av_api_key)

    process_token_prices(start_date, end_date)


if __name__ == "__main__":

    main()
