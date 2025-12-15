# Getting Started Guide

This guide will walk you through setting up a complete local development environment for BioETL. By the end of this guide, you will have a running instance of the platform and be able to execute data pipelines.

## Prerequisites

Ensure you have the following tools installed on your machine:

*   **Python 3.11** or higher: [Download](https://www.python.org/downloads/)
*   **Docker Desktop**: For running local infrastructure (Redis, Postgres, MinIO). [Download](https://www.docker.com/products/docker-desktop/)
*   **Git**: Version control.
*   **Make**: Build automation tool (usually pre-installed on Linux/macOS; for Windows, use Chocolatey or WSL).

## 1. Clone the Repository

```bash
git clone https://github.com/SatoryKono/BioactivityDataAcquisition.git
cd BioactivityDataAcquisition
```

## 2. Environment Setup

We use `make` to automate the setup process. This command will create a Python virtual environment (`.venv`) and install all production and development dependencies.

```bash
make install
```

*Note: If you are on Windows and don't have `make`, you can manually run:*
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev,docs]
```

## 3. Configuration

### Environment Variables
Copy the example environment file to create your local configuration:

```bash
cp .env.example .env
```

Open `.env` and verify the settings. For local development, the defaults are usually sufficient.

**Key Variables:**
*   `BIOETL_ENV`: Set to `dev`.
*   `BIOETL_S3_ENDPOINT`: URL for local MinIO (default: `http://localhost:9000`).
*   `BIOETL_REDIS_URL`: URL for local Redis (default: `redis://localhost:6379/0`).

### Secrets
If you plan to access APIs requiring authentication (e.g., UniProt, OpenAlex), add your keys to `.env`:

```ini
BIOETL_UNIPROT_API_KEY=your_key_here
BIOETL_OPENALEX_API_KEY=your_email@example.com
```

## 4. Start Infrastructure

Start the required services (Redis, MinIO, Postgres) using Docker Compose:

```bash
make docker-up
```

Verify that containers are running:
```bash
docker ps
```
You should see containers named `bioetl-redis`, `bioetl-minio`, etc.

## 5. Verify Installation

Run the test suite to ensure everything is correctly configured:

```bash
make test
```

If all tests pass, your environment is ready!

## 6. Running Your First Pipeline

To verify the end-to-end flow, run a sample pipeline (e.g., ChEMBL Activity).

```bash
# Ensure your virtual environment is active
source .venv/bin/activate

# Run the pipeline
python -m bioetl.main run --pipeline chembl_activity --limit 100
```

This command will:
1.  Fetch 100 records from the ChEMBL API.
2.  Save raw data to the **Bronze** layer (local MinIO).
3.  Normalize and save to the **Silver** layer (Delta Lake).

## Troubleshooting

### "Make command not found"
On Windows, ensure you have installed Make via Chocolatey (`choco install make`) or use the manual commands listed above.

### Docker Connection Errors
Ensure Docker Desktop is running. If `docker-up` fails, try restarting Docker Desktop.

### Permission Denied
If you encounter permission errors with `./docker-data/`, run `make docker-reset` to clear old volumes and start fresh.
