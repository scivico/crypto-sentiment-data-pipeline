import pandas as pd
import requests
from platform import node, platform
from prefect import flow, task, get_run_logger


@flow(name="Sentiment Data")
def sentiment_data(
    time_from: str,
    time_to: str,
    api_key: str,
) -> pd.DataFrame:
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
        return None

    # Extract the relevant data for each article and store it in a list of dictionaries
    print("Successfully retrieved data")
    data = response.json()

    articles_data = [
        {
            "title": article["title"],
            "url": article["url"],
            "published_at": pd.to_datetime(article["time_published"]),
            "authors": article["authors"],
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


@flow(name="Main", log_prints=True)
def main(
    time_from: str = "20220410T0130",
    time_to: str = "20220415T0130",
    av_api_key: str = "AV_API_KEY",
) -> None:
    """
    One flow to rule them all. Call the sub-flows to get daily sentiment and market
    data for the selected time range, then the sub-flows to upload the data to the
    GCS bucket, then the sub-flows to load the data into BigQuery and finally the
    sub-flows to run the DBT models and generate the analytics-ready data.
    """

    sentiment = sentiment_data(
        time_from,
        time_to,
        av_api_key,
    )
    print(sentiment.head())


if __name__ == "__main__":

    logger = get_run_logger()
    logger.info("Network: %s. Instance: %s. Agent is healthy ✅️", node(), platform())

    main()
