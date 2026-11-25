# AI Software Scanner

A Python command-line tool that audits a spreadsheet of approved software and flags every product with embedded AI features, so security reviewers know exactly what to look at.

## AI Is Quietly Shipping Inside Software You Already Approved

Security teams approve software once, then vendors keep changing it. A note-taking app adds voice transcription. An office suite adds a copilot. A PDF tool starts sending documents to a cloud model for OCR. Each of those updates can move sensitive data to a third-party AI service without anyone on the review team hearing about it.

Tracking this by hand does not scale. An approved-software inventory can hold hundreds of entries across several sheets, and vendors add AI features every month. Researching each product manually takes hours, and the answer is stale by the next release cycle.

## An LLM Triage Pass Over the Whole Inventory

AI Software Scanner turns that manual research into one repeatable command:

- **Reads the inventory as it already exists.** It loads an Excel workbook, finds the vendor, product, description, and status columns by header name, and skips rows marked `INACTIVE`.
- **Asks a model one focused question per product.** Each entry goes to OpenAI or Azure OpenAI with a prompt that covers transcription, assistants and chatbots, ML predictions, AI document processing, NLP, cloud AI APIs, smart automation, and computer vision.
- **Gets a structured verdict.** Every answer is parsed into `HAS_AI` (`YES`, `NO`, or `UNKNOWN`), a confidence level, and a one-sentence reason capped at 255 characters.
- **Fails safe.** The prompt tells the model to lean toward `YES`, and anything it does not recognize is marked `UNKNOWN`. Both outcomes are flagged for human review, so an unfamiliar product never passes silently.
- **Writes a reviewer-ready CSV.** All results land in `ai_scan_results.csv` with a `Needs Review` column that can be filtered in seconds.

The scanner is a triage tool. It narrows hundreds of products down to a short list for a person to verify. It relies on the model's knowledge of each product and does not browse vendor sites.

The shared scanning logic lives in one core module, with two thin entry points on top: one for OpenAI and one for Azure OpenAI.

## From Spreadsheet to Review List

Start with an inventory sheet like this:

| Vendor Name | Product Name | Description | Status |
| --- | --- | --- | --- |
| Microsoft | Office 365 | Productivity suite | ACTIVE |
| Otter.ai | Otter | Meeting notes | ACTIVE |
| 7-Zip | 7-Zip | File archiver | ACTIVE |
| Acme Corp | LegacyTool | Internal utility | INACTIVE |

Run the scan:

```sh
uv run src/ai_software_scanner.py software_inventory.xlsx
```

The console shows progress as each product is checked:

```
2026-11-25 09:14:02 INFO Loading from software_inventory.xlsx...
2026-11-25 09:14:02 INFO Found 3 software entries
2026-11-25 09:14:02 INFO [1/3] Microsoft - Office 365
2026-11-25 09:14:05 INFO   FLAGGED (YES)
2026-11-25 09:14:05 INFO [2/3] Otter.ai - Otter
2026-11-25 09:14:07 INFO   FLAGGED (YES)
2026-11-25 09:14:07 INFO [3/3] 7-Zip - 7-Zip
2026-11-25 09:14:09 INFO   OK
2026-11-25 09:14:09 INFO ============================================================
2026-11-25 09:14:09 INFO SCAN COMPLETE - 3 checked, 2 flagged
2026-11-25 09:14:09 INFO Results saved to: ai_scan_results.csv
```

And `ai_scan_results.csv` holds the full record:

| Sheet | Vendor | Product | Description | Has AI | Confidence | Reason | Needs Review |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MASTER Spreadsheet | Microsoft | Office 365 | Productivity suite | YES | HIGH | Includes Copilot, an AI assistant that processes document content in the cloud. | YES |
| MASTER Spreadsheet | Otter.ai | Otter | Meeting notes | YES | HIGH | Core product is AI speech-to-text transcription and meeting summaries. | YES |
| MASTER Spreadsheet | 7-Zip | 7-Zip | File archiver | NO | HIGH | Local file compression utility with no AI or cloud features. | NO |

The output above is illustrative. Model answers vary between runs. The inactive row was skipped before any API call was made.

## Getting Started

### Requirements

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/)
- An OpenAI API key, or an Azure OpenAI resource with a chat deployment

### Install

```sh
git clone https://github.com/tdiprima/AI-Software-Scanner.git
cd AI-Software-Scanner
uv sync
```

### Configure credentials

Copy the template and fill in the values for the provider you use:

```sh
cp .env.example .env
```

| Variable | Used by | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | OpenAI entry point | API key |
| `AZURE_OPENAI_ENDPOINT` | Azure entry point | Resource URL, for example `https://your-org.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | Azure entry point | API key |
| `AZURE_OPENAI_DEPLOYMENT` | Azure entry point | Name of the chat model deployment |
| `LOG_LEVEL` | Both | Optional. Defaults to `INFO` |

The scripts read these from the environment and do not load `.env` on their own. Pass the file with `--env-file`, or `export` the variables in your shell. Keep `.env` out of version control; it is already in `.gitignore`.

### Prepare the spreadsheet

The workbook needs a header row with these columns. Matching is case-insensitive.

| Column | Required | Rule |
| --- | --- | --- |
| Vendor name | Yes | Header must contain both `vendor` and `name` |
| Product name | Yes | Header must be exactly `Product Name` |
| Description | No | Header must be exactly `Description`. Sent to the model as extra context |
| Status | No | Header must be exactly `Status`. Rows with `INACTIVE` are skipped |

By default the scanner reads the sheet named `MASTER Spreadsheet`. Sheets that lack the required columns are skipped with a warning.

### Run a scan

With OpenAI:

```sh
uv run --env-file .env src/ai_software_scanner.py software_inventory.xlsx
```

With Azure OpenAI:

```sh
uv run --env-file .env src/azure_implementation.py software_inventory.xlsx
```

Both entry points accept the same options:

| Option | Effect |
| --- | --- |
| `--sheet "NAME"` | Scan one named sheet instead of `MASTER Spreadsheet` |
| `--all` | Scan every sheet in the workbook |
| `--debug` | Log the raw model response for each product |

Results are written to `ai_scan_results.csv` in the current directory, replacing any earlier file. Filter on `Needs Review = YES` to get the review list.

### Run it on a schedule

Vendors add AI features all the time, so one scan goes stale. Schedule the command weekly with cron or a CI job and compare each new CSV with the last one to catch products that changed.

## License

Released under the [MIT License](LICENSE).

<br>
