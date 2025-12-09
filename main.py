#!/usr/bin/env python3
"""
AI Software Scanner

Reads an Excel file of approved software and uses AI to determine
which ones contain embedded AI features that need security review.

Usage:
    python main.py software_inventory.xlsx
    python main.py software_inventory.xlsx --sheet "MASTER Spreadsheet"

Output:
    - Console summary
    - ai_scan_results.csv with all results
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from openai import OpenAI


def load_software_list(filepath: str, sheet_name: str = "MASTER Spreadsheet") -> list[dict]:
    """
    Load software entries from Excel file.
    Returns list of dicts with vendor, product, and description.
    """
    software = []
    
    df = pd.read_excel(filepath, sheet_name=sheet_name)
    
    # Normalize column names (handle variations in spacing/naming)
    col_map = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if 'vendor' in col_lower and 'name' in col_lower:
            col_map['vendor'] = col
        elif col_lower == 'product name':
            col_map['product'] = col
        elif col_lower == 'description':
            col_map['description'] = col
        elif col_lower == 'status':
            col_map['status'] = col
    
    if 'vendor' not in col_map or 'product' not in col_map:
        raise ValueError(f"Could not find required columns. Found: {list(df.columns)}")
    
    for _, row in df.iterrows():
        vendor = str(row.get(col_map['vendor'], '') or '').strip()
        product = str(row.get(col_map['product'], '') or '').strip()
        description = str(row.get(col_map.get('description', ''), '') or '').strip()
        status = str(row.get(col_map.get('status', ''), '') or '').strip().upper()
        
        # Skip rows without vendor or product name
        if not vendor or not product or vendor.lower() == 'nan' or product.lower() == 'nan':
            continue
        
        # Optionally skip inactive entries
        if status == 'INACTIVE':
            continue
            
        # Clean up "nan" strings from description
        if description.lower() == 'nan':
            description = ''
        
        software.append({
            'vendor': vendor,
            'product': product,
            'description': description
        })
    
    return software


def build_software_context(entry: dict) -> str:
    """Build a descriptive string for the AI to analyze."""
    parts = [f"{entry['vendor']} {entry['product']}"]
    if entry['description']:
        parts.append(f"Description: {entry['description']}")
    return "\n".join(parts)


def check_for_ai(client: OpenAI, entry: dict) -> dict:
    """
    Use OpenAI to determine if software contains AI features.
    Returns dict with: has_ai (bool), confidence (str), reason (str)
    """
    software_context = build_software_context(entry)
    
    prompt = f"""You are a software analyst checking if applications contain AI/ML features.

For the following software, determine if it contains any embedded AI, machine learning, 
or features that might send data to AI cloud services.

SOFTWARE:
{software_context}

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
HAS_AI: YES or NO or UNKNOWN
CONFIDENCE: HIGH, MEDIUM, or LOW
REASON: One sentence explaining your assessment

Be conservative - if there's a reasonable chance it has AI features, say YES.
If you don't recognize the software or can't determine its features, say UNKNOWN."""

    try:
        response = client.chat.completions.create(
            model="gpt-5.1",
            # max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.choices[0].message.content

        # DEBUG:
        # print(f"\n--- Response for {software_name} ---")
        # print(repr(text))
        # print("--- End ---")

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
        print("Usage: python main.py <software_inventory.xlsx> [--sheet SHEET_NAME]")
        print("\nExpected Excel format with columns:")
        print("  - Vendor Name")
        print("  - Product Name")
        print("  - Description (optional)")
        print("\nDefault sheet: 'MASTER Spreadsheet'")
        sys.exit(1)

    input_file = sys.argv[1]
    
    # Parse optional sheet name argument
    sheet_name = "MASTER Spreadsheet"
    if "--sheet" in sys.argv:
        sheet_idx = sys.argv.index("--sheet")
        if sheet_idx + 1 < len(sys.argv):
            sheet_name = sys.argv[sheet_idx + 1]

    if not Path(input_file).exists():
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)

    # Load software list
    print(f"Loading software list from {input_file} (sheet: {sheet_name})...")
    try:
        software_list = load_software_list(input_file, sheet_name)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)
        
    print(f"Found {len(software_list)} software entries to check\n")

    if not software_list:
        print("No software found in file. Check format.")
        sys.exit(1)

    # Initialize OpenAI client
    client = OpenAI()  # Uses OPENAI_API_KEY env var

    # Check each software
    results = []
    flagged = []

    for i, entry in enumerate(software_list, 1):
        display_name = f"{entry['vendor']} - {entry['product']}"
        print(f"[{i}/{len(software_list)}] Checking: {display_name}...", end=" ", flush=True)

        result = check_for_ai(client, entry)
        result["vendor"] = entry["vendor"]
        result["product"] = entry["product"]
        result["description"] = entry["description"]
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
        writer.writerow(["Vendor", "Product", "Description", "Has AI", "Confidence", "Reason", "Needs Review"])
        for r in results:
            needs_review = "YES" if r["has_ai"] in ("YES", "UNKNOWN") else "NO"
            writer.writerow([
                r["vendor"],
                r["product"],
                r["description"],
                r["has_ai"],
                r["confidence"],
                r["reason"],
                needs_review
            ])

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
            print(f"  • {item['vendor']} - {item['product']}")
            print(f"    Status: {item['has_ai']} (Confidence: {item['confidence']})")
            print(f"    Reason: {item['reason']}\n")

    print(f"\nScan completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
