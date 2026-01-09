Yeah — a few things jump out in `ai_scan_results.csv` besides the smart-quote rendering stuff:

### 1) **`Needs Review` is *literally identical* to `Has AI`**

* 512/512 rows: **Has AI == Needs Review**
* So if Has AI = YES → Needs Review = YES (always)
* If Has AI = NO → Needs Review = NO (always)

That’s… *kinda sus*, because “needs review” should usually mean **uncertainty / bad input / edge case**, not “it has AI.”
It also causes a real bug:

* **284 rows have `Confidence = LOW` but `Needs Review = NO`**, which is probably not what you intended.

### 2) **There are rows with actual Excel error values (`#REF!`) but they’re NOT flagged**

I found **4 rows** where Vendor/Product/Description contain `#REF!` (some are entirely `#REF!`), yet they still show:

* `Needs Review = NO`
* `Confidence = LOW`

Those should basically be auto-review every time.

### 3) **Your “Reason” field often breaks the 256-char target**

* Max reason length: **401 chars**
* **121 rows** have `Reason > 256 chars`

If Andy makes “Reason” a 256-char field in Drupal, those will get truncated unless you trim them yourself.

### 4) **Two Product values start with a dash (`- ...`)**

Not a “data quality” issue, but a **CSV/Excel safety gotcha**:

* Cells starting with `=`, `+`, `-`, or `@` can sometimes trigger formula behavior in Excel (CSV injection risk).
* You’ve got **2 rows** where Product starts with `- Intellidesk - Mobile Connect`.

If anyone opens the CSV in Excel, safest move is to prefix those fields with an apostrophe `'` or space when exporting.

### 5) **Same Vendor+Product appears twice with different AI conclusions (example: Phreesia)**

There are duplicates where the description changes and your AI output changes too. Most duplicates keep the same Has AI, but **Phreesia flips NO→YES** depending on the row. That’s not “wrong,” but it’s something Andy will notice if he filters by vendor/product and expects consistency.

---

## If you want the quickest “make it sane” fixes

* Set `Needs Review = YES` when:

  * Confidence is LOW (or maybe LOW+MEDIUM depending how conservative you want)
  * Vendor/Product/Description is missing or contains `#REF!`
* Enforce `Reason` length (hard truncate to 256, or generate a short version)
* Sanitize CSV export for cells starting with `= + - @`

If you want, paste a couple lines from your output logic (or describe how you set Needs Review) and I’ll tell you exactly why it ended up mirroring Has AI.

