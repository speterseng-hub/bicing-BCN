from google.cloud import bigquery

client = bigquery.Client(project="elite-coral-496815-s5")
result = list(client.query(
    "SELECT COUNT(*) as filas, MIN(timestamp) as desde, MAX(timestamp) as hasta "
    "FROM bicing_analytics.bicing_raw"
).result())
print(result[0])
