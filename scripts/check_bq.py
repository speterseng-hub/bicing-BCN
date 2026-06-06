import os

from google.cloud import bigquery

project = os.environ.get("GCP_PROJECT_ID") or exit("Set GCP_PROJECT_ID env var")
client = bigquery.Client(project=project)
result = list(client.query(
    "SELECT COUNT(*) as filas, MIN(timestamp) as desde, MAX(timestamp) as hasta "
    "FROM bicing_analytics.bicing_raw"
).result())
print(result[0])
