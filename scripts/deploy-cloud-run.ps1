param(
    [Parameter(Mandatory = $true)]
    [string] $ProjectId,

    [Parameter(Mandatory = $true)]
    [string] $PhoenixCollectorEndpoint,

    [string] $Region = "europe-west1",
    [string] $ServiceName = "phoenix-reflex"
)

$ErrorActionPreference = "Stop"

gcloud config set project $ProjectId
gcloud run deploy $ServiceName `
    --source . `
    --region $Region `
    --allow-unauthenticated `
    --set-env-vars "PHOENIX_PROJECT_NAME=phoenix-reflex,PHOENIX_COLLECTOR_ENDPOINT=$PhoenixCollectorEndpoint" `
    --set-secrets "PHOENIX_API_KEY=PHOENIX_API_KEY:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest"
