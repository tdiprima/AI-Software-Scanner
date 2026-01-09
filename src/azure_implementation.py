#!/usr/bin/env python3
"""
AI Software Scanner (Azure OpenAI)

Reads an Excel file of approved software and uses Azure OpenAI to determine
which ones contain embedded AI features that need security review.

Usage:
    python azure_implementation.py software_inventory.xlsx  # Uses MASTER Spreadsheet
    python azure_implementation.py software_inventory.xlsx --sheet "Dental School"  # Specific sheet
    python azure_implementation.py software_inventory.xlsx --all  # All sheets
    python azure_implementation.py software_inventory.xlsx --debug  # Show AI responses

Output:
    - Console summary
    - ai_scan_results.csv with all results

Environment Variables Required:
    AZURE_OPENAI_ENDPOINT
    AZURE_OPENAI_API_KEY
    AZURE_OPENAI_DEPLOYMENT
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from openai import AzureOpenAI
from ai_scanner_core import load_software_list, scan_software, save_results


def main():
    if len(sys.argv) < 2:
        print("Usage: python azure_implementation.py <file.xlsx> [--sheet NAME | --all | --debug]")
        sys.exit(1)

    input_file = sys.argv[1]
    sheet_name = None
    all_sheets = "--all" in sys.argv
    debug = "--debug" in sys.argv

    if "--sheet" in sys.argv:
        idx = sys.argv.index("--sheet")
        if idx + 1 < len(sys.argv):
            sheet_name = sys.argv[idx + 1]

    if not Path(input_file).exists():
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)

    # Load software list
    print(f"Loading from {input_file}...")
    software_list = load_software_list(input_file, sheet_name, all_sheets)
    print(f"Found {len(software_list)} software entries\n")

    if not software_list:
        print("No software found.")
        sys.exit(1)

    # Initialize Azure OpenAI client
    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version="2024-02-15-preview"
    )
    model = os.environ["AZURE_OPENAI_DEPLOYMENT"]

    # Scan software
    results, flagged = scan_software(client, model, software_list, debug=debug)

    # Save results
    output_file = "ai_scan_results.csv"
    save_results(results, output_file)

    # Print summary
    print("\n" + "=" * 60)
    print(f"SCAN COMPLETE - {len(results)} checked, {len(flagged)} flagged")
    print(f"Results saved to: {output_file}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
