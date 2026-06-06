#!/usr/bin/env python3
"""
Windows GUI wrapper for the SUTA TXT to CSV converter.

This file uses only tkinter and the converter module, so it can be packaged
into a standalone Windows executable with PyInstaller.
"""

from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from suta_txt_to_csv import build_rows, parse_report, write_csv


FIELD_DEFINITIONS = [
    ("submitter_fein", "Submitter FEIN"),
    ("business_name", "Submitter business name"),
    ("business_address", "Submitter address"),
    ("business_city", "Submitter city"),
    ("state_fips", "Submitter state FIPS code"),
    ("zip_code", "Submitter ZIP code"),
    ("zip4", "Submitter ZIP+4"),
    ("contact_name", "Submitter contact name"),
    ("contact_phone", "Submitter contact phone"),
    ("contact_ext", "Submitter contact extension"),
    ("contact_email", "Submitter contact email"),
    ("ui_account", "Employer UI account"),
    ("employer_fein", "Employer FEIN"),
    ("reporting_period", "Reporting period"),
    ("month1_count", "Employer month 1 count"),
    ("month2_count", "Employer month 2 count"),
    ("month3_count", "Employer month 3 count"),
    ("no_wage_indicator", "No wage indicator"),
    ("out_of_state_taxable_wages", "Out-of-state taxable wages"),
    ("employee_out_of_state_taxable_wages", "Employee out-of-state taxable wages"),
    ("hours_worked", "Employee hours worked"),
    ("employee_month1", "Employee month 1 indicator"),
    ("employee_month2", "Employee month 2 indicator"),
    ("employee_month3", "Employee month 3 indicator"),
    ("owner_officer", "Owner/officer relationship code"),
    ("adjustment_code", "Adjustment code"),
]


class SutaConverterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SUTA TXT to CSV Converter")
        self.minsize(820, 720)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Choose a TXT file to begin.")
        self.field_vars = {name: tk.StringVar() for name, _label in FIELD_DEFINITIONS}

        self._build_layout()

    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)

        file_frame = ttk.LabelFrame(root, text="Files", padding=12)
        file_frame.pack(fill=tk.X)

        ttk.Label(file_frame, text="TXT file").grid(row=0, column=0, sticky=tk.W, padx=(0, 8), pady=4)
        ttk.Entry(file_frame, textvariable=self.input_path).grid(row=0, column=1, sticky=tk.EW, pady=4)
        ttk.Button(file_frame, text="Browse", command=self.choose_input).grid(row=0, column=2, padx=(8, 0), pady=4)

        ttk.Label(file_frame, text="Output CSV").grid(row=1, column=0, sticky=tk.W, padx=(0, 8), pady=4)
        ttk.Entry(file_frame, textvariable=self.output_path).grid(row=1, column=1, sticky=tk.EW, pady=4)
        ttk.Button(file_frame, text="Save As", command=self.choose_output).grid(row=1, column=2, padx=(8, 0), pady=4)
        file_frame.columnconfigure(1, weight=1)

        fields_frame = ttk.LabelFrame(root, text="CSV Fields", padding=12)
        fields_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        canvas = tk.Canvas(fields_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(fields_frame, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for index, (name, label) in enumerate(FIELD_DEFINITIONS):
            row = index // 2
            col = (index % 2) * 2
            ttk.Label(scroll_frame, text=label).grid(row=row, column=col, sticky=tk.W, padx=(0, 8), pady=5)
            ttk.Entry(scroll_frame, textvariable=self.field_vars[name], width=28).grid(
                row=row, column=col + 1, sticky=tk.EW, padx=(0, 18), pady=5
            )

        for col in (1, 3):
            scroll_frame.columnconfigure(col, weight=1)

        action_frame = ttk.Frame(root)
        action_frame.pack(fill=tk.X, pady=(12, 0))

        ttk.Label(action_frame, textvariable=self.status_text).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(action_frame, text="Create CSV", command=self.create_csv).pack(side=tk.RIGHT)

    def choose_input(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose SUTA TXT file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not selected:
            return

        input_path = Path(selected)
        self.input_path.set(str(input_path))
        if not self.output_path.get():
            self.output_path.set(str(input_path.with_suffix(".csv")))
        self.load_detected_values(input_path)

    def choose_output(self) -> None:
        initial = self.output_path.get() or "output.csv"
        selected = filedialog.asksaveasfilename(
            title="Choose output CSV",
            defaultextension=".csv",
            initialfile=Path(initial).name,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if selected:
            self.output_path.set(selected)

    def load_detected_values(self, input_path: Path) -> None:
        try:
            report = parse_report(input_path)
        except Exception as exc:
            self.status_text.set("Could not parse the selected TXT file.")
            messagebox.showerror("Parse Error", str(exc))
            return

        if report.reporting_period and not self.field_vars["reporting_period"].get():
            self.field_vars["reporting_period"].set(report.reporting_period)
        if not self.field_vars["month3_count"].get():
            self.field_vars["month3_count"].set(str(len(report.employees)))

        self.status_text.set(
            f"Detected {len(report.employees)} employees. Total gross cents: {report.total_gross_cents}."
        )

    def create_csv(self) -> None:
        input_value = self.input_path.get().strip().strip('"')
        output_value = self.output_path.get().strip().strip('"')
        if not input_value:
            messagebox.showerror("Missing TXT File", "Choose a TXT file first.")
            return
        if not output_value:
            messagebox.showerror("Missing Output CSV", "Choose where to save the CSV file.")
            return

        input_path = Path(input_value)
        output_path = Path(output_value)
        if not input_path.exists():
            messagebox.showerror("TXT File Not Found", f"File not found:\n{input_path}")
            return

        try:
            report = parse_report(input_path)
            values = {name: variable.get().strip() for name, variable in self.field_vars.items()}
            args = argparse.Namespace(guided=False, **values)
            rows = build_rows(args, report)
            write_csv(output_path, rows)
        except Exception as exc:
            messagebox.showerror("Conversion Error", str(exc))
            return

        self.status_text.set(f"Wrote {output_path}")
        messagebox.showinfo(
            "CSV Created",
            f"CSV created successfully.\n\nEmployees: {len(report.employees)}\nOutput: {output_path}",
        )


def main() -> int:
    app = SutaConverterApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
