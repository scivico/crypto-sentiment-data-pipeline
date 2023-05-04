"""
This module contains a Prefect flow for fetching news articles sentiment data from an API for a
specified time range, and storing the data in a Pandas DataFrame.
"""
from datetime import timedelta, date, datetime, timezone
from platform import node, platform

from extract_load_data import extract_load_data
from transform_data import transform_data

from prefect import flow, get_run_logger


@flow(name="Main Flow", log_prints=True)
def main(
    start_date: date = datetime.now(timezone.utc).date() - timedelta(days=1),
    end_date: date = datetime.now(timezone.utc).date(),
    block_name: str = "default",
    dataset_name: str = "crypto_data",
    bucket_name: str = "sample-bucket",
    av_api_key: str = "NDFLAIZ6VJKH5GIJ",
) -> None:
    """
    Sets up Prefect flows for fetching sentiment and market data for a specified time
    and uploading it to a GCS bucket.
    """

    logger = get_run_logger()
    logger.info("Network: %s. Instance: %s. Agent is healthy ✅️", node(), platform())

    # Convert the start and end dates to datetime objects if they are not already
    start_date = datetime.strptime("20220501", "%Y%m%d").date()

    end_date = datetime.strptime("20230501", "%Y%m%d").date()

    extract_load_data(
        start_date=start_date,
        end_date=end_date,
        block_name=block_name,
        av_api_key=av_api_key,
    )

    transform_data(
        block_name=block_name,
        dataset_name=dataset_name,
        bucket_name=bucket_name,
    )


if __name__ == "__main__":

    main()
