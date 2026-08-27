from unittest.mock import Mock, patch

import pytest

from _stool.reg import _delete_return_registration, delete_return_registration


def test_delete_task_runs_in_project_environment() -> None:
    context = Mock()

    delete_return_registration.body(context, "42")

    context.run.assert_called_once_with(
        "uv run python -m _stool.reg 42", pty=True, echo=True
    )


@pytest.mark.parametrize(
    ("identifier", "lookup"),
    [
        ("42", {"pk": 42}),
        (
            "13fcf4fc-040e-45d7-aec5-99c961992acd",
            {"external_id": "13fcf4fc-040e-45d7-aec5-99c961992acd"},
        ),
    ],
)
@patch("returns.models.ReturnRegistration.objects.get")
def test_delete_return_registration_resolves_identifier(
    get_registration: Mock,
    identifier: str,
    lookup: dict[str, object],
    settings,
) -> None:
    settings.DEV = True
    registration = get_registration.return_value
    registration.pk = 42
    registration.external_id = "13fcf4fc-040e-45d7-aec5-99c961992acd"

    _delete_return_registration(identifier)

    get_registration.assert_called_once_with(**lookup)
    registration.delete.assert_called_once_with()
