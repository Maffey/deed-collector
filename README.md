# deed-collector

Scrape a real estate listing and write it into a Google Sheets tracker.

## Google Sheets setup

You need a service account that's allowed to write to your spreadsheet.

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or pick an existing one).
3. Search for **Google Sheets API** and click **Enable**.
4. Go to **IAM & Admin > Service Accounts > Create Service Account**. Name it
   something like `sheets-updater`, skip the optional roles, click **Done**.
5. Open the account, go to **Keys > Add Key > Create new key > JSON**. Save the
   downloaded file as `credentials.json` in the project folder, and put it in
   your `.gitignore`.
6. Copy the service account email
   (`sheets-updater@your-project.iam.gserviceaccount.com`).
7. Open your spreadsheet, click **Share**, paste that email in, give it
   **Editor**.

## Configuration

Config is a TOML file — `config.toml` by default. Point the CLI somewhere else
with `--config-path/-f`. There are two tables: `[worksheet]` for the target
spreadsheet, and `[worksheet_mapping]` for how scraped fields line up with your
columns.

### Worksheet target

Instead of passing the target on the command line every time, put it in
`[worksheet]`:

```toml
[worksheet]
spreadsheet_id = "1AbC..."
sheet_name = "Sheet1"
header_row = 1
```

All three keys are optional. When a value is set in more than one place, the CLI
wins, then the config file, then the defaults:

| Config key       | CLI equivalent             | Default  |
| ---------------- | -------------------------- | -------- |
| `spreadsheet_id` | second positional argument | required |
| `sheet_name`     | `--sheet-name`/`-w`        | `Sheet1` |
| `header_row`     | `--header-row`/`-r`        | `1`      |

The listing `url` only ever comes from the CLI. It's not read from config.

### Column mapping

The scraper produces a fixed set of fields (provider, url, address, price, area,
etc.). Your sheet can name those columns whatever you want. `[worksheet_mapping]`
connects the two.

On a first run with no `config.toml`, in an interactive terminal, the CLI reads
your sheet's header row and asks where each field goes, then writes the file for
you. Run it again whenever with `--setup`. In non-interactive sessions (CI, piped
input) the built-in defaults are used instead.

To set it up by hand:

```bash
cp config.example.toml config.toml
```

```toml
[worksheet]
spreadsheet_id = "1AbC..."
sheet_name = "Sheet1"

[worksheet_mapping]
provider = "portal"
url = "link do ogłoszenia"
price = "cena (zł)"
area = "metraż (m²)"
# Skip a field by leaving it empty:
year_of_construction = ""
```

Keys are the scraper's fields; values are your sheet's headers. Matching ignores
case and surrounding whitespace.

## Usage

With `credentials.json` and a `config.toml` describing your sheet, pass a
listing URL:

```bash
uv run deed-collector "https://www.otodom.pl/pl/oferta/some-listing"
```

The listing is fetched, parsed, and appended as a new row. `url` and
`spreadsheet_id` are positional; the id is optional when it's already in
`config.toml`:

```bash
uv run deed-collector "https://www.otodom.pl/pl/oferta/some-listing" "1AbC..."
```

Only **Otodom** (`otodom.pl`) works right now. A URL from any other host fails
before anything is written.

### Options

| Option                      | Short | Description                                                                            |
| --------------------------- | ----- | -------------------------------------------------------------------------------------- |
| `--sheet-name <name>`       | `-w`  | Worksheet tab to write to. Overrides `[worksheet].sheet_name`.                         |
| `--header-row <n>`          | `-r`  | 1-based row holding the column headers (`n >= 1`). Overrides `[worksheet].header_row`. |
| `--config-path <file>`      | `-f`  | TOML config file to read. Defaults to `config.toml` in the current directory.          |
| `--credentials-path <file>` | `-c`  | Service account JSON key. Defaults to `credentials.json` in the project folder.        |
| `--setup`                   |       | Re-run the interactive column-mapping wizard, then continue with the scrape.           |
| `--help`                    |       | Show the full help text and exit.                                                      |

### Examples

Write to a different tab whose headers live on row 2:

```bash
uv run deed-collector "https://www.otodom.pl/pl/oferta/some-listing" -w "Flats" -r 2
```

Use a config file and credentials stored outside the project folder:

```bash
uv run deed-collector "https://www.otodom.pl/pl/oferta/some-listing" \
  -f ./my-config.toml -c ./secrets/service-account.json
```

Rebuild the column mapping after changing your sheet's headers:

```bash
uv run deed-collector "https://www.otodom.pl/pl/oferta/some-listing" --setup
```

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
