"""Tests for term extraction sanitization."""

import pytest

from auto_ontology.semantic.models import (
    ColumnAttributeSpec,
    RawTableTermsResult,
    RawTermProposal,
    TermColumnRef,
)
from auto_ontology.semantic.term_extractor import (
    _fallback_result,
    _normalize_label,
    _sanitize_result,
)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Rata-rata Nilai", "Rata-Rata Nilai"),  # reduplication keeps its hyphen
        ("Tanggal Pesanan", "Tanggal Pesanan"),
        ("PurchaseOrder", "Purchase Order"),
        ("tidak diketahui", "fallback"),
        ("Unknown", "fallback"),
        ("Jumlah (Rp)", "fallback"),
        ("-Nilai", "fallback"),
    ],
)
def test_normalize_label(label: str, expected: str) -> None:
    assert _normalize_label(label, fallback="fallback") == expected


def test_fallback_term_is_described_in_indonesian() -> None:
    term = _fallback_result({"name": "dim_program"}, specs=[]).terms[0]
    assert term.description == "Entitas bisnis yang diwakili tabel dim_program"


def test_sanitize_uses_llm_display_names() -> None:
    specs = [
        ColumnAttributeSpec(
            source_column="amount",
            name="amount",
            datatype="numeric",
        ),
        ColumnAttributeSpec(
            source_column="status",
            name="status",
            datatype="text",
        ),
    ]
    raw = RawTableTermsResult(
        terms=[
            RawTermProposal(
                name="PurchaseOrder",
                description="A purchase order",
                attributes=[
                    TermColumnRef(
                        source_column="amount",
                        display_name="TotalAmount",
                    )
                ],
            )
        ]
    )

    result = _sanitize_result(raw, table={"name": "purchase_orders"}, specs=specs)

    assert len(result.terms) == 1
    assert result.terms[0].name == "Purchase Order"
    assigned = {a.source_column: a.display_name for a in result.terms[0].attributes}
    assert assigned == {"amount": "Total Amount", "status": "status"}
    assert specs[0].display_name == "Total Amount"
    assert specs[1].display_name == "status"


def test_sanitize_assigns_orphan_specs_to_primary_term() -> None:
    specs = [
        ColumnAttributeSpec(
            source_column="amount",
            name="amount",
            datatype="numeric",
        ),
        ColumnAttributeSpec(
            source_column="status",
            name="status",
            datatype="text",
        ),
    ]
    raw = RawTableTermsResult(
        terms=[
            RawTermProposal(
                name="Purchase Order",
                description="A purchase order",
                attributes=[
                    TermColumnRef(
                        source_column="amount",
                        display_name="Total Amount",
                    ),
                    TermColumnRef(
                        source_column="status",
                        display_name="Order Status",
                    ),
                ],
            )
        ]
    )

    result = _sanitize_result(raw, table={"name": "purchase_orders"}, specs=specs)

    assigned = {a.source_column: a.display_name for a in result.terms[0].attributes}
    assert assigned == {
        "amount": "Total Amount",
        "status": "Order Status",
    }
    assert specs[0].display_name == "Total Amount"
    assert specs[1].display_name == "Order Status"
