import argparse
import os
import shlex

import invoke


@invoke.task(name="del")
def delete_return_registration(ctx: invoke.Context, identifier: str) -> None:
    """Delete a local return registration by ID or external ID."""
    ctx.run(
        f"uv run python -m _stool.reg {shlex.quote(identifier)}",
        pty=True,
        echo=True,
    )


def _delete_return_registration(identifier: str) -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings")

    import django  # noqa: PLC0415

    django.setup()

    from django.conf import settings  # noqa: PLC0415

    from returns.models import ReturnRegistration  # noqa: PLC0415

    if not settings.DEV:
        raise invoke.Exit("Return registrations can only be deleted in development.")

    lookup = (
        {"pk": int(identifier)}
        if identifier.isdecimal()
        else {"external_id": identifier}
    )
    registration = ReturnRegistration.objects.get(**lookup)
    registration_id = registration.pk
    external_id = registration.external_id
    registration.delete()
    print(  # noqa: T201
        f"Deleted return registration {registration_id} ({external_id})."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("identifier")
    args = parser.parse_args()
    _delete_return_registration(args.identifier)


if __name__ == "__main__":
    main()
