# deed-collector

Scrap real estate data and populate your tracker with it.

## Google Sheets API configuration

You need credentials allowing your script to write to the spreadsheet:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).

2. Create a new project (or select an existing one).

3. In the search bar, search for **Google Sheets API** and click **Enable**.

4. Go to **IAM & Admin > Service Accounts > Create Service Account**:
    - Give it a name (e.g., `sheets-updater`).
    - Skip the optional role/permission steps and click **Done**.

5. Click on the created service account and navigate to the **Keys** tab:
    - Click **Add Key > Create new key > choose JSON**.
    - Download the file and save it in your project folder as `credentials.json` (make sure to add this to your `.gitignore`!).

6. **Important:** Copy the service account's email address (e.g., `sheets-updater@your-project.iam.gserviceaccount.com`).

7. Open your Google Sheet in your browser, click **Share**, paste that service account email, and give it **Editor** access.

## Column mapping configuration

The scraper exposes a fixed set of fields (provider, url, address, price, area,
etc.). Your spreadsheet can name those columns whatever you like. The mapping
between the two lives in a TOML file, by default `config.toml` in the current
directory.

On first run, if `config.toml` is missing, and you are in an interactive
terminal, the CLI reads your worksheet's header row and asks you which column
each field belongs to, then writes the file for you. Re-run it at any time with
`--setup`. In non-interactive sessions (CI, piped input) the built-in defaults
are used instead.

To configure it by hand, copy the example and edit the headers:

```bash
cp config.example.toml config.toml
```

```toml
[worksheet_mapping]
provider = "portal"
url = "link do ogłoszenia"
price = "cena (zł)"
area = "metraż (m²)"
# Skip a field by leaving it empty:
year_of_construction = ""
```

Keys are the scraper's internal fields; values are your worksheet headers.
Matching is case-insensitive and ignores surrounding whitespace. Point the CLI
at a different file with `--config-path/-f`.

## Usage

< TODO To be added >

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
