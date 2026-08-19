from __future__ import annotations

import argparse
import json
import os
import shlex
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import invoke

DATA_DIR = Path(__file__).with_name("data") / "parcellab_v4_inline_exchange"
DEFAULT_DYNAMODB_LOCAL_DIR = Path.home() / ".local/share/dynamodb-local"


def _load_payload(name: str) -> dict[str, Any]:
    with (DATA_DIR / name).open() as payload_file:
        return json.load(payload_file)


def _ensure_product_feed_table(client: Any, table_name: str) -> None:
    from botocore.exceptions import ClientError  # noqa: PLC0415

    try:
        client.describe_table(TableName=table_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "user_id_client_key", "KeyType": "HASH"},
                {"AttributeName": "sku", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id_client_key", "AttributeType": "S"},
                {"AttributeName": "sku", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        client.get_waiter("table_exists").wait(TableName=table_name)


@invoke.task
def start_dynamodb(
    ctx: invoke.Context,
    install_dir: str = str(DEFAULT_DYNAMODB_LOCAL_DIR),
    port: int = 8001,
) -> None:
    """Start DynamoDB Local for Returns product-feed development."""
    dynamodb_dir = Path(install_dir).expanduser().resolve()
    jar = dynamodb_dir / "DynamoDBLocal.jar"
    libraries = dynamodb_dir / "DynamoDBLocal_lib"
    if not jar.is_file() or not libraries.is_dir():
        raise invoke.Exit(
            f"DynamoDB Local not found in {dynamodb_dir}. "
            "Expected DynamoDBLocal.jar and DynamoDBLocal_lib/."
        )
    ctx.run(
        f"java -Djava.library.path={shlex.quote(str(libraries))} "
        f"-jar {shlex.quote(str(jar))} -sharedDb -port {int(port)}",
        pty=True,
        echo=True,
    )


@invoke.task
def seed_inline_exchange(
    ctx: invoke.Context,
    account_id: int,
    portal_code: str = "dev",
) -> None:
    """Seed a parcelLab v4 order, tracking, and inline-exchange product feed."""
    ctx.run(
        "uv run python -m _stool.parcellab "
        f"--account-id {int(account_id)} "
        f"--portal-code {shlex.quote(portal_code)}",
        pty=True,
        echo=True,
    )


def _seed_inline_exchange(account_id: int, portal_code: str) -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings")

    import django  # noqa: PLC0415

    django.setup()

    from boto3.dynamodb.types import TypeSerializer  # noqa: PLC0415
    from django.conf import settings  # noqa: PLC0415

    from account.models import Account  # noqa: PLC0415
    from api.clients import get_aws_dynamodb_client  # noqa: PLC0415
    from track.models import Order, Tracking  # noqa: PLC0415
    from track.types import LineItem, LineItemOrder  # noqa: PLC0415

    if not settings.DEV:
        raise invoke.Exit("This seed task is only available in development.")

    account = Account.objects.get(pk=int(account_id))
    order_data = _load_payload("order.json")
    order_number = order_data.pop("order_number")
    order_data["order_date"] = datetime.fromisoformat(order_data["order_date"])
    order_data["announced_delivery_date"] = date.fromisoformat(
        order_data["announced_delivery_date"]
    )
    for field in ("order_total_amount", "order_tax_amount", "order_net_amount"):
        order_data[field] = Decimal(order_data[field])
    order_data["articles_order"] = [
        LineItemOrder.model_validate(article)
        for article in order_data["articles_order"]
    ]
    order, order_created = Order.objects.update_or_create(
        account=account,
        order_number=order_number,
        defaults=order_data,
    )

    tracking_data = _load_payload("tracking.json")
    tracking_number = tracking_data.pop("tracking_number")
    courier = tracking_data.pop("courier")
    tracking_data["order"] = order
    tracking_data["order_number"] = order_number
    tracking_data["reporting_delivery_date"] = date.fromisoformat(
        tracking_data["reporting_delivery_date"]
    )
    tracking_data["articles"] = [
        LineItem.model_validate(article).model_dump(mode="json", exclude_none=True)
        for article in tracking_data["articles"]
    ]
    _, tracking_created = Tracking.objects.update_or_create(
        account=account,
        courier=courier,
        tracking_number=tracking_number,
        defaults=tracking_data,
    )

    feed_data = _load_payload("product_feed.json")
    feed_data["user_id_client_key"] = f"{account.pk}_{order.client_key}"
    serializer = TypeSerializer()
    client = get_aws_dynamodb_client()
    table_name = settings.RETURNS_PRODUCT_FEED_TABLE
    _ensure_product_feed_table(client, table_name)
    client.put_item(
        TableName=table_name,
        Item={key: serializer.serialize(value) for key, value in feed_data.items()},
    )

    print(  # noqa: T201
        f"{'Created' if order_created else 'Updated'} order {order_number}; "
        f"{'created' if tracking_created else 'updated'} tracking {tracking_number}."
    )
    print(f"Product feed item written to {table_name}.")  # noqa: T201
    print(  # noqa: T201
        f"Open http://localhost:8000/returns/{account.pk}/{portal_code}/"
    )
    print(  # noqa: T201
        f"Login with {order_number} / {order.recipient_email}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-id", required=True, type=int)
    parser.add_argument("--portal-code", default="dev")
    args = parser.parse_args()
    _seed_inline_exchange(args.account_id, args.portal_code)


if __name__ == "__main__":
    main()
