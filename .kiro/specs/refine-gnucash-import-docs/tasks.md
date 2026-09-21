# GnuCash Import Skill Documentation Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Remove duplicated skill documentation, separate personal transaction rules from tracked files, and keep all import behavior and source-specific knowledge intact.

**Architecture:** `SKILL.md` owns the shared import workflow and safety rules. Account references contain only access, statement format, mapping, and source-specific exceptions. Ignored `personal.json` stores real personal values, while tracked `personal.example.json` defines the schema; affected scripts load only their source-specific settings and fail safely when a rule is absent.

**Tech Stack:** Markdown, Python 3 standard library, JSON, `unittest`, basedpyright

**Spec:** `.kiro/specs/refine-gnucash-import-docs/design.md`

## Global Constraints

- Preserve transaction classification meaning, split signs, currency denominators, security quantities, and mirror-transaction skip behavior.
- Keep descriptions in English when non-NULL.
- Store real names, nearest-station values, relationship labels, personal account mappings, and fixed personal splits only in ignored `references/personal.json`.
- Use dummy financial and identity values in tracked examples.
- Run scripts copied to `/tmp/gnucash-import.XXXXXX` from the repository root, with `GNUCASH_IMPORT_ROOT` available as an explicit override.
- Use only the Python standard library.
- Preserve existing unrelated working-tree changes, including the externally deleted commit hook.
- Do not create commits unless explicitly requested.

---

### Task 1: Runtime path resolution

**Files:**
- Create: `tests/test_runtime_paths.py`
- Modify: `.kiro/skills/gnucash-import/references/templates/script-template.py`
- Modify: all 32 files matching `scripts/*_import.py`

**Interfaces:**
- Consumes: `GNUCASH_IMPORT_ROOT`, current working directory, and each script's original repository-relative fallback.
- Produces: `PROJECT_ROOT: pathlib.Path` and `ACCOUNTS_FILE = PROJECT_ROOT / '.kiro/skills/gnucash-import/references/account-guid-cache.json'` in every import script.

- [x] **Step 1: Add a failing structural test for runtime path resolution**

```python
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimePathTest(unittest.TestCase):
    def test_all_import_scripts_support_project_root_override(self):
        paths = sorted((ROOT / "scripts").glob("*_import.py"))
        self.assertEqual(32, len(paths))
        for path in paths:
            source = path.read_text()
            with self.subTest(path=path.name):
                self.assertIn("GNUCASH_IMPORT_ROOT", source)
                self.assertIn("PROJECT_ROOT", source)
                self.assertNotIn("Path(__file__).parent.parent / '.kiro/", source)

    def test_script_template_supports_project_root_override(self):
        path = ROOT / ".kiro/skills/gnucash-import/references/templates/script-template.py"
        source = path.read_text()
        self.assertIn("GNUCASH_IMPORT_ROOT", source)
        self.assertIn("PROJECT_ROOT", source)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run the test and confirm RED**

Run: `python3 -m unittest tests.test_runtime_paths -v`

Expected: failures reporting missing `GNUCASH_IMPORT_ROOT` and `PROJECT_ROOT`.

- [x] **Step 3: Add the self-contained resolver to every import script and the template**

Use this implementation in each file before loading the account cache:

```python
import os
from pathlib import Path


def find_project_root():
    configured_root = os.environ.get("GNUCASH_IMPORT_ROOT")
    candidates = [Path(configured_root)] if configured_root else []
    candidates.extend([Path.cwd(), Path(__file__).resolve().parent.parent])
    for candidate in candidates:
        if (candidate / ".kiro/skills/gnucash-import").is_dir():
            return candidate
    raise FileNotFoundError(
        "Cannot find the repository root. Run from the repository root or set GNUCASH_IMPORT_ROOT."
    )


PROJECT_ROOT = find_project_root()
ACCOUNTS_FILE = PROJECT_ROOT / ".kiro/skills/gnucash-import/references/account-guid-cache.json"
```

Remove duplicate `os` or `Path` imports and preserve each script's remaining imports.

- [x] **Step 4: Run runtime-path and syntax checks**

Run: `python3 -m unittest tests.test_runtime_paths -v && python3 -m compileall -q scripts .kiro/skills/gnucash-import/references/templates/script-template.py`

Expected: all tests pass and compileall exits 0.

---

### Task 2: Personal settings and transaction rules

**Files:**
- Create: `.kiro/skills/gnucash-import/references/personal.example.json`
- Create: `tests/test_personal_rules.py`
- Modify ignored file: `.kiro/skills/gnucash-import/references/personal.json`
- Modify: `scripts/docomo_smtb_net_bank_import.py`
- Modify: `scripts/mufg_bank_import.py`
- Modify: `scripts/pasmo_import.py`
- Modify: `scripts/sony_bank_import.py`
- Modify: `scripts/suica_import.py`

**Interfaces:**
- Consumes: `personal.json` with top-level `nearest_station` and `transfer_rules` keyed by source slug.
- Produces: source-local rule dictionaries whose account paths are resolved through `get_guid`; missing rules raise a source-specific `ValueError` only when the matching personal transaction needs classification.

- [x] **Step 1: Add failing tests for configured, missing, and split rules**

Create a standard-library `unittest` module that builds a temporary repository containing an account cache and personal settings, imports each target script with `GNUCASH_IMPORT_ROOT` set to that directory, and restores the environment after each test. Cover these cases with dummy values:

```python
def test_docomo_configured_deposit_rule():
    info = module.get_transaction_info(1, {
        "currency": "JPY", "desc": "振込＊EXAMPLE A", "amount": 12345
    })
    assert info == ("income-guid", "Family")


def test_docomo_configured_split_rule():
    info = module.get_transaction_info(1, {
        "currency": "JPY", "desc": "振込＊EXAMPLE B", "amount": -10000
    })
    assert info == [
        ("asset-guid", -6000, "Family"),
        ("expense-guid", -4000, "Family"),
    ]


def test_mufg_configured_self_transfer():
    info = module.get_transaction_info(1, {
        "desc": "振込 EXAMPLE NAME", "amount": 1000
    })
    assert info == ("bank-guid", None)


def test_sony_configured_self_transfer():
    info = module.get_transaction_info(1, {
        "currency": "JPY", "desc": "振込 EXAMPLE NAME", "amount": 1000
    })
    assert info == ("bank-guid", None)


def test_missing_personal_rule_is_not_guessed(self):
    with self.assertRaises(ValueError):
        module.get_transaction_info(1, personal_transaction)
```

Implement the final assertion with `self.assertRaises(ValueError)` rather than adding pytest. Also test Suica business pairs and PASMO nearest-station railway detection from a dummy `nearest_station`.

- [x] **Step 2: Run the tests and confirm RED**

Run: `python3 -m unittest tests.test_personal_rules -v`

Expected: failures because the scripts still contain hard-coded identity values and do not load source-specific rules.

- [x] **Step 3: Define the tracked example and migrate real values**

Create `personal.example.json` with the exact schema and dummy values from the design document. Extend ignored `personal.json` with the equivalent real values currently present in the scripts and Markdown. Do not print or copy those real values into tests, diffs, logs, or tracked files.

- [x] **Step 4: Load personal rules in the five scripts**

Use `PERSONAL_FILE = PROJECT_ROOT / ".kiro/skills/gnucash-import/references/personal.json"`. Load `{}` if the file is absent, resolve configured account paths with `get_guid`, and replace each hard-coded personal pattern, account, amount, and relationship description with the corresponding source rule. Keep public institution and merchant rules in code.

- [x] **Step 5: Fail safely for absent or malformed source rules**

When a source rule is absent, let unrelated transactions continue through public rules. If a transaction would require a personal mapping, raise `ValueError` with the source name and the missing `personal.json` key. Reject a configured split whose split amounts do not sum to the transaction amount.

- [x] **Step 6: Run focused tests and type checks**

Run: `python3 -m unittest tests.test_personal_rules tests.test_runtime_paths -v && basedpyright scripts/docomo_smtb_net_bank_import.py scripts/mufg_bank_import.py scripts/pasmo_import.py scripts/sony_bank_import.py scripts/suica_import.py`

Expected: all tests pass and basedpyright reports 0 errors.

---

### Task 3: Shared skill workflow and reference template

**Files:**
- Modify: `.kiro/skills/gnucash-import/SKILL.md`
- Modify: `.kiro/skills/gnucash-import/references/email-lookup.md`
- Modify: `.kiro/skills/gnucash-import/references/fixed-assets.md`
- Modify: `.kiro/skills/gnucash-import/references/gnucash-schema.md`
- Modify: `.kiro/skills/gnucash-import/references/templates/reference-template.md`

**Interfaces:**
- Consumes: account references as source-specific details and the two personal JSON files from Task 2.
- Produces: one authoritative import workflow referenced by all account documents.

- [x] **Step 1: Rewrite SKILL.md around the shared workflow**

Keep the frontmatter description. Organize the body as `Workflow`, `Safety Rules`, `Workspace`, `Duplicate Detection`, `Credit Cards`, `Personal Settings`, `Adding a Source`, and `References`. Require this sequence:

```text
select source reference → create work_dir → refresh account cache if needed → retrieve statement → compare existing transactions → prepare script and data → review with user → generate SQL → inspect SQL → execute
```

Replace the handwritten Supported Sources list with links to `references/accounts/` and repository-root `scripts/`. State that billing-total matches are duplicate candidates, not proof of a complete import. State that only non-NULL descriptions must be English.

- [x] **Step 2: Align workspace instructions with runtime resolution**

Use `work_dir=$(mktemp -d "/tmp/gnucash-import.XXXXXX")`, copy the selected source script into `$work_dir`, run it from the repository root, and document `GNUCASH_IMPORT_ROOT` for execution from another directory. Store statement data, temporary scripts, and SQL only in `$work_dir`.

- [x] **Step 3: Shorten shared references without dropping operational details**

In `email-lookup.md`, replace `V10` and `2026-01-01` with named placeholders and explain how to locate the active Mail directory. In `gnucash-schema.md`, retain only fields and examples used by import scripts, correct the `text`/`varchar` inconsistency, and distinguish cleared statement imports from generic unreconciled examples. In `fixed-assets.md`, remove repeated rationale while preserving capitalization, acquisition cost, valuation, disposal, and tax caveats.

- [x] **Step 4: Rewrite the account reference template**

Use the headings `Accounts`, `Access`, `Statement Data`, `Mapping`, and `Source-specific Rules`. Include placeholders for the script path, authentication, browser extraction, exact column/input format, mapping table, and exceptions. Do not include cache refresh, generic review columns, SQL execution, or a copied Email Lookup paragraph.

- [x] **Step 5: Check the shared documents**

Run searches that must return no matches:

```bash
rg 'Supported Sources|V10|2026-01-01|tmp/\{source_slug\}|Display transactions sorted by date' \
  .kiro/skills/gnucash-import/SKILL.md \
  .kiro/skills/gnucash-import/references/email-lookup.md \
  .kiro/skills/gnucash-import/references/templates/reference-template.md
```

Expected: no output.

---

### Task 4: Bank and securities account references

**Files:**
- Modify: `.kiro/skills/gnucash-import/references/accounts/docomo-smtb-net-bank.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/jre-bank.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/mufg-bank.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/sbi-securities.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/sbi-shinsei-bank.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/sompo-japan-dc.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/sony-bank.md`

**Interfaces:**
- Consumes: shared workflow from Task 3 and personal rule schema from Task 2.
- Produces: delta-only references for bank deposits, transfers, multi-currency flows, funds, stocks, fees, tax, and quantities.

- [x] **Step 1: Apply the standard account-reference structure**

Put the script path directly below each title. Merge authentication and navigation into `Access`; merge browser and script input formats into `Statement Data`; keep mapping tables in `Mapping`; move duplicate lookbacks, mirror transfers, quantity handling, and history limits to `Source-specific Rules`.

- [x] **Step 2: Remove personal identities from bank documents**

Replace identity-bearing rows and samples in DOCOMO SMTB, MUFG, and Sony references with a statement that personal transfer rules come from `../personal.json`, using `../personal.example.json` as the schema. Keep public benefit, tax, card debit, interest, insurance, and currency-transfer mappings in the account document.

- [x] **Step 3: Preserve securities arithmetic**

Keep SBI Securities and Sompo Japan DC security-name mappings, trade and settlement dates, fee/tax splits, `value_num`, `quantity_num`, denominators, and all source-specific subcommands. Remove only shared import boilerplate and generic review-column descriptions.

- [x] **Step 4: Verify bank and securities references against scripts**

Check every documented command and mapping name against its corresponding script. Run:

```bash
rg 'tmp/|Check if `account-guid-cache|Display transactions sorted|シバタ|Wife|Parents|Reimbursement:Friend' \
  .kiro/skills/gnucash-import/references/accounts/{docomo-smtb-net-bank,jre-bank,mufg-bank,sbi-securities,sbi-shinsei-bank,sompo-japan-dc,sony-bank}.md
```

Expected: no output.

---

### Task 5: Credit-card account references

**Files:**
- Modify: `.kiro/skills/gnucash-import/references/accounts/amazon-mastercard-gold.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/ana-super-flyers-gold-card.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/gold-point-card-plus.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/lumine-card.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/luxury-card-mastercard-titanium.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/paypay-card-jcb.md`

**Interfaces:**
- Consumes: shared credit-card rules from SKILL.md.
- Produces: source-specific access, confirmed/unconfirmed formats, discounts, points, split purchases, and subcommands.

- [x] **Step 1: Remove repeated card workflow**

Delete copied billing-total SQL, common duplicate-count logic, payment registration, current-cycle explanation, cache refresh, review, and SQL execution. Link to SKILL.md for common card behavior.

- [x] **Step 2: Preserve source-specific card behavior**

Keep confirmed and unconfirmed extraction formats, statement-specific fields, LUMINE discount handling, Luxury Card points and KDDI split logic, accepted command variants, and merchant mapping tables. Replace real cardholder or person values in examples with dummy labels.

- [x] **Step 3: Verify card documents against scripts**

Check each command branch in the six scripts and confirm every special mode remains documented. Search for duplicated boilerplate:

```bash
rg 'Check if `account-guid-cache|Display transactions sorted|billing statement has already|Current Statement \(Unconfirmed\)|tmp/' \
  .kiro/skills/gnucash-import/references/accounts/{amazon-mastercard-gold,ana-super-flyers-gold-card,gold-point-card-plus,lumine-card,luxury-card-mastercard-titanium,paypay-card-jcb}.md
```

Expected: no output except source-specific headings needed to distinguish confirmed and unconfirmed data formats.

---

### Task 6: Stored-value, transit, and reward account references

**Files:**
- Modify: `.kiro/skills/gnucash-import/references/accounts/amazon-gc.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/amazon-point.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/ana-mileage-club.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/ana-sky-coin.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/bic-point.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/dpoint.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/hapitas.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/ihg-rewards-club.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/jre-point.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/marriott-rewards.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/pasmo.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/ponta.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/rakuten-super-point.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/revolut.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/starbucks.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/suica.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/v-point.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/world-of-hyatt.md`
- Modify: `.kiro/skills/gnucash-import/references/accounts/yodobashi-gold-point.md`

**Interfaces:**
- Consumes: shared workflow, email lookup, and personal settings schema.
- Produces: concise references for balance direction, order lookup, points valuation, transit parsing, station/company mapping, and source-specific account selection.

- [x] **Step 1: Apply the standard structure and remove common boilerplate**

Retain exact browser columns, whitespace/tab/newline behavior, signs, pagination, skipped balance rows, points valuation, and merchant or transaction-type mappings. Remove generic workflow and review columns.

- [x] **Step 2: Separate transit personal values**

In Suica and PASMO references, document that `nearest_station` comes from `../personal.json`. Remove the real station from tracked station tables when its only purpose is personal detection; retain stations that are general railway-company exceptions. Keep Suica commute-pair behavior expressed with placeholders.

- [x] **Step 3: Correct known reference defects**

Change the dPoint script reference to `scripts/dpoint_import.py`. Change account-level email links to `../email-lookup.md` only where source-specific lookup is actually needed. Ensure every browser command includes `--auto-connect`.

- [x] **Step 4: Verify reward and transit documents against scripts**

Run:

```bash
rg 'tmp/|Check if `account-guid-cache|Display transactions sorted|d_point_import|\]\(email-lookup\.md\)|新宿御苑' \
  .kiro/skills/gnucash-import/references/accounts
```

Expected: no output. Then manually compare each retained parsing rule and mapping table with the corresponding script.

---

### Task 7: Repository-wide validation and review

**Files:**
- Test: `tests/test_runtime_paths.py`
- Test: `tests/test_personal_rules.py`
- Review: `.kiro/skills/gnucash-import/**/*.md`
- Review: `scripts/*.py`

**Interfaces:**
- Consumes: all outputs from Tasks 1 through 6.
- Produces: evidence that documentation, scripts, private settings, and links remain consistent.

- [x] **Step 1: Validate Markdown links and source pairs**

Run this temporary validator without writing it to the repository:

```bash
python3 - <<'PY'
from pathlib import Path
import re

root = Path('.kiro/skills/gnucash-import')
for doc in root.rglob('*.md'):
    for target in re.findall(r'\\[[^]]+\\]\\(([^)]+)\\)', doc.read_text()):
        if '://' in target or target.startswith('#'):
            continue
        resolved = (doc.parent / target.split('#', 1)[0]).resolve()
        assert resolved.exists(), f'{doc}: missing {target}'

scripts = {
    path.stem.removesuffix('_import').replace('_', '-')
    for path in Path('scripts').glob('*_import.py')
}
references = {
    path.stem
    for path in (root / 'references/accounts').glob('*.md')
}
assert len(scripts) == 32
assert scripts == references, (scripts - references, references - scripts)
for reference in (root / 'references/accounts').glob('*.md'):
    script = reference.stem.replace('-', '_') + '_import.py'
    assert script in reference.read_text(), f'{reference}: missing {script}'
PY
```

Expected: exit 0 with no output. Do not retain the validator.

- [x] **Step 2: Measure duplication reduction**

Count total Markdown lines and repeated substantive lines across account references using the audit method from the design phase. Confirm these phrases occur only in SKILL.md or nowhere:

```text
Check if `account-guid-cache.json`
Display transactions sorted by date descending
User reviews and specifies manual overrides
Execute SQL to insert transactions
If you don't know the account or the merchant
```

Expected: account-reference Markdown is materially shorter and no phrase is repeated across source files.

- [x] **Step 3: Scan tracked files for migrated personal values**

Search tracked Markdown and Python for every real value moved to ignored `personal.json`. Build the search terms from the pre-edit files without printing them in logs or the final response.

Expected: no matches outside ignored `personal.json`.

- [x] **Step 4: Run all automated checks**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts .kiro/skills/gnucash-import/references/templates/script-template.py
basedpyright scripts .kiro/skills/gnucash-import/references/templates/script-template.py
git -P diff --check
```

Expected: unit tests pass, compileall exits 0, basedpyright reports 0 errors, and diff check reports no whitespace errors.

- [x] **Step 5: Perform independent reviews**

Use `python-reviewer` for the configuration and runtime-path changes, `security-reviewer` for personal-data handling, and `code-reviewer` for the full diff. Resolve all critical, high, and medium findings, then rerun only the checks affected by fixes.

- [x] **Step 6: Report the result**

Report files added, removed, and reorganized; before/after Markdown line counts; personal-data scan status; test and type-check results; and any retained caveat. Do not include values from `personal.json`.
