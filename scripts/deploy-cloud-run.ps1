param(
    [Parameter(Mandatory = $true)]
    [string] $ProjectId,

    [string] $ArizeOtelEndpoint = "https://otlp.eu-west-1a.arize.com/v1",
    [string] $Region = "europe-west1",
    [string] $ServiceName = "phoenix-reflex",
    [string] $PhoenixHost = $env:PHOENIX_HOST
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($PhoenixHost)) {
    throw "PHOENIX_HOST is required. Pass -PhoenixHost or set PHOENIX_HOST in the environment."
}

gcloud config set project $ProjectId
gcloud run deploy $ServiceName `
    --source . `
    --region $Region `
    --allow-unauthenticated `
    --set-env-vars "ARIZE_PROJECT_NAME=phoenix-reflex,ARIZE_OTEL_ENDPOINT=$ArizeOtelEndpoint,GEMINI_MODEL=gemini-3.5-flash,ENABLE_PHOENIX_MCP=1,PHOENIX_HOST=$PhoenixHost" `
    --set-secrets "ARIZE_API_KEY=ARIZE_API_KEY:latest,ARIZE_SPACE_ID=ARIZE_SPACE_ID:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest,GOOGLE_API_KEY=GEMINI_API_KEY:latest,PHOENIX_API_KEY=PHOENIX_API_KEY:latest"
