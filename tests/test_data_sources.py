import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from reels_maker.data_sources import (
    ColumnSpec,
    DataSchema,
    DataSourceError,
    RightsProvenance,
    load_data_source,
)


RIGHTS = RightsProvenance(
    source_title="Synthetic test observations",
    license_name="CC0-1.0 (synthetic fixture)",
    license_url="https://example.invalid/synthetic",
    authorization_basis="Generated solely for this test",
    authorized=True,
)


def schema(locale="pl_PL"):
    return DataSchema(
        columns=(
            ColumnSpec("month", "string", "none", "reject"),
            ColumnSpec("revenue", "decimal", "PLN", "null", ("NA",), currency="PLN"),
        ),
        locale=locale,
        currency="PLN",
    )


class DataSourceTests(unittest.TestCase):
    def test_csv_typed_locale_and_checksum_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic.csv"
            # CSV decimal commas must be quoted so one record maps to two columns.
            path.write_text('month,revenue\nJan,"1 234,50"\nFeb,NA\n', encoding="utf-8")
            result = load_data_source(path, schema=schema(), rights=RIGHTS)
            self.assertEqual(result.rows[0]["revenue"], Decimal("1234.50"))
            self.assertIsNone(result.rows[1]["revenue"])
            self.assertEqual(len(result.sha256), 64)
            self.assertEqual(result.source_path, str(path.resolve()))
            self.assertEqual(result.rights, RIGHTS)

    def test_json_and_us_locale(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.json"
            path.write_text(json.dumps([{"month": "Jan", "revenue": 1234.5}]), encoding="utf-8")
            result = load_data_source(path, schema=schema("en_US"), rights=RIGHTS)
            self.assertEqual(result.rows[0]["revenue"], Decimal("1234.5"))

    def test_rejects_ambiguous_number_and_missing_authorization(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.json"
            path.write_text('[{"month":"Jan","revenue":"1,234.50"}]', encoding="utf-8")
            with self.assertRaisesRegex(DataSourceError, "locale-ambiguous|invalid"):
                load_data_source(path, schema=schema(), rights=RIGHTS)
            with self.assertRaisesRegex(DataSourceError, "authorization"):
                load_data_source(path, schema=schema(), rights=RightsProvenance("synthetic", "test", "id", "", False))

    def test_requires_explicit_units_currency_and_missing_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.json"
            path.write_text('[{"month":"Jan","revenue":1}]', encoding="utf-8")
            bad = DataSchema((ColumnSpec("revenue", "decimal", "", "reject", currency="PLN"),), "en_US", "PLN")
            with self.assertRaisesRegex(DataSourceError, "unit"):
                load_data_source(path, schema=bad, rights=RIGHTS)
            missing = DataSchema((ColumnSpec("revenue", "decimal", "PLN", "null", currency="PLN"),), "en_US", "PLN")
            with self.assertRaisesRegex(DataSourceError, "missing_tokens"):
                load_data_source(path, schema=missing, rights=RIGHTS)

    def test_xlsx_is_explicit_and_optional(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.xlsx"
            path.touch()
            with self.assertRaisesRegex(DataSourceError, "sheet name"):
                load_data_source(path, schema=schema(), rights=RIGHTS)

    def test_rejects_empty_data_and_noncanonical_date(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.csv"
            path.write_text("day\n20260105\n", encoding="utf-8")
            date_schema = DataSchema(
                (ColumnSpec("day", "date", "none", "reject"),),
                "en_US", "none")
            with self.assertRaisesRegex(DataSourceError, "ISO YYYY-MM-DD"):
                load_data_source(path, schema=date_schema, rights=RIGHTS)
            path.write_text("day\n", encoding="utf-8")
            with self.assertRaisesRegex(DataSourceError, "at least one data row"):
                load_data_source(path, schema=date_schema, rights=RIGHTS)


if __name__ == "__main__":
    unittest.main()
