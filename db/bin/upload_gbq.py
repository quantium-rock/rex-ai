import os
import time
import pandas as pd
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery
from gbq_utils import get_table_last_date, load_last_rows


PROJECT = "artful-talon-355716"
DATASET = "rex_ai"
LOCATION = "EU"

dataset_id = f"{PROJECT}.{DATASET}"
client = bigquery.Client()


def upload_tendency_volatility_data():
    DATA_PATH = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../", "data", "merge")
    )
    DIRS = ["tendency", "volatility"]

    # try:
    #     client.create_dataset(bigquery.Dataset(dataset_id), timeout=30)
    #     print(f"Created empty dataset {dataset_id}")
    # except Exception:
    #     print(f"Dataset {dataset_id} exists")

    for d in DIRS:
        path = os.path.join(DATA_PATH, d)

        last_gbq_date = get_table_last_date(client, dataset_id, d)

        for file in os.listdir(path):

            N = 28
            if d == "tendency":
                N = 8

            start_time = time.time()

            data = pd.read_csv(os.path.join(path, file), index_col=0)

            data = data.iloc[:, :N]

            data.index = pd.to_datetime(data.index)
            data.index.name = "DATE_TIME"

            extended_dict = {"DATE_TIME": [], "CURRENCY": [], "VALUE": []}

            for row in data.iterrows():
                extended_dict["DATE_TIME"] += [row[0]] * N
                extended_dict["CURRENCY"] += row[1].index.to_list()
                extended_dict["VALUE"] += row[1].values.tolist()

            print([len(extended_dict[key]) for key in extended_dict.keys()])
            FIRST_VALID_HOUR = last_gbq_date or datetime(
                2010, 1, 1, 0, 0, 0, 0, timezone.utc
            )
            LAST_VALID_HOUR = datetime.now(timezone.utc)
            date_diff = LAST_VALID_HOUR - FIRST_VALID_HOUR
            hour_diff = date_diff.seconds // 3600

            data = data.loc[FIRST_VALID_HOUR + timedelta(0, 3600) : LAST_VALID_HOUR]

            extended_data = pd.DataFrame(extended_dict)
            extended_data.set_index("DATE_TIME", inplace=True)
            extended_data.index = pd.to_datetime(extended_data.index, utc=True)
            extended_data.index.name = "DATE_TIME"
            extended_data = extended_data.loc[
                datetime(2010, 1, 1, 0, 0, 0, 0, timezone.utc) : LAST_VALID_HOUR
            ]

            job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")

            if hour_diff > 0 and len(data) > 0:
                print(f"Uploading last {hour_diff} hours from {file} to {dataset_id}")

                try:
                    job = client.load_table_from_dataframe(
                        data,
                        f"{dataset_id}.{d}",
                        job_config=job_config,
                    )  # Make an API request.
                    job.result()
                except Exception as e:
                    print(e)

                print(f"Uploaded successfully in {round(time.time() - start_time, 2)}s")

            else:
                print(f"{dataset_id}.{d} up to date")

            print(f"Uploading last {hour_diff} hours from {file} to {dataset_id}")

            try:
                job = client.load_table_from_dataframe(
                    extended_data,
                    f"{dataset_id}.{d}_ext",
                    job_config=job_config,
                )  # Make an API request.
                job.result()
            except Exception as e:
                print(e)

            print(f"Uploaded successfully in {round(time.time() - start_time, 2)}s")

    return


def upload_csv_data(parent: str, files: list, year: int = 2022):
    DATA_PATH = os.path.normpath(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../",
            "data",
            parent,
            str(year),
        )
    )

    FILES = files

    try:
        client.create_dataset(bigquery.Dataset(dataset_id), timeout=30)
        print(f"Created empty dataset {dataset_id}")
    except Exception:
        print(f"Dataset {dataset_id} exists")

    for f in FILES:

        file_name = f"{f}.csv"
        last_gbq_date = get_table_last_date(client, dataset_id, f)
        start_time = time.time()

        path = os.path.join(DATA_PATH, file_name)

        try:
            data = pd.read_csv(path, index_col=0)
        except FileNotFoundError:
            print(f"File {file_name} not found")
            return

        data.index = pd.to_datetime(data.index)
        data.index.name = "DATE_TIME"
        FIRST_VALID_HOUR = last_gbq_date or datetime(
            2010, 1, 1, 0, 0, 0, 0, timezone.utc
        )
        LAST_VALID_HOUR = datetime.now(timezone.utc)
        date_diff = LAST_VALID_HOUR - FIRST_VALID_HOUR
        hour_diff = date_diff.seconds // 3600

        data = data.loc[FIRST_VALID_HOUR + timedelta(0, 3600) : LAST_VALID_HOUR]

        if hour_diff > 0 and len(data) > 0:
            print(f"Uploading last {hour_diff} hours from {file_name} to {dataset_id}")

            try:
                job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
                job = client.load_table_from_dataframe(
                    data,
                    f"{dataset_id}.{f}",
                    job_config=job_config,
                )  # Make an API request.
                job.result()
            except Exception as e:
                print(e)

            print(f"Uploaded successfully in {round(time.time() - start_time, 2)}s")
        else:
            print(f"{dataset_id}.{f} up to date")

    return


def upload_dataframe(df: pd.DataFrame, name: str):

    try:
        client.create_dataset(bigquery.Dataset(dataset_id), timeout=30)
        print(f"Created empty dataset {dataset_id}")
    except Exception:
        print(f"Dataset {dataset_id} exists")

    last_gbq_date = get_table_last_date(client, dataset_id, name)
    start_time = time.time()

    df.index = pd.to_datetime(df.index)
    df.index.name = "DATE_TIME"
    FIRST_VALID_HOUR = last_gbq_date or max(
        datetime(2010, 1, 1, 0, 0, 0, 0, timezone.utc), df.index[0]
    )
    df = df.loc[FIRST_VALID_HOUR + timedelta(0, 3600) :]

    if len(df) > 0:
        print(f"Uploading last {len(df)} hours from {name} to {dataset_id}")

        try:
            job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
            job = client.load_table_from_dataframe(
                df,
                f"{dataset_id}.{name}",
                job_config=job_config,
            )  # Make an API request.
            job.result()
        except Exception as e:
            print(e)

        print(f"Uploaded successfully in {round(time.time() - start_time, 2)}s")
    else:
        print(f"{dataset_id}.{name} up to date")

    return


if __name__ == "__main__":
    # pass
    # upload_csv_data("primary", ["closes"])
    # upload_csv_data("tertiary", ["logs_"])
    upload_tendency_volatility_data()
