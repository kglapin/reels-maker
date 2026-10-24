import unittest
from decimal import Decimal

from reels_maker.data_integrity import (
    DataIntegrityError,
    aggregate,
    divide,
    validate_loaded_data,
)
from reels_maker.data_sources import ColumnSpec, DataSchema, LoadedData, RightsProvenance


RIGHTS = RightsProvenance("Synthetic fixture", "test", "synthetic", "generated for tests", True)


def loaded(rows):
    schema = DataSchema(
        (ColumnSpec("amount", "decimal", "USD", "null", ("NA",), currency="USD"),),
        "en_US",
        "USD",
    )
    return LoadedData(tuple(rows), schema, "synthetic.json", "a" * 64, RIGHTS)


class DataIntegrityTests(unittest.TestCase):
    def test_sum_is_deterministic_and_returns_explicit_ledger(self):
        data = loaded(({"amount": Decimal("0.1")}, {"amount": Decimal("0.2")}))
        result = aggregate(
            data, column="amount", operation="sum", period="2026-01",
            currency="USD", decimal_places=2, rounding_policy="half_up",
        )
        self.assertEqual(result.exact_value, Decimal("0.3"))
        self.assertEqual(result.value, Decimal("0.30"))
        self.assertEqual(result.unit, "USD")
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.period, "2026-01")
        self.assertEqual(result.ledger.input_columns, ("amount",))
        self.assertEqual(result.ledger.row_count, 2)
        self.assertEqual(result.ledger.rounding_policy, "half_up")

    def test_mean_and_named_rounding_are_stable(self):
        result = aggregate(
            loaded(({"amount": Decimal("1")}, {"amount": Decimal("2")})),
            column="amount", operation="mean", period="FY2026", currency="USD",
            decimal_places=2, rounding_policy="half_even",
        )
        self.assertEqual(result.exact_value, Decimal("1.5"))
        self.assertEqual(result.value, Decimal("1.50"))

    def test_null_missing_currency_and_unknown_column_fail_closed(self):
        with self.assertRaisesRegex(DataIntegrityError, "null"):
            aggregate(loaded(({"amount": None},)), column="amount", operation="sum",
                      period="2026", currency="USD", decimal_places=2, rounding_policy="half_up")
        data = loaded(({"amount": Decimal("1")},))
        for kwargs in ({"currency": "EUR"}, {"column": "absent"}):
            args = {"column": "amount", "operation": "sum", "period": "2026",
                    "currency": "USD", "decimal_places": 2, "rounding_policy": "half_up"}
            args.update(kwargs)
            with self.assertRaises(DataIntegrityError):
                aggregate(data, **args)

    def test_validator_rejects_nonfinite_and_division_rejects_zero(self):
        with self.assertRaisesRegex(DataIntegrityError, "finite Decimal"):
            validate_loaded_data(loaded(({"amount": Decimal("NaN")},)))
        with self.assertRaisesRegex(DataIntegrityError, "zero"):
            divide(Decimal("1"), Decimal("0"), numerator_unit="USD", denominator_unit="USD",
                   output_unit="ratio", currency="none", period="2026", decimal_places=2,
                   rounding_policy="half_up")

    def test_validator_requires_authorization_and_typed_integer_values(self):
        unauthorized = LoadedData(
            ({"amount": Decimal("1")},), loaded(({"amount": Decimal("1")},)).schema,
            "synthetic.json", "b" * 64,
            RightsProvenance("fixture", "test", "test", "not approved", False))
        with self.assertRaisesRegex(DataIntegrityError, "authorization"):
            validate_loaded_data(unauthorized)
        int_schema = DataSchema(
            (ColumnSpec("count", "integer", "items", "reject"),), "en_US", "none")
        invalid_int = LoadedData(({"count": True},), int_schema, "synthetic.json", "c" * 64, RIGHTS)
        with self.assertRaisesRegex(DataIntegrityError, "expected integer"):
            validate_loaded_data(invalid_int)

    def test_divide_requires_explicit_units_and_does_not_change_percent_basis(self):
        self.assertEqual(
            divide(Decimal("1"), Decimal("3"), numerator_unit="items", denominator_unit="items",
                   output_unit="fraction", currency="none", period="2026", decimal_places=3,
                   rounding_policy="half_up"),
            Decimal("0.333"),
        )
        with self.assertRaisesRegex(DataIntegrityError, "output_unit"):
            divide(Decimal("1"), Decimal("2"), numerator_unit="items", denominator_unit="items",
                   output_unit="", currency="none", period="2026", decimal_places=2,
                   rounding_policy="half_up")


if __name__ == "__main__":
    unittest.main()
