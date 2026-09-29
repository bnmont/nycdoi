"""
Checks the money classifier against real fragments from DOI press releases.

    python tests/test_money.py

No test framework, so this runs anywhere the pipeline runs.

The case that matters most is the salary one. DOI states a defendant's annual
salary in most enforcement releases, often a sentence away from the amount
they are accused of stealing. Every fragment below marked 0/0 was taken from
a real release and would have been published as money stolen by a classifier
that simply took the largest dollar figure on the page.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from transform import classify_money, parse_amount  # noqa: E402

RULES = json.loads((ROOT / "config.json").read_text())["money_rules"]

# (title, mentions, expected_stolen, expected_recouped)
REAL_CASES = [
    # The value of contracts a defendant won is not money they took. All
    # three of these were published as thefts before the exclusions landed.
    ("CEO and Business Partner Charged with Massive Scheme to Defraud",
     ["Between 2014 and 2020, CCS was awarded 12 contracts with the City "
      "worth approximately $913 million. BRANSKY"], 0, 0),
    ("Former CEO at City-Funded Nonprofit Sentenced to Six Months in Prison",
     ["BRANSKY was the Chief Executive Officer of CCS, a not-for-profit "
      "homeless services provider that had over $900 million in contracts"], 0, 0),
    # Street value of seized drugs is not money stolen.
    ("Two Pharmacists Sentenced for Illegal Distribution of Oxycodone",
     ["the scheme resulted in the illegal distribution of more than 1.6 million "
      "pills of oxycodone, worth more than $48 million in retail street value"], 0, 0),
    # The release says $1.7 million five times; $40 million is payroll hidden
    # from an insurance fund, and $7.8 million is the insurance fraud total.
    ("DA Vance, Partners Announce Criminal Charges in Multimillion Dollar Wage Theft",
     ["Defendants Stole More Than $1.7 Million From 500+ Laborers who Performed "
      "Dangerous Construction Work Defendants Also Hid More Than $40 Million",
      "schemes involving the theft of more than $1.7 million in wages, as well as "
      "workers compensation insurance fraud totaling approximately $7.8 million",
      "stole more than $1.7 million from employees through a wage theft scheme",
      "the defendants stole more than $1.7 million from at least 520 workers",
      "the defendants also hid more than $40 million in payroll from NYSIF"],
     1_700_000, 0),
    # A figure in the title is the release's own headline number.
    ("Manhattan D.A., D.O.I. Announce Indictment In $128K NYCERS Theft",
     ["unrelated background mentioning $9,000,000 in agency contracts"],
     128_000, 0),
    # Money the City paid out is not money anyone recovered. This matched
    # only because "delivering" contains "deliver".
    ("DOI Issues Report Today on Corruption Vulnerabilities in City Contracting",
     ["the City made payments to nonprofit human service contractors totaling "
      "more than $4 billion. These contractors supplement City government by "
      "delivering a variety of services"], 0, 0),
    # A forfeiture action seeking money has not recovered it.
    ("Procurement Fraud at the Department of Environmental Protection",
     ["The Asset Forfeiture Unit is also filing two civil forfeiture actions "
      "seeking a total of $177,609,293 from the indicted defendants"], 0, 0),
    # A prosecutor's career total is not this case's recovery.
    ("New York City and State Partners Announce Joint Effort to Combat Wage Theft",
     ["My office has zero tolerance for wage theft. Since 2011, we have "
      "recovered nearly $30 million in stolen wages for more than 21,000 workers"],
     0, 0),
    # But a recovery genuinely delivered in this case still counts.
    ("Attorney General James and DOI Commissioner Strauber Deliver $900,000 to "
     "200 NYCHA Construction Workers Denied Fair Pay", [], 0, 900_000),
]

# (mentions, expected_stolen, expected_recouped) — no title involved
CASES = [
    # Salaries and other non-thefts — all must be ignored.
    (["he was receiving an annual salary of $178,907"], 0, 0),
    (["ALFRED RIVERA, 47, was receiving an annual base salary of $76,488"], 0, 0),
    (["COWEN receives an annual base salary of approximately $81,879."], 0, 0),
    (["Each receives a base salary of $76,488."], 0, 0),
    (["this network grossed approximately $10,000 weekly in drug sales"], 0, 0),
    (["Homeless Shelter Contracts Worth $12 Million"], 0, 0),
    # Thefts.
    (["the defendants allegedly obtained more than $1.3 million of government benefits"],
     1_300_000, 0),
    (["Indicted for Allegedly Stealing Over $243,000 from Sheriff's Office Trust Accounts"],
     243_000, 0),
    (["a scheme that allegedly diverted over $400,000 into accounts controlled by her"],
     400_000, 0),
    (["Former Officials Indicted in $3 Million Fraud Scheme"], 3_000_000, 0),
    (["Pleads Guilty to Stealing Nearly $22,000 in Wages"], 22_000, 0),
    # Recoveries.
    (["was ordered to pay $250,000 in restitution to the City"], 0, 250_000),
    (["with Public Contracts to Forfeit $2.5 Million After Pleading Guilty"], 0, 2_500_000),
    (["has recovered $1.75 million for taxpayers"], 0, 1_750_000),
    # A salary must not contaminate a genuine theft in the same release.
    (["stole $500,000 from the agency", "earns an annual salary of $90,000"], 500_000, 0),
    (["stole $500,000", "paid $100,000 in restitution"], 500_000, 100_000),
]

AMOUNTS = [
    ("$243,000", 243_000),
    ("$2.5 million", 2_500_000),
    ("$3 Million", 3_000_000),
    ("$1.3 billion", 1_300_000_000),
    ("$800", 800),
    ("$20k", 20_000),
]


def main():
    failures = []

    for mentions, want_s, want_r in CASES:
        got_s, _, got_r, _ = classify_money("", mentions, RULES)
        if (got_s, got_r) != (want_s, want_r):
            failures.append(
                f"{mentions[0][:70]!r}\n"
                f"      expected stolen={want_s:,} recouped={want_r:,}\n"
                f"      got      stolen={got_s:,.0f} recouped={got_r:,.0f}"
            )

    for title, mentions, want_s, want_r in REAL_CASES:
        got_s, _, got_r, _ = classify_money(title, mentions, RULES)
        if (got_s, got_r) != (want_s, want_r):
            failures.append(
                f"{title[:70]!r}\n"
                f"      expected stolen={want_s:,} recouped={want_r:,}\n"
                f"      got      stolen={got_s:,.0f} recouped={got_r:,.0f}"
            )

    for text, want in AMOUNTS:
        got = parse_amount(text)
        if got != want:
            failures.append(f"parse_amount({text!r}) = {got:,.0f}, expected {want:,}")

    total = len(CASES) + len(REAL_CASES) + len(AMOUNTS)
    if failures:
        print(f"FAILED {len(failures)} of {total}:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print(f"all {total} money checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
