from unittest.mock import Mock

import invoke
import pytest

from _stool.sqs import peek_dlq


def test_peek_preserves_messages_and_quotes_queue_url() -> None:
    context = Mock(spec=invoke.Context)
    context.run.return_value.stdout = "https://sqs.example/queue-dlq\n"

    peek_dlq(context, limit=7)

    assert context.run.call_count == 2
    context.run.assert_any_call(
        "aws sqs get-queue-url --queue-name prod-return-tracking-events-dlq "
        "--region eu-central-1 --profile default --query QueueUrl "
        "--output text --no-cli-pager",
        hide=True,
    )
    context.run.assert_called_with(
        "aws sqs receive-message --queue-url https://sqs.example/queue-dlq "
        "--max-number-of-messages 7 --visibility-timeout 0 "
        "--wait-time-seconds 1 --message-system-attribute-names All "
        "--message-attribute-names All --region eu-central-1 --profile default "
        "--output json --no-cli-pager",
    )


@pytest.mark.parametrize(
    ("queue_name", "limit"),
    [("prod-return-tracking-events", 10), ("events-dlq", 0), ("events-dlq", 11)],
)
def test_invalid_input_does_not_call_aws(queue_name: str, limit: int) -> None:
    context = Mock(spec=invoke.Context)

    with pytest.raises(invoke.Exit):
        peek_dlq(context, queue_name, limit=limit)

    context.run.assert_not_called()
