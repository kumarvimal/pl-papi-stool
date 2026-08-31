from unittest.mock import Mock

from _stool.parcellab import (
    _load_payload,
    seed_inline_exchange,
    start_dynamodb,
)
from track.types import LineItem, LineItemOrder


def test_inline_exchange_seed_payloads_are_consistent() -> None:
    order = _load_payload("order.json")
    tracking = _load_payload("tracking.json")
    feed = _load_payload("product_feed.json")

    order_item = LineItemOrder.model_validate(order["articles_order"][0])
    tracking_item = LineItem.model_validate(tracking["articles"][0])

    assert tracking_item.order_item_id == order_item.line_item_id
    assert feed["sku"] == order_item.sku
    assert order_item.variant_id in {variant["id"] for variant in feed["variants"]}


def test_seed_task_runs_as_module_to_avoid_stdlib_module_shadowing() -> None:
    context = Mock()

    seed_inline_exchange.body(context, 2, "dev")  # type: ignore[attr-defined]

    context.run.assert_called_once_with(
        "uv run python -m _stool.parcellab --account-id 2 --portal-code dev",
        pty=True,
        echo=True,
    )


def test_start_dynamodb_uses_configured_installation(tmp_path) -> None:
    (tmp_path / "DynamoDBLocal.jar").touch()
    (tmp_path / "DynamoDBLocal_lib").mkdir()
    context = Mock()

    start_dynamodb.body(  # type: ignore[attr-defined]
        context, str(tmp_path), 8001
    )

    context.run.assert_called_once_with(
        f"java -Djava.library.path={tmp_path}/DynamoDBLocal_lib "
        f"-jar {tmp_path}/DynamoDBLocal.jar -sharedDb -port 8001",
        pty=True,
        echo=True,
    )
