from __future__ import annotations

import json
import shlex
from typing import Any

import invoke

DEFAULT_LIMIT = 20
DEFAULT_REGION = "eu-central-1"
DEFAULT_TABLE = "product_feed"


def _validate_account_client(account_client: str) -> None:
    account, separator, client = account_client.partition("_")
    if not separator or not account.isdigit() or not client:
        raise invoke.Exit(
            "ACCOUNT_CLIENT must use the <account>_<client> format, "
            "for example 1624810_0001."
        )


def _deserialize_item(item: dict[str, Any]) -> dict[str, Any]:
    from boto3.dynamodb.types import TypeDeserializer  # noqa: PLC0415

    deserializer = TypeDeserializer()
    return {key: deserializer.deserialize(value) for key, value in item.items()}


def _get_items(
    dynamodb: Any,
    *,
    account_client: str,
    table_name: str,
    limit: int,
    sku: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if sku:
        response = dynamodb.get_item(
            TableName=table_name,
            Key={
                "user_id_client_key": {"S": account_client},
                "sku": {"S": sku},
            },
        )
        item = response.get("Item")
        return ([_deserialize_item(item)] if item else []), None

    response = dynamodb.query(
        TableName=table_name,
        KeyConditionExpression="user_id_client_key = :account_client",
        ExpressionAttributeValues={
            ":account_client": {"S": account_client},
        },
        Limit=limit,
    )
    items = [_deserialize_item(item) for item in response.get("Items", [])]
    last_key = response.get("LastEvaluatedKey")
    return items, _deserialize_item(last_key) if last_key else None


def _run_query(
    *,
    account_client: str,
    sku: str | None,
    limit: int,
    table_name: str,
    region: str,
    profile: str,
) -> None:
    import boto3  # noqa: PLC0415

    dynamodb = boto3.Session(
        profile_name=profile,
        region_name=region,
    ).client("dynamodb")
    items, last_key = _get_items(
        dynamodb,
        account_client=account_client,
        table_name=table_name,
        limit=limit,
        sku=sku,
    )
    result = {
        "table": table_name,
        "region": region,
        "account_client": account_client,
        "count": len(items),
        "items": items,
        "last_evaluated_key": last_key,
    }
    print(json.dumps(result, indent=2, default=str, sort_keys=True))  # noqa: T201


@invoke.task(
    positional=["account_client"],
    help={
        "account_client": "DynamoDB partition key in <account>_<client> format.",
        "sku": "Fetch one exact SKU instead of listing the partition.",
        "limit": "Maximum rows returned when listing a partition.",
        "table_name": "DynamoDB product-feed table name.",
        "region": "AWS region containing the table.",
        "profile": "AWS profile used for authentication.",
    },
)
def query(
    ctx: invoke.Context,
    account_client: str,
    sku: str | None = None,
    limit: int = DEFAULT_LIMIT,
    table_name: str = DEFAULT_TABLE,
    region: str = DEFAULT_REGION,
    profile: str = "default",
) -> None:
    """Query product_feed by an <account>_<client> partition key."""
    _validate_account_client(account_client)
    if limit < 1:
        raise invoke.Exit("LIMIT must be at least 1.")

    command = [
        "uv",
        "run",
        "python",
        "-m",
        "_stool.product_feed",
        account_client,
        "--limit",
        str(limit),
        "--table-name",
        table_name,
        "--region",
        region,
        "--profile",
        profile,
    ]
    if sku:
        command.extend(["--sku", sku])
    ctx.run(shlex.join(command), pty=True, echo=True)


def main() -> None:
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser()
    parser.add_argument("account_client")
    parser.add_argument("--sku")
    parser.add_argument("--limit", default=DEFAULT_LIMIT, type=int)
    parser.add_argument("--table-name", default=DEFAULT_TABLE)
    parser.add_argument("--region", default=DEFAULT_REGION)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args()
    _validate_account_client(args.account_client)
    if args.limit < 1:
        raise invoke.Exit("LIMIT must be at least 1.")
    _run_query(
        account_client=args.account_client,
        sku=args.sku,
        limit=args.limit,
        table_name=args.table_name,
        region=args.region,
        profile=args.profile,
    )


if __name__ == "__main__":
    main()
