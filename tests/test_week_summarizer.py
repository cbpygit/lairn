"""Tests for week summarizer formatting."""
from datetime import date

from lairn.reporting.week_summarizer import WeekActivitiesWithDateInfo, WeekSubjectActivities


def test_str_fmt_with_nomy_data():
    """Test that Nomy section is included when data is present."""
    summary = WeekActivitiesWithDateInfo(
        week_number=1,
        year=2026,
        start_date=date(2026, 1, 6),
        end_date=date(2026, 1, 12),
        summary="Test summary with Nomy data.",
        activities=[
            WeekSubjectActivities(subject="Deutsch", activities=["Reading practice"])
        ],
        nomy_activities="- **Math**: Addition exercises",
        is_preliminary=False,
    )
    
    result = summary.str_fmt()
    
    assert "(Vorversion)" not in result
    assert "## Nomy School" in result
    assert "Math" in result
    assert "Nomy Wochenbericht liegt noch nicht vor" not in result


def test_str_fmt_without_nomy_data():
    """Test that Nomy section is omitted when data is missing, but Vorversion marker is present."""
    summary = WeekActivitiesWithDateInfo(
        week_number=1,
        year=2026,
        start_date=date(2026, 1, 6),
        end_date=date(2026, 1, 12),
        summary="Test summary without Nomy data.",
        activities=[
            WeekSubjectActivities(subject="Deutsch", activities=["Reading practice"])
        ],
        nomy_activities=None,
        is_preliminary=True,
    )
    
    result = summary.str_fmt()
    
    assert "(Vorversion)" in result
    assert "## Nomy School" not in result
    assert "Nomy Wochenbericht liegt noch nicht vor" not in result


def test_str_fmt_with_nomy_data_not_preliminary():
    """Test that no Vorversion marker when Nomy data is present."""
    summary = WeekActivitiesWithDateInfo(
        week_number=1,
        year=2026,
        start_date=date(2026, 1, 6),
        end_date=date(2026, 1, 12),
        summary="Test summary.",
        activities=[
            WeekSubjectActivities(subject="Deutsch", activities=["Reading practice"])
        ],
        nomy_activities="- **Math**: Addition",
        is_preliminary=False,
    )
    
    result = summary.str_fmt()
    
    assert "(Vorversion)" not in result
    assert "## Nomy School" in result

