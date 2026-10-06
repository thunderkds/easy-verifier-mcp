"""T048 - the optional finance pack (area #3, DDR-0008 §4, FR-053).

AC1 money-named fields declared or typed as binary floating point count
against #3 (CWE-1339 / ISO/IEC 5055 cited, per-language decimal-type docs in
the registry); decimals and integer minor units never count, nor do non-money
names. AC2 ledger, transaction and payment tables without an audit column, and
UPDATE / DELETE aimed at a declared ledger, count; with no ledger both rules
abstain, never 0. AC3 an inactive pack contributes nothing (byte-identical
payload; area #3 stays unruled).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from easy_verifier.core.judge import (
    AREAS,
    PACK_FLOORS,
    PROJECT_DEFAULT,
    RATING_RULES,
    areas_without_rule,
)
from easy_verifier.core.registry import PACK_FIELDS, load_pack
from easy_verifier.core.score import score_repository
from easy_verifier.packs import PACKS
from easy_verifier.packs.finance import entity_key, is_ledger_name, is_money_name

FLOAT = "float_money_observed"
AUDIT = "ledger_tables_without_audit_columns_observed"
MUTATED = "ledger_rows_mutated_observed"
AREA = AREAS[2]
CONFIG = 'packs = ["finance"]\n'


def _write(root: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _repo(tmp_path: Path, files: dict[str, str], *, config: str | None = CONFIG):
    base = {"README.md": "# Shop\n\nA small service.\n"}
    if config is not None:
        base[".easy-verifier.toml"] = config
    return _write(tmp_path / "repo", {**base, **files})


def _score(repo: Path):
    return score_repository(repo, scope="project")


def _metric(result, name: str) -> dict:
    return next(
        m
        for m in result.to_dict()["metrics"]["metrics"]
        if m["dimension"] == "finance" and m["name"] == name
    )


def _value(result, name: str):
    outcome = _metric(result, name)["outcome"]
    return None if outcome["abstained"] else outcome["value"]


def _rating(result) -> dict:
    return next(r for r in result.to_dict()["ratings"] if r["dimension"] == "finance")


PY_FLOAT = (
    "from dataclasses import dataclass\n\n\n@dataclass\nclass Payment:\n"
    "    amount: float\n"
)
PY_DECIMAL = (
    "from dataclasses import dataclass\nfrom decimal import Decimal\n\n\n"
    "@dataclass\nclass Payment:\n    amount: Decimal\n"
)


# ---------------------------------------------------------------------------
# rule table, registry, activation


def test_finance_rules_are_cited_labelled_and_pending() -> None:
    rules = RATING_RULES["finance"]
    assert list(rules) == [FLOAT, AUDIT, MUTATED]
    assert sum(rule.weight for rule in rules.values()) == 100
    for rule in rules.values():
        assert rule.area == AREA
        assert (rule.comparison, rule.threshold) == ("at_most", 0)
        assert rule.threshold_citation == PROJECT_DEFAULT
        assert all(c.url.startswith("https://") for c in rule.metric_citation)
    labels = " ".join(c.label for c in rules[FLOAT].metric_citation)
    assert "CWE-1339" in labels and "ISO/IEC 5055" in labels
    assert PACK_FLOORS["finance"].value == 0.25
    assert "finance" in PACKS
    source = Path("src/easy_verifier/core/judge.py").read_text(encoding="utf-8")
    assert "PENDING user" in source  # weights are a proposal


def test_pack_patterns_live_in_the_registry_with_citations() -> None:
    entry = load_pack("finance")
    assert set(entry.fields) == set(PACK_FIELDS["finance"])
    urls = set()
    for items in entry.fields.values():
        for item in items:
            assert item.citation_url.startswith("https://")
            assert item.source_tag == "curated"
            urls.add(item.citation_url)
    # per-language decimal-type documentation
    for doc in ("docs.python.org", "BigDecimal", "developer.mozilla.org", "postgresql"):
        assert any(doc in url for url in urls), doc
    source = Path("src/easy_verifier/packs/finance.py").read_text(encoding="utf-8")
    assert '"amount"' not in source and "float64" not in source


@pytest.mark.parametrize(
    ("name", "money"),
    [
        ("amount", True),
        ("price", True),
        ("totalPrice", True),
        ("costPerUnit", True),
        ("lineCost", True),
        ("account_balance", True),
        ("amount_of_items", False),
        ("item_count", False),
        ("total_pages", False),
        ("total", False),
        ("totalCount", False),
        ("amount_cents", False),
        ("priceId", False),
        ("feeRate", False),
        ("quantity", False),
    ],
)
def test_money_names_are_conservative(name, money) -> None:
    assert is_money_name(name) is money


@pytest.mark.parametrize(
    ("name", "ledger"),
    [
        ("payments", True),
        ("Payment", True),
        ("LedgerEntry", True),
        ("ledger_entries", True),
        ("transactions", True),
        ("PaymentMethod", False),
        ("TransactionStatus", False),
        ("orders", False),
        ("users", False),
    ],
)
def test_ledger_names(name, ledger) -> None:
    assert is_ledger_name(name) is ledger


def test_entity_keys_join_tables_models_and_repositories() -> None:
    assert entity_key("payments") == entity_key("Payment") == "payment"
    assert entity_key("paymentRepository") == "payment"
    assert entity_key("ledger_entries") == entity_key("LedgerEntry") == "ledger_entry"


# ---------------------------------------------------------------------------
# AC1 float money


def test_float_amount_in_a_payments_model_is_unmet_and_cited(tmp_path) -> None:
    result = _score(_repo(tmp_path, {"src/payments.py": PY_FLOAT}))
    metric = _metric(result, FLOAT)
    assert metric["outcome"] == {"abstained": False, "value": 1}
    assert "src/payments.py:6 (amount: float)" in metric["derivation"]
    entry = next(i for i in _rating(result)["inputs"] if i["metric_name"] == FLOAT)
    assert entry["passed"] is False and entry["area"] == AREA
    assert any("CWE-1339" in c["label"] for c in entry["metric_citation"])


def test_decimal_amount_is_met(tmp_path) -> None:
    result = _score(_repo(tmp_path, {"src/payments.py": PY_DECIMAL}))
    assert _value(result, FLOAT) == 0
    entry = next(i for i in _rating(result)["inputs"] if i["metric_name"] == FLOAT)
    assert entry["passed"] is True


@pytest.mark.parametrize(
    ("path", "text", "expected"),
    [
        # None: no money-named field at all, so nothing to judge (abstains);
        # a counted non-money name would give 1.
        # TypeScript / JavaScript number is a double
        ("src/a.ts", "export class Dto {\n  price!: number;\n}\n", 1),
        ("src/a.ts", "export interface I {\n  price?: number | null;\n}\n", 1),
        ("src/a.ts", "export class Dto {\n  price!: string;\n}\n", 0),
        ("src/a.ts", "const s = z.object({\n  price: z.number(),\n});\n", None),
        ("src/a.ts", "export class C {\n  amountCents!: number;\n}\n", None),
        (
            "src/a.ts",
            "export class P {\n  totalPages!: number;\n  total!: number;\n}\n",
            None,
        ),
        # Mongoose
        (
            "src/s.js",
            "const s = new Schema({\n  amount: { type: Number, default: 0 },\n});\n",
            1,
        ),
        (
            "src/s.js",
            "const s = new Schema({\n  amount: Schema.Types.Decimal128,\n});\n",
            0,
        ),
        # Prisma
        ("prisma/schema.prisma", "model Ingredient {\n  costPerUnit Float\n}\n", 1),
        (
            "prisma/schema.prisma",
            "model Item {\n  price Decimal @db.Decimal(10, 2)\n}\n",
            0,
        ),
        # SQL, also inside a migration string
        ("db/001.sql", 'CREATE TABLE fees (\n  "fee" double precision\n);\n', 1),
        (
            "db/001.sql",
            "CREATE TABLE p (\n  amount REAL,\n  price NUMERIC(10,2)\n);\n",
            1,
        ),
        ("db/001.sql", "CREATE TABLE p (\n  amount_cents bigint\n);\n", None),
        (
            "src/m.ts",
            'this.addSql(`create table "v" ("price" numeric(10,2) not null);`);\n',
            0,
        ),
        # Python ORMs and annotations
        ("src/m.py", "class P(models.Model):\n    price = models.FloatField()\n", 1),
        (
            "src/m.py",
            "class P(models.Model):\n    price = models.DecimalField(max_digits=9)\n",
            0,
        ),
        ("src/m.py", "class P(Base):\n    amount = Column(Float)\n", 1),
        ("src/m.py", "def charge(amount: Optional[float]) -> None:\n    pass\n", 1),
        (
            "src/m.py",
            "def f(amount_cents: int, amount_of_items: float) -> None:\n    pass\n",
            None,
        ),
        # Java, C#, Go, Rust
        ("src/P.java", "class P {\n  private double price;\n}\n", 1),
        ("src/P.java", "class P {\n  private BigDecimal price;\n}\n", 0),
        ("src/P.cs", "class P {\n  public decimal Price { get; set; }\n}\n", 0),
        ("src/p.go", "type P struct {\n\tPrice float64\n}\n", 1),
        ("src/p.rs", "struct P {\n    price: f64,\n}\n", 1),
    ],
)
def test_float_money_per_language(tmp_path, path, text, expected) -> None:
    assert _value(_score(_repo(tmp_path, {path: text})), FLOAT) == expected


def test_no_money_field_abstains_and_below_floor(tmp_path) -> None:
    result = _score(_repo(tmp_path, {"src/app.py": "def f(count: float):\n    pass\n"}))
    assert _metric(result, FLOAT)["outcome"]["abstained"] is True
    assert "nothing to judge" in _metric(result, FLOAT)["outcome"]["reason"]
    assert _rating(result)["kind"] == "rating_abstention"


# ---------------------------------------------------------------------------
# AC2 append-only ledgers

LEDGER_SQL = (
    "CREATE TABLE payments (\n"
    "  id bigint PRIMARY KEY,\n"
    "  amount numeric(12,2) NOT NULL,\n"
    "  created_at timestamptz NOT NULL\n"
    ");\n"
    "CREATE TABLE ledger_entries (\n"
    "  id bigint PRIMARY KEY,\n"
    "  amount numeric(12,2) NOT NULL\n"
    ");\n"
    "CREATE TABLE payment_methods (\n"
    "  id bigint PRIMARY KEY\n"
    ");\n"
)


def test_ledger_without_audit_column_counts(tmp_path) -> None:
    result = _score(_repo(tmp_path, {"db/schema.sql": LEDGER_SQL}))
    metric = _metric(result, AUDIT)
    assert metric["outcome"] == {"abstained": False, "value": 1}
    assert "db/schema.sql:6 (ledger_entries)" in metric["derivation"]
    assert _value(result, MUTATED) == 0
    assert _value(result, FLOAT) == 0


def test_ledger_mutations_count_only_against_declared_ledgers(tmp_path) -> None:
    service = (
        "export class S {\n"
        "  async a() {\n"
        "    await this.prisma.payment.update({ where: { id } });\n"
        "    await this.paymentRepository.delete(id);\n"
        "    await this.prisma.user.update({ where: { id } });\n"
        "    await this.prisma.$transaction([]);\n"
        "    await this.db.query('UPDATE ledger_entries SET amount = 0');\n"
        "    await this.db.query('DELETE FROM orders WHERE id = 1');\n"
        "  }\n"
        "}\n"
    )
    result = _score(_repo(tmp_path, {"db/schema.sql": LEDGER_SQL, "src/s.ts": service}))
    metric = _metric(result, MUTATED)
    assert metric["outcome"] == {"abstained": False, "value": 3}
    for line in (
        "src/s.ts:3 (payment)",
        "src/s.ts:4 (paymentRepository)",
        "src/s.ts:7",
    ):
        assert line in metric["derivation"]


def test_orm_models_and_inherited_audit_columns(tmp_path) -> None:
    files = {
        "prisma/schema.prisma": (
            "model Transaction {\n  id Int @id\n  amount Decimal\n"
            "  createdAt DateTime @default(now())\n}\n"
            "model Payment {\n  id Int @id\n  amount Decimal\n}\n"
        ),
        "src/entities/ledger.entity.ts": (
            "@Entity()\nexport class LedgerEntry extends BaseEntity {\n"
            "  @Property()\n  amount!: string;\n}\n"
        ),
        "src/models.py": (
            "class Transfer(Base):\n    __tablename__ = 'transfers'\n"
            "    id = Column(Integer)\n\n\nclass Other:\n    created_at = 1\n"
        ),
    }
    metric = _metric(_score(_repo(tmp_path, files)), AUDIT)
    # Payment (Prisma) and Transfer (SQLAlchemy) lack one; Transaction has
    # createdAt; LedgerEntry inherits from a base class and is never counted.
    assert metric["outcome"] == {"abstained": False, "value": 2}
    assert "prisma/schema.prisma:6 (Payment)" in metric["derivation"]
    assert "src/models.py:1 (Transfer)" in metric["derivation"]


def test_no_ledger_abstains_never_zero(tmp_path) -> None:
    result = _score(_repo(tmp_path, {"src/payments.py": PY_FLOAT}))
    for name in (AUDIT, MUTATED):
        outcome = _metric(result, name)["outcome"]
        assert outcome["abstained"] is True
        assert "no ledger" in outcome["reason"]
    # one money rule measured: 50 of 100 weight reaches the measured floor
    assert _rating(result)["kind"] == "rating"


def test_ledger_code_is_quoted_for_the_agent(tmp_path) -> None:
    from easy_verifier.core.models import to_json_dict
    from easy_verifier.core.synthesis import combined_pack
    from easy_verifier.dimensions import dimension_names

    repo = _repo(tmp_path, {"db/schema.sql": LEDGER_SQL})
    packs = combined_pack(
        (*dimension_names(), "finance"),
        repo_path=repo,
        scope="project",
        packs=("finance",),
    )
    slot = next(s for s in packs.slots if s.dimension == "finance")
    text = json.dumps(to_json_dict(slot.pack))
    assert "CREATE TABLE ledger_entries" in text


def test_a_batched_read_says_later_batches_were_not_read(tmp_path) -> None:
    # tapchat-apis (2026-10-06): 200 of 450 sources read; its transactions
    # table sat in a later batch, and "no ledger found" read as a fact.
    files = {f"src/m{i:03}.py": f"def f{i}():\n    return {i}\n" for i in range(205)}
    files["src/payments.py"] = PY_FLOAT
    result = _score(_repo(tmp_path, files))
    reason = _metric(result, AUDIT)["outcome"]["reason"]
    assert "later batches were not read" in reason


# ---------------------------------------------------------------------------
# AC3 inactive


def test_inactive_pack_leaves_no_trace_and_area_stays_unruled(tmp_path) -> None:
    result = _score(_repo(tmp_path, {"src/payments.py": PY_FLOAT}, config=None))
    payload = result.serialize()
    assert "finance" not in payload and FLOAT not in payload
    assert AREA in result.to_dict()["areas_without_rule"]
    assert AREA in areas_without_rule()
    assert AREA not in areas_without_rule(("finance",))


def test_active_pack_measures_area_three_and_is_disclosed(tmp_path) -> None:
    result = _score(_repo(tmp_path, {"src/payments.py": PY_FLOAT}))
    payload = result.to_dict()
    assert AREA not in payload["areas_without_rule"]
    assert AREA in payload["areas_measured"]
    assert "packs active: finance" in payload["overall"]["disclosure"]


def test_agent_pick_activates_and_replay_is_byte_equal(tmp_path) -> None:
    repo = _repo(tmp_path, {"src/payments.py": PY_FLOAT}, config=None)
    first = score_repository(repo, scope="project", agent_input={"packs": ["finance"]})
    assert _value(first, FLOAT) == 1
    again = score_repository(repo, scope="project", agent_input={"packs": ["finance"]})
    assert again.serialize() == first.serialize()
