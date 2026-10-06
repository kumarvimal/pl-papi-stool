import shlex

import invoke


@invoke.task
def peek_dlq(
    ctx: invoke.Context,
    queue_name: str = "prod-return-tracking-events-dlq",
    limit: int = 10,
    region: str = "eu-central-1",
    profile: str = "default",
) -> None:
    """Sample DLQ messages without deleting or hiding them; receive counts increase."""
    if not queue_name.endswith("-dlq"):
        raise invoke.Exit("Queue name must end with -dlq.")
    if not 1 <= limit <= 10:
        raise invoke.Exit("Limit must be between 1 and 10.")
    options = f"--region {shlex.quote(region)} --profile {shlex.quote(profile)}"
    queue_url = ctx.run(
        f"aws sqs get-queue-url --queue-name {shlex.quote(queue_name)} "
        f"{options} --query QueueUrl --output text --no-cli-pager",
        hide=True,
    ).stdout.strip()
    ctx.run(
        f"aws sqs receive-message --queue-url {shlex.quote(queue_url)} "
        f"--max-number-of-messages {limit} --visibility-timeout 0 "
        "--wait-time-seconds 1 --message-system-attribute-names All "
        f"--message-attribute-names All {options} --output json --no-cli-pager",
    )
