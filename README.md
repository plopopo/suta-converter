# SUTA TXT to CSV Converter

Small Windows-friendly utility for converting a state unemployment worksheet TXT export into the 15-column CSV import layout used by the unemployment wage reporting system.

## Requirements

- Windows
- Python 3.10 or newer
- No third-party Python packages are required

## Easiest Use From Source

1. Double-click `Run SUTA Converter.bat`.
2. Enter the path to the TXT file when prompted.
3. Press Enter to accept the default output CSV path, or type a different CSV path.
4. Enter the two commonly needed fields: Submitter FEIN and Employer UI account.
5. The converter keeps the rest of the submitter row constant and uses parsed/default values for technical fields.

The script will parse employee rows, gross wages, employee count, and the reporting period from the TXT file when available.

## No-Install Client Use

For users who should not install Python, distribute the packaged executable:

```text
dist\SUTA Converter Console.exe
```

The executable opens a simple prompt window. Users enter the TXT path, choose the output CSV path, then enter Submitter FEIN and Employer UI account. The first row stays constant except for B1, which is the Submitter FEIN. Use `--advanced` only when optional CSV fields need to be overridden manually.

## Simple Mode vs Advanced Mode

By default, the converter uses simple mode. Simple mode asks only for:

- TXT file path
- Output CSV path
- Submitter FEIN
- Employer UI account

Simple mode automatically:

- Parses the reporting period from the TXT file
- Counts employee records from the TXT file
- Uses the parsed employee count for month 1, month 2, and month 3
- Uses `1` for no wage indicator
- Uses `1,1,1` for employee month indicators
- Uses `0` for owner/officer relationship code
- Uses `0` for adjustment code
- Keeps the first submitter row constant except for B1

Use advanced mode only when you need to manually fill every optional CSV field.

From PowerShell:

```powershell
python .\suta_txt_to_csv.py --advanced
```

With the standalone executable:

```powershell
& ".\dist\SUTA Converter Console.exe" --advanced
```

## Build The EXE

On the build machine only:

```powershell
pip install pyinstaller
python -m PyInstaller --onefile --name "SUTA Converter Console" suta_txt_to_csv.py
```

Or double-click:

```text
Build EXE.bat
```

Clients do not need Python or PyInstaller after you give them the built `.exe`.

## GUI Source

`suta_converter_gui.py` contains a tkinter GUI version of the converter. It can be run with Python:

```powershell
python .\suta_converter_gui.py
```

Packaging the GUI as an EXE requires a Python installation with complete Tcl/Tk files. The prompt-based EXE above is the tested no-install distribution artifact.

## Command-Line Use

```powershell
python .\suta_txt_to_csv.py "C:\path\to\SUTA WKST.txt" -o "C:\path\to\output.csv" --submitter-fein 123456789 --ui-account 000123456
```

You can also provide fields directly:

```powershell
python .\suta_txt_to_csv.py "C:\path\to\SUTA WKST.txt" `
  -o "C:\path\to\output.csv" `
  --submitter-fein 123456789 `
  --ui-account 000123456
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
- Gross, taxable, and excess wages are parsed separately for the employer summary row.
- SSNs and phone/FEIN/account fields are normalized to digits only.
- CSV values are written as text, but Excel may still visually strip leading zeros when a CSV is opened by double-clicking it. For inspection, import the CSV through Excel's Data/Text import flow and mark FEIN, UI account, and SSN columns as text.
- The converter validates that parsed employee wage totals match the worksheet total when the worksheet contains a total.
