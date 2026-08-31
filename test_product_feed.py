import json
from unittest.mock import Mock

import invoke
import pytest

from _stool.product_feed import _run_query, query


def test_query_runs_product_feed_module() -> None:
    context = Mock()

    query.body(context, "1624810_0001", sku="686875", limit=5)

    context.run.assert_called_once_with(
        "uv run python -m _stool.product_feed 1624810_0001 --limit 5 "
        "--table-name product_feed --region eu-central-1 --profile default "
        "--sku 686875",
        pty=True,
        echo=True,
    )


def test_run_query_lists_a_bounded_account_client_partition(mocker, capsys) -> None:
    dynamodb = Mock()
    dynamodb.query.return_value = {
        "Items": [{"sku": {"S": "686875"}}],
        "LastEvaluatedKey": {
            "user_id_client_key": {"S": "1624810_0001"},
            "sku": {"S": "686875"},
        },
    }
    session = mocker.patch("boto3.Session")
    session.return_value.client.return_value = dynamodb

    _run_query(
        account_client="1624810_0001",
        sku=None,
        limit=5,
        table_name="product_feed",
        region="eu-central-1",
        profile="default",
    )

    dynamodb.query.assert_called_once_with(
        TableName="product_feed",
        KeyConditionExpression="user_id_client_key = :account_client",
        ExpressionAttributeValues={
            ":account_client": {"S": "1624810_0001"},
        },
        Limit=5,
    )
    output = json.loads(capsys.readouterr().out)
    assert output["items"] == [{"sku": "686875"}]
    assert output["last_evaluated_key"] == {
        "user_id_client_key": "1624810_0001",
        "sku": "686875",
    }


def test_run_query_fetches_one_exact_sku(mocker, capsys) -> None:
    dynamodb = Mock()
    dynamodb.get_item.return_value = {
        "Item": {
            "user_id_client_key": {"S": "1624810_0001"},
            "sku": {"S": "686875"},
            "imageUrl": {"S": "https://example.com/image.jpeg"},
        }
    }
    session = mocker.patch("boto3.Session")
    session.return_value.client.return_value = dynamodb

    _run_query(
        account_client="1624810_0001",
        sku="686875",
        limit=20,
        table_name="product_feed",
        region="eu-central-1",
        profile="default",
    )

    dynamodb.get_item.assert_called_once_with(
        TableName="product_feed",
        Key={
            "user_id_client_key": {"S": "1624810_0001"},
            "sku": {"S": "686875"},
        },
    )
    output = json.loads(capsys.readouterr().out)
    assert output["items"] == [
        {
            "user_id_client_key": "1624810_0001",
            "sku": "686875",
            "imageUrl": "https://example.com/image.jpeg",
        }
    ]
    assert output["last_evaluated_key"] is None


@pytest.mark.parametrize("account_client", ["1624810", "client_0001", "_0001"])
def test_query_rejects_invalid_account_client(account_client) -> None:
    with pytest.raises(invoke.Exit, match="<account>_<client>"):
        query.body(Mock(), account_client)
