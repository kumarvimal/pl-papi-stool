# Stool commands

`_stool` contains project-specific commands discovered automatically by
[`st`](https://pypi.org/project/stool/). Run commands from the `product-api`
repository root with `st`; do not execute command files directly.

## Discover commands

```bash
st -l
st --help product-feed.query
```

Command modules live directly in `_stool/`. Each module becomes a namespace,
and functions decorated with `@invoke.task` become commands.

## Query the product feed

Signature:

```text
st product-feed.query ACCOUNT_CLIENT [--sku SKU] [--limit LIMIT]
  [--table-name TABLE] [--region REGION] [--profile PROFILE]
```

`ACCOUNT_CLIENT` must use the `<account>_<client>` DynamoDB partition-key
format, for example `1624810_0001`.

List the first 20 rows in a partition:

```bash
st product-feed.query 1624810_0001
```

Fetch one exact SKU:

```bash
st product-feed.query 1624810_0001 --sku 686875
```

Request a smaller bounded page:

```bash
st product-feed.query 1624810_0001 --limit 5
```

Defaults are table `product_feed`, region `eu-central-1`, AWS profile
`default`, and a 20-row limit. The JSON response includes
`last_evaluated_key` when more rows are available. If AWS SSO has expired,
authenticate first:

```bash
aws sso login --profile default
```

The command is read-only. It uses DynamoDB `Query` for a partition and
`GetItem` when `--sku` is supplied.

## Peek at dead-letter queue messages

```bash
st sqs.peek-dlq
st sqs.peek-dlq --limit 5
st sqs.peek-dlq --queue-name staging-return-tracking-events-dlq
```

Defaults to `prod-return-tracking-events-dlq`; override with `--queue-name`
(must end in `-dlq`). Other defaults are region `eu-central-1`, profile
`default`, and limit 10; override with `--region`, `--profile`, or `--limit`
(1–10). The queue URL is resolved from AWS on each invocation.

The command prints one SQS receive response as JSON, including message bodies
and attributes. It never deletes messages and uses visibility timeout zero,
so messages remain available. SQS has no true peek: receiving increments the
receive count and updates receive metadata. A response can contain fewer
messages than requested, and repeated calls may return the same messages.

## Configure GitHub Packages npm authentication

Configure login shells to retrieve `NPM_GITHUB_TOKEN` dynamically from the
authenticated GitHub CLI session:

```bash
st npm.setup-token
source ~/.zprofile
```

The command verifies the GitHub CLI login and replaces any literal npm token in
`~/.zprofile`; it does not persist the token itself.

## Tests

Tests belong in `_stool/tests/`, separate from command modules. Run the stool
suite with:

```bash
uv run pytest -o addopts='' _stool/tests -q
```

Run a single command's tests while developing:

```bash
uv run pytest -o addopts='' _stool/tests/test_product_feed.py -q
```

After changing commands, verify discovery and project checks:

```bash
st -l
make lint
```

Keep test code and fixtures out of command modules. Reusable fixture data can
live under `_stool/data/`; longer operational documentation belongs in
`_stool/docs/`.
