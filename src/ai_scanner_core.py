"""
AI Scanner Core Module

Shared functionality for scanning software for AI features using OpenAI or Azure OpenAI.
"""

import csv
from typing import Union

import openpyxl
from openai import OpenAI, AzureOpenAI


def load_software_list(
    filepath: str, sheet_name: str = None, all_sheets: bool = False
) -> list[dict]:
    """Load software entries from Excel file."""
    software = []
    wb = openpyxl.load_workbook(filepath, data_only=True)

    if all_sheets:
        sheets_to_process = wb.sheetnames
    else:
        sheets_to_process = [sheet_name or "MASTER Spreadsheet"]

    for sheet in sheets_to_process:
        if sheet not in wb.sheetnames:
            print(f"Warning: Sheet '{sheet}' not found, skipping...")
            continue

        ws = wb[sheet]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue

        # Find column indices from header row
        header = [str(c).lower().strip() if c else "" for c in rows[0]]
        vendor_col = product_col = desc_col = status_col = None

        for i, col in enumerate(header):
            if "vendor" in col and "name" in col:
                vendor_col = i
            elif col == "product name":
                product_col = i
            elif col == "description":
                desc_col = i
            elif col == "status":
                status_col = i

        if vendor_col is None or product_col is None:
            continue

        # Process data rows
        for row in rows[1:]:
            if len(row) <= max(vendor_col, product_col):
                continue

            vendor = str(row[vendor_col] or "").strip()
            product = str(row[product_col] or "").strip()
            desc = (
                str(row[desc_col] or "").strip()
                if desc_col and len(row) > desc_col
                else ""
            )
            status = (
                str(row[status_col] or "").strip().upper()
                if status_col and len(row) > status_col
                else ""
            )

            if (
                not vendor
                or not product
                or vendor.lower() == "nan"
                or product.lower() == "nan"
            ):
                continue
            if status == "INACTIVE":
                continue
            if desc.lower() == "nan":
                desc = ""

            software.append(
                {
                    "vendor": vendor,
                    "product": product,
                    "description": desc,
                    "sheet": sheet,
                }
            )

    return software


def has_data_quality_issues(entry: dict) -> bool:
    """Check if entry has data quality issues requiring review."""
    # Check for missing data
    if not entry.get("vendor") or not entry.get("product"):
        return True

    # Check for Excel error values
    error_values = ["#REF!", "#N/A", "#VALUE!", "#DIV/0!", "#NAME?", "#NUM!", "#NULL!"]
    for field in ["vendor", "product", "description"]:
        value = str(entry.get(field, ""))
        if any(err in value for err in error_values):
            return True

    return False


def check_for_ai(
    client: Union[OpenAI, AzureOpenAI], model: str, entry: dict, debug: bool = False
) -> dict:
    """Use OpenAI/Azure OpenAI to determine if software contains AI features."""
    software_info = f"{entry['vendor']} {entry['product']}"
    if entry["description"]:
        software_info += f"\nDescription: {entry['description']}"

    prompt = f"""You are a software analyst checking if applications contain AI/ML features.

For the following software, determine if it contains any embedded AI, machine learning,
or features that might send data to AI cloud services.

SOFTWARE:
{software_info}

Consider things like:
- Voice transcription or speech-to-text
- AI-powered assistants or chatbots (e.g., Copilot, Assistant features)
- Machine learning models for predictions/recommendations
- AI image/document processing or OCR with AI
- Natural language processing features
- Cloud-based AI APIs the software might use
- Smart/intelligent automation features
- Computer vision or image recognition

Respond in this exact format:
HAS_AI: Yes or No or Unknown
CONFIDENCE: High, Medium, or Low
REASON: One concise sentence (max 256 characters) explaining your assessment

Do not use special characters or 'smart quotes' in your response.
Be conservative - if there's a reasonable chance it has AI features, say Yes.
If you don't recognize the software, say Unknown."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content

        if debug:
            print(f"\n--- DEBUG: Raw AI Response ---")
            print(text)
            print("--- END DEBUG ---\n")

        # Parse response
        has_ai, confidence, reason = "Unknown", "Low", "Could not determine"
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("HAS_AI:"):
                value = line.replace("HAS_AI:", "").strip().upper()
                has_ai = (
                    "Yes" if "YES" in value else ("No" if "NO" in value else "Unknown")
                )
            elif line.startswith("CONFIDENCE:"):
                confidence = line.replace("CONFIDENCE:", "").strip().upper()
            elif line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()

        # Truncate reason to 256 characters if needed
        if len(reason) > 256:
            reason = reason[:253].rsplit(" ", 1)[0] + "..."

        return {"has_ai": has_ai, "confidence": confidence, "reason": reason}
    except Exception as e:
        return {"has_ai": "ERROR", "confidence": "N/A", "reason": str(e)}


def scan_software(
    client: Union[OpenAI, AzureOpenAI], model: str, software_list: list[dict], debug: bool = False
) -> tuple[list[dict], list[dict]]:
    """Scan software list for AI features and return results."""
    results, flagged = [], []

    for i, entry in enumerate(software_list, 1):
        name = f"{entry['vendor']} - {entry['product']}"
        print(f"[{i}/{len(software_list)}] {name}...", end=" ", flush=True)

        result = check_for_ai(client, model, entry, debug=debug)
        result.update(entry)
        results.append(result)

        if result["has_ai"] in ("Yes", "Unknown"):
            flagged.append(result)
            print(f"⚠️ FLAGGED ({result['has_ai']})")
        else:
            print("✓ OK")

    return results, flagged


def sanitize_csv_value(value: str) -> str:
    """Sanitize CSV values to prevent formula injection."""
    if not value:
        return value

    value_str = str(value)
    # If value starts with =, +, -, or @, prefix with apostrophe
    if value_str and value_str[0] in ("=", "+", "-", "@"):
        return "'" + value_str
    return value_str


def save_results(results: list[dict], output_file: str = "ai_scan_results.csv"):
    """Save scan results to CSV file."""
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Sheet",
                "Vendor",
                "Product",
                "Description",
                "Has AI",
                "Confidence",
                "Reason",
                "Needs Review",
            ]
        )
        for r in results:
            # Determine if needs review based on multiple factors
            needs_review = "No"
            if r["has_ai"] in ("Yes", "Unknown"):
                needs_review = "Yes"
            elif r.get("confidence", "").upper() == "LOW":
                needs_review = "Yes"
            elif has_data_quality_issues(r):
                needs_review = "Yes"

            # Sanitize values to prevent CSV formula injection
            vendor = sanitize_csv_value(r["vendor"])
            product = sanitize_csv_value(r["product"])
            description = sanitize_csv_value(r["description"])
            reason = sanitize_csv_value(r["reason"])

            writer.writerow(
                [
                    r["sheet"],
                    vendor,
                    product,
                    description,
                    r["has_ai"],
                    r["confidence"],
                    reason,
                    needs_review,
                ]
            )
