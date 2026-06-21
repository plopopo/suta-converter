#!/usr/bin/env python3
"""
Convert a state unemployment worksheet TXT export into the 15-column CSV import
layout used by the unemployment wage reporting system.

Easy use:
    python suta_txt_to_csv.py

Command-line use:
    python suta_txt_to_csv.py "SUTA WKST_NO_SSN.txt" -o "Q126 import.csv"
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


CSV_WIDTH = 15

DEFAULT_SUBMITTER = {
    "business_name": "",
    "business_address": "",
    "business_city": "",
    "state_fips": "",
    "zip_code": "",
    "zip4": "",
    "contact_name": "",
    "contact_phone": "",
    "contact_ext": "",
    "contact_email": "",
}

STATE_FIPS = {
    "AL": "01",
    "AK": "02",
    "AZ": "04",
    "AR": "05",
    "CA": "06",
    "CO": "08",
    "CT": "09",
    "DE": "10",
    "DC": "11",
    "FL": "12",
    "GA": "13",
    "HI": "15",
    "ID": "16",
    "IL": "17",
    "IN": "18",
    "IA": "19",
    "KS": "20",
    "KY": "21",
    "LA": "22",
    "ME": "23",
    "MD": "24",
    "MA": "25",
    "MI": "26",
    "MN": "27",
    "MS": "28",
    "MO": "29",
    "MT": "30",
    "NE": "31",
    "NV": "32",
    "NH": "33",
    "NJ": "34",
    "NM": "35",
    "NY": "36",
    "NC": "37",
    "ND": "38",
    "OH": "39",
    "OK": "40",
    "OR": "41",
    "PA": "42",
    "RI": "44",
    "SC": "45",
    "SD": "46",
    "TN": "47",
    "TX": "48",
    "UT": "49",
    "VT": "50",
    "VA": "51",
    "WA": "53",
    "WV": "54",
    "WI": "55",
    "WY": "56",
}

EMPLOYEE_RE = re.compile(
    r"""
    ^\s*
    (?P<ssn>(?:\d{3}-\d{2}-\d{4})|(?:\d{9}))
    \s+
    (?P<name>.+?)
    \s+
    (?P<employee_id>\S+)
    \s+
    (?P<weeks>\d+(?:\.\d+)?)
    \s+
    (?P<gross>[\d,]+\.\d{2})
    \s+
    (?P<taxable>[\d,]+\.\d{2})
    \s+
    (?P<exempt>[\d,]+\.\d{2})
    \s*$
    """,
    re.VERBOSE,
)

TOTALS_RE = re.compile(
    r"^\s*Totals:\s+(?P<gross>[\d,]+\.\d{2})\s+(?P<taxable>[\d,]+\.\d{2})\s+(?P<exempt>[\d,]+\.\d{2})",
    re.IGNORECASE,
)

LISTED_EMPLOYEES_RE = re.compile(r"Listed Employees:\s*(?P<count>\d+)", re.IGNORECASE)
QUARTER_ENDED_RE = re.compile(r"Quarter Ended:\s*(?P<month>\d{1,2})/\d{1,2}/(?P<year>\d{4})", re.IGNORECASE)
STATE_RE = re.compile(r"State:\s*(?P<state>[A-Z]{2})", re.IGNORECASE)


@dataclass
class Employee:
    ssn: str
    first_name: str
    middle_initial: str
    last_name: str
    gross_cents: str


@dataclass
class ParsedReport:
    employees: list[Employee]
    reporting_period: str | None
    state_code: str | None
    total_gross_cents: str
    listed_employee_count: int | None


def money_to_cents(value: str) -> str:
    amount = Decimal(value.replace(",", ""))
    cents = (amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return str(int(cents))


def digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def split_employee_name(name: str) -> tuple[str, str, str]:
    parts = name.replace(".", "").split()
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return parts[0], "", ""
    last_name = parts[-1]
    if len(parts) >= 3 and len(parts[-2]) == 1:
        return " ".join(parts[:-2]), parts[-2], last_name
    return " ".join(parts[:-1]), "", last_name


def reporting_period_from_quarter(month: str, year: str) -> str:
    return f"{int(month)}{year}"


def parse_report(path: Path) -> ParsedReport:
    employees: list[Employee] = []
    reporting_period: str | None = None
    state_code: str | None = None
    totals_gross_cents: str | None = None
    listed_employee_count: int | None = None

    for raw_line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if reporting_period is None:
            quarter_match = QUARTER_ENDED_RE.search(raw_line)
            if quarter_match:
                reporting_period = reporting_period_from_quarter(
                    quarter_match.group("month"), quarter_match.group("year")
                )

        if state_code is None:
            state_match = STATE_RE.search(raw_line)
            if state_match:
                state_code = state_match.group("state").upper()

        totals_match = TOTALS_RE.match(raw_line)
        if totals_match:
            totals_gross_cents = money_to_cents(totals_match.group("gross"))
            continue

        listed_match = LISTED_EMPLOYEES_RE.search(raw_line)
        if listed_match:
            listed_employee_count = int(listed_match.group("count"))
            continue

        employee_match = EMPLOYEE_RE.match(raw_line)
        if employee_match:
            first_name, middle_initial, last_name = split_employee_name(employee_match.group("name"))
            employees.append(
                Employee(
                    ssn=digits_only(employee_match.group("ssn")),
                    first_name=first_name,
                    middle_initial=middle_initial,
                    last_name=last_name,
                    gross_cents=money_to_cents(employee_match.group("gross")),
                )
            )

    if not employees:
        raise ValueError(f"No employee rows were found in {path}")

    calculated_total = str(sum(int(employee.gross_cents) for employee in employees))
    if totals_gross_cents is None:
        totals_gross_cents = calculated_total
    elif totals_gross_cents != calculated_total:
        raise ValueError(
            f"Parsed employee gross total {calculated_total} does not match worksheet total {totals_gross_cents}"
        )

    if listed_employee_count is not None and listed_employee_count != len(employees):
        raise ValueError(
            f"Parsed {len(employees)} employee rows, but worksheet says {listed_employee_count}"
        )

    return ParsedReport(
        employees=employees,
        reporting_period=reporting_period,
        state_code=state_code,
        total_gross_cents=totals_gross_cents,
        listed_employee_count=listed_employee_count,
    )


def pad_row(fields: list[str]) -> list[str]:
    if len(fields) > CSV_WIDTH:
        raise ValueError(f"Row has {len(fields)} fields; expected at most {CSV_WIDTH}")
    return fields + [""] * (CSV_WIDTH - len(fields))


def prompt_if_missing(
    label: str,
    value: str | None,
    default: str | None = None,
    *,
    guided: bool = False,
) -> str:
    if value not in (None, ""):
        return value
    if not guided and default is not None:
        return default
    prompt = f"{label}"
    if guided and default not in (None, ""):
        prompt += f" [{default}]"
    prompt += ": "
    entered = input(prompt).strip()
    if entered == "" and default is not None:
        return default
    return entered


def build_rows(args: argparse.Namespace, report: ParsedReport) -> list[list[str]]:
    guided = bool(args.guided)
    advanced = bool(getattr(args, "advanced", False))
    reporting_period = prompt_if_missing(
        "Reporting period, e.g. 32026",
        args.reporting_period,
        report.reporting_period,
        guided=guided and report.reporting_period is None,
    )

    submitter_fein = digits_only(prompt_if_missing("Submitter FEIN", args.submitter_fein, "", guided=guided))
    business_name = prompt_if_missing(
        "Submitter business name", args.business_name, DEFAULT_SUBMITTER["business_name"], guided=guided and advanced
    ).upper()
    business_address = prompt_if_missing(
        "Submitter address", args.business_address, DEFAULT_SUBMITTER["business_address"], guided=guided and advanced
    ).upper()
    business_city = prompt_if_missing(
        "Submitter city", args.business_city, DEFAULT_SUBMITTER["business_city"], guided=guided and advanced
    ).upper()
    state_fips = prompt_if_missing(
        "Submitter state FIPS code", args.state_fips, DEFAULT_SUBMITTER["state_fips"], guided=guided and advanced
    )
    zip_code = digits_only(
        prompt_if_missing("Submitter ZIP code", args.zip_code, DEFAULT_SUBMITTER["zip_code"], guided=guided and advanced)
    )
    zip4 = digits_only(
        prompt_if_missing("Submitter ZIP+4", args.zip4, DEFAULT_SUBMITTER["zip4"], guided=guided and advanced)
    )
    contact_name = prompt_if_missing(
        "Submitter contact name", args.contact_name, DEFAULT_SUBMITTER["contact_name"], guided=guided and advanced
    ).upper()
    contact_phone = digits_only(
        prompt_if_missing(
            "Submitter contact phone", args.contact_phone, DEFAULT_SUBMITTER["contact_phone"], guided=guided and advanced
        )
    )
    contact_ext = digits_only(
        prompt_if_missing(
            "Submitter contact extension", args.contact_ext, DEFAULT_SUBMITTER["contact_ext"], guided=guided and advanced
        )
    )
    contact_email = prompt_if_missing(
        "Submitter contact email", args.contact_email, DEFAULT_SUBMITTER["contact_email"], guided=guided and advanced
    ).upper()

    ui_account = digits_only(prompt_if_missing("Employer UI account", args.ui_account, "", guided=guided))
    employer_fein = digits_only(prompt_if_missing("Employer FEIN", args.employer_fein, submitter_fein, guided=guided))
    month1_count = prompt_if_missing(
        "Employer 12th-of-month count for month 1", args.month1_count, "0", guided=guided and advanced
    )
    month2_count = prompt_if_missing(
        "Employer 12th-of-month count for month 2", args.month2_count, "0", guided=guided and advanced
    )
    month3_count = prompt_if_missing(
        "Employer 12th-of-month count for month 3",
        args.month3_count,
        str(len(report.employees)),
        guided=guided and advanced,
    )
    no_wage_indicator = prompt_if_missing("No wage indicator", args.no_wage_indicator, "1", guided=guided and advanced)

    employee_month1 = prompt_if_missing("Employee month 1 indicator", args.employee_month1, "1", guided=guided and advanced)
    employee_month2 = prompt_if_missing("Employee month 2 indicator", args.employee_month2, "1", guided=guided and advanced)
    employee_month3 = prompt_if_missing("Employee month 3 indicator", args.employee_month3, "1", guided=guided and advanced)
    owner_officer = prompt_if_missing("Owner/officer relationship code", args.owner_officer, "0", guided=guided and advanced)
    adjustment_code = prompt_if_missing("Adjustment code", args.adjustment_code, "0", guided=guided and advanced)

    rows = [
        pad_row(
            [
                "0",
                submitter_fein,
                business_name,
                business_address,
                business_city,
                state_fips,
                zip_code,
                zip4,
                contact_name,
                contact_phone,
                contact_ext,
                contact_email,
            ]
        ),
        pad_row(
            [
                "1",
                ui_account,
                reporting_period,
                employer_fein,
                report.total_gross_cents,
                args.out_of_state_taxable_wages or "0",
                month1_count,
                month2_count,
                month3_count,
                no_wage_indicator,
            ]
        ),
    ]

    for employee in report.employees:
        rows.append(
            pad_row(
                [
                    "2",
                    ui_account,
                    reporting_period,
                    employee.ssn,
                    employee.first_name,
                    employee.middle_initial,
                    employee.last_name,
                    employee.gross_cents,
                    args.employee_out_of_state_taxable_wages or "",
                    args.hours_worked or "",
                    employee_month1,
                    employee_month2,
                    employee_month3,
                    owner_officer,
                    adjustment_code,
                ]
            )
        )

    rows.append(pad_row(["3", str(len(report.employees)), report.total_gross_cents]))
    return rows

def write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerows(rows)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse a SUTA unemployment worksheet TXT file into the formatted CSV import layout."
    )
    parser.add_argument("input_txt", type=Path, nargs="?", help="Path to the source TXT worksheet.")
    parser.add_argument("-o", "--output", type=Path, help="Path for the output CSV.")
    parser.add_argument("--guided", action="store_true", help="Ask simple questions for missing CSV values.")
    parser.add_argument("--advanced", action="store_true", help="Prompt for every optional CSV field instead of using defaults/blanks.")
    parser.add_argument("--non-interactive", action="store_true", help="Fail instead of prompting for missing values.")

    parser.add_argument("--submitter-fein")
    parser.add_argument("--business-name", default=DEFAULT_SUBMITTER["business_name"])
    parser.add_argument("--business-address", default=DEFAULT_SUBMITTER["business_address"])
    parser.add_argument("--business-city", default=DEFAULT_SUBMITTER["business_city"])
    parser.add_argument("--state-fips", default=DEFAULT_SUBMITTER["state_fips"])
    parser.add_argument("--zip-code", default=DEFAULT_SUBMITTER["zip_code"])
    parser.add_argument("--zip4", default=DEFAULT_SUBMITTER["zip4"])
    parser.add_argument("--contact-name", default=DEFAULT_SUBMITTER["contact_name"])
    parser.add_argument("--contact-phone", default=DEFAULT_SUBMITTER["contact_phone"])
    parser.add_argument("--contact-ext", default=DEFAULT_SUBMITTER["contact_ext"])
    parser.add_argument("--contact-email", default=DEFAULT_SUBMITTER["contact_email"])

    parser.add_argument("--ui-account")
    parser.add_argument("--employer-fein")
    parser.add_argument("--reporting-period", help="Last month of quarter plus year, e.g. 32026.")
    parser.add_argument("--month1-count")
    parser.add_argument("--month2-count")
    parser.add_argument("--month3-count")
    parser.add_argument("--no-wage-indicator")
    parser.add_argument("--out-of-state-taxable-wages", default="0")

    parser.add_argument("--employee-out-of-state-taxable-wages", default="")
    parser.add_argument("--hours-worked", default="")
    parser.add_argument("--employee-month1")
    parser.add_argument("--employee-month2")
    parser.add_argument("--employee-month3")
    parser.add_argument("--owner-officer")
    parser.add_argument("--adjustment-code")

    return parser.parse_args(argv)


def require_non_interactive_values(args: argparse.Namespace, report: ParsedReport) -> None:
    required: list[str] = []
    missing = [name.replace("_", "-") for name in required if not getattr(args, name)]
    if missing:
        raise ValueError(
            "Missing required values in --non-interactive mode: "
            + ", ".join(f"--{name}" for name in missing)
        )


def prompt_path(label: str, default: Path | None = None) -> Path:
    while True:
        prompt = label
        if default is not None:
            prompt += f" [{default}]"
        prompt += ": "
        entered = input(prompt).strip().strip('"')
        if entered:
            return Path(entered).expanduser()
        if default is not None:
            return default
        print("Please enter a file path.")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.input_txt is None:
        args.guided = True
        print("SUTA TXT to CSV converter")
        print("Simple mode asks only for the fields normally needed.")
        print("Use --advanced if you need to fill every optional CSV field.")
        input_path = prompt_path("TXT file to convert")
    else:
        input_path = args.input_txt.expanduser()

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    default_output_path = input_path.with_suffix(".csv")
    if args.output is None and args.guided:
        output_path = prompt_path("Output CSV file", default_output_path)
    else:
        output_path = args.output or default_output_path

    report = parse_report(input_path)
    if args.non_interactive:
        require_non_interactive_values(args, report)

    rows = build_rows(args, report)
    write_csv(output_path, rows)
    print(f"Wrote {output_path}")
    print(f"Employees: {len(report.employees)}")
    print(f"Total gross cents: {report.total_gross_cents}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
