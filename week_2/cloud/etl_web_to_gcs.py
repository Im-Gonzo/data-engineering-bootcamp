from pathlib import Path
from prefect import flow, task
from prefect_gcp.cloud_storage import GcsBucket
import pandas as pd
import os
import sys


@task(log_prints=True)
def filename_from_url(url: str) -> str:
    """Extract filename from url that downloads a .parquet file"""
    try:
        output = url.split('/')
        output = output[4].replace('.parquet', '').replace('-', '_')
        return output
    except ValueError as e:
        print('The url doesnt have the correct format')
        print(e)
        return sys.exit(1)


@task(log_prints=True)
def clean_data(df: pd.DataFrame, filename: str) -> str:
    """Gets rid of record without passengers"""
    path = f'dataset/{filename}'
    print(f"Pre Missing passenger count: {df['passenger_count'].isin([0]).sum()}")
    df = df[df['passenger_count'] != 0]
    print(f"Post Missing passenger count: {df['passenger_count'].isin([0]).sum()}")
    df.to_parquet(path, engine='pyarrow')
    return path


@task()
def extract_data(url: str, file_name: str) -> pd.DataFrame:
    """Downloads a parquet file and returns it as a pandas Dataframe"""
    try:
        os.system(f'curl {url} -o dataset/{file_name}')
        df = pd.read_parquet(f'dataset/{file_name}', engine='pyarrow')
        return df
    except ValueError as e:
        print(e)
        return sys.exit(1)


@task()
def write_gcs(path: Path, filename: str):
    """Loads a GCS block with our credentials and uploads the file to our GCS Bucket"""
    gcs_block = GcsBucket.load("datatalks-bootcamp")
    gcs_block.upload_from_path(from_path=path, to_path=filename)
    return


@flow()
def etl_web_to_gcs() -> None:
    url = 'https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2022-09.parquet'
    file_name = filename_from_url(url)
    df = extract_data(url, file_name)
    path = clean_data(df, file_name)
    write_gcs(path, file_name)


if __name__ == '__main__':
    etl_web_to_gcs()
