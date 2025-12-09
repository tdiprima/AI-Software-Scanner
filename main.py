#!/usr/bin/env python3
"""
AI Software Scanner

Reads a CSV/Excel file of approved software and uses AI to determine
which ones contain embedded AI features that need security review.

Usage:
    python ai_software_scanner.py software_list.csv
    python ai_software_scanner.py software_list.xlsx

Output:
    - Console summary
    - ai_scan_results.csv with all results
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

import anthropic
import openpyxl


def load_software_list(filepath: str) -> list[str]:
    """Load software names from CSV or Excel file."""
    software = []

    if filepath.endswith((".xlsx", ".xls")):
        wb = openpyxl.load_workbook(filepath)
        sheet = wb.active
        for row in sheet.iter_rows(min_row=2, values_only=True):  # Skip header
            if row[0]:  # First column has software name
                software.append(str(row[0]).strip())
    else:
        # Assume CSV
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if row and row[0].strip():
                    software.append(row[0].strip())

    return software


def check_for_ai(client: anthropic.Anthropic, software_name: str) -> dict:
    """
    Use Claude to determine if software contains AI features.
    Returns dict with: has_ai (bool), confidence (str), reason (str)
    """
    prompt = f"""You are a software analyst checking if applications contain AI/ML features.

For the software "{software_name}", determine if it contains any embedded AI, machine learning, 
or features that might send data to AI cloud services.

Consider things like:
- Voice transcription or speech-to-text
- AI-powered assistants or chatbots
- Machine learning models for predictions/recommendations
- AI image/document processing
- Natural language processing features
- Cloud-based AI APIs the software might use

Respond in this exact format:
HAS_AI: YES or NO or UNKNOWN
CONFIDENCE: HIGH, MEDIUM, or LOW
REASON: One sentence explaining your assessment

Be conservative - if there's reasonable chance it has AI features, say YES.
If you don't know what the software is, say UNKNOWN."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text

        # Parse response
        has_ai = "UNKNOWN"
        confidence = "LOW"
        reason = "Could not determine"

        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("HAS_AI:"):
                value = line.replace("HAS_AI:", "").strip().upper()
                if "YES" in value:
                    has_ai = "YES"
                elif "NO" in value:
                    has_ai = "NO"
                else:
                    has_ai = "UNKNOWN"
            elif line.startswith("CONFIDENCE:"):
                confidence = line.replace("CONFIDENCE:", "").strip().upper()
            elif line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()

        return {"has_ai": has_ai, "confidence": confidence, "reason": reason}

    except Exception as e:
        return {"has_ai": "ERROR", "confidence": "N/A", "reason": str(e)}


def main():
    if len(sys.argv) < 2:
        print("Usage: python ai_software_scanner.py <software_list.csv>")
        print("\nExpected CSV format:")
        print("  Software Name")
        print("  Microsoft Word")
        print("  Zoom")
        print("  ...")
        sys.exit(1)

    input_file = sys.argv[1]

    if not Path(input_file).exists():
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)

    # Load software list
    print(f"Loading software list from {input_file}...")
    software_list = load_software_list(input_file)
    print(f"Found {len(software_list)} software entries to check\n")

    if not software_list:
        print("No software found in file. Check format.")
        sys.exit(1)

    # Initialize Anthropic client
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

    # Check each software
    results = []
    flagged = []

    for i, software in enumerate(software_list, 1):
        print(
            f"[{i}/{len(software_list)}] Checking: {software}...", end=" ", flush=True
        )

        result = check_for_ai(client, software)
        result["software"] = software
        results.append(result)

        if result["has_ai"] in ("YES", "UNKNOWN"):
            flagged.append(result)
            print(f"⚠️  FLAGGED ({result['has_ai']})")
        else:
            print("✓ OK")

    # Write results to CSV
    output_file = "ai_scan_results.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Software", "Has AI", "Confidence", "Reason", "Needs Review"])
        for r in results:
            needs_review = "YES" if r["has_ai"] in ("YES", "UNKNOWN") else "NO"
            writer.writerow(
                [r["software"], r["has_ai"], r["confidence"], r["reason"], needs_review]
            )

    # Print summary
    print("\n" + "=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print(f"Total software checked: {len(results)}")
    print(f"Flagged for review:     {len(flagged)}")
    print(f"Results saved to:       {output_file}")

    if flagged:
        print("\n⚠️  SOFTWARE FLAGGED FOR AI REVIEW:")
        print("-" * 60)
        for item in flagged:
            print(f"  • {item['software']}")
            print(f"    Status: {item['has_ai']} (Confidence: {item['confidence']})")
            print(f"    Reason: {item['reason']}\n")

    print(f"\nScan completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
