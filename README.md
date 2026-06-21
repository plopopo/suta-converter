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
4. Fill in any submitter/employer fields needed for the output CSV.
5. Press Enter on any field that should stay blank.

The script will parse employee rows, gross wages, employee count, and the reporting period from the TXT file when available.

## No-Install Client Use

For users who should not install Python, distribute the packaged executable:

```text
dist\SUTA Converter Console.exe
```

The executable opens a simple prompt window. Users enter the TXT path, choose the output CSV path, then enter Submitter FEIN, Employer UI account, and Employer FEIN. Optional submitter/contact fields stay blank by default. Use `--advanced` only when every optional CSV field needs to be filled manually.

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
python .\suta_txt_to_csv.py "C:\path\to\SUTA WKST.txt" -o "C:\path\to\output.csv" --submitter-fein 413771120 --ui-account 100132872 --employer-fein 111111111
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
