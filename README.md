# SUTA TXT to CSV Converter

Small Windows-friendly utility for converting a state unemployment worksheet TXT export into the 15-column CSV import layout used by the unemployment wage reporting system.

## Requirements

- Windows
- Python 3.10 or newer
- No third-party Python packages are required

## Easiest Use

1. Double-click `Run SUTA Converter.bat`.
2. Enter the path to the TXT file when prompted.
3. Press Enter to accept the default output CSV path, or type a different CSV path.
4. Fill in any submitter/employer fields needed for the output CSV.
5. Press Enter on any field that should stay blank.

The script will parse employee rows, gross wages, employee count, and the reporting period from the TXT file when available.

## Command-Line Use

```powershell
python .\suta_txt_to_csv.py "C:\path\to\SUTA WKST.txt" -o "C:\path\to\output.csv"
```

You can also provide fields directly:

```powershell
python .\suta_txt_to_csv.py "C:\path\to\SUTA WKST.txt" `
  -o "C:\path\to\output.csv" `
  --submitter-fein 413771120 `
  --ui-account 100132872 `
  --employer-fein 111111111
```

## Output

The generated CSV contains:

- Submitter record
- Employer summary record
- One wage record per employee
- Final total record

Each row is padded to 15 columns.

## Notes

- Monetary values are converted to cents, matching the provided sample CSV format.
- SSNs and phone/FEIN/account fields are normalized to digits only.
- The converter validates that parsed employee wage totals match the worksheet total when the worksheet contains a total.
