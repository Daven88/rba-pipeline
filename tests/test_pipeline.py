import importlib
from datetime import date

import pandas as pd
import pytest

from main import run_days_from
from src.project_extension.ml.train import categorise_change
from src.project_extension.transform.transform_rba_tables import clean


# main.py imports every stage, so a broken module anywhere fails the build here
# rather than halfway through a scheduled run. Every cloud client in these
# modules is constructed inside a function, so importing needs no credentials.
MODULES = [
    "main",
    "src.project_extension.extract.extract_rba_tables",
    "src.project_extension.transform.transform_rba_tables",
    "src.project_extension.ml.train",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module):
    importlib.import_module(module)


class TestRunDays:
    """The gate decides whether an unattended run happens at all. Getting it
    wrong is invisible until a meeting is missed, weeks later."""

    MEETING = date(2026, 9, 29)

    def test_runs_two_days_before_a_meeting(self):
        assert date(2026, 9, 27) in run_days_from({self.MEETING})

    def test_runs_fourteen_days_after_a_meeting(self):
        assert date(2026, 10, 13) in run_days_from({self.MEETING})

    def test_does_not_run_on_the_meeting_day_itself(self):
        assert self.MEETING not in run_days_from({self.MEETING})

    def test_does_not_run_the_day_before_a_meeting(self):
        assert date(2026, 9, 28) not in run_days_from({self.MEETING})

    def test_each_meeting_contributes_exactly_two_run_days(self):
        meetings = {date(2026, 9, 29), date(2026, 11, 3), date(2026, 12, 8)}
        assert len(run_days_from(meetings)) == 2 * len(meetings)

    def test_empty_calendar_yields_no_run_days(self):
        assert run_days_from(set()) == set()


class TestCategoriseChange:
    """Defines the model's target variable - a sign error here silently
    relabels every rate decision in training."""

    def test_positive_change_is_a_raise(self):
        assert categorise_change(0.25) == 'raise'

    def test_zero_change_is_a_hold(self):
        assert categorise_change(0.0) == 'hold'

    def test_negative_change_is_a_cut(self):
        assert categorise_change(-0.25) == 'cut'

    def test_small_positive_change_is_still_a_raise(self):
        # The RBA moved 0.15 in November 2020
        assert categorise_change(0.15) == 'raise'


class TestClean:
    """transform_rba_tables selects columns by position, so a column the RBA
    inserts upstream shifts every field silently. These tests pin the shape."""

    CONFIG = {
        "skiprows": 2,
        "usecols": [0, 2],
        "columns": ["date", "value"],
    }

    CSV = (
        b"Title row to skip\n"
        b"Another header row to skip\n"
        b"Series ID,ignored,ACGT\n"
        b"31-Mar-2026,junk,3.5\n"
        b"30-Jun-2026,junk,3.8\n"
    )

    def test_returns_the_configured_columns(self):
        out = clean(self.CSV, self.CONFIG)
        assert list(out.columns) == ["date", "value"]

    def test_drops_the_series_id_row(self):
        out = clean(self.CSV, self.CONFIG)
        assert len(out) == 2

    def test_parses_dates_day_first(self):
        out = clean(self.CSV, self.CONFIG)
        assert out["date"].iloc[0] == pd.Timestamp("2026-03-31")

    def test_values_are_numeric(self):
        out = clean(self.CSV, self.CONFIG)
        assert out["value"].iloc[0] == 3.5
        assert out["value"].dtype.kind == "f"

    def test_rows_that_cannot_be_parsed_are_dropped(self):
        csv = self.CSV + b"30-Sep-2026,junk,not-a-number\n"
        out = clean(csv, self.CONFIG)
        assert len(out) == 2
