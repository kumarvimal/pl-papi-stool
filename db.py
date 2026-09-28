import shlex

import invoke


@invoke.task
def readonly_prod(ctx, port: int = 15432, duration: str = "1h"):
    """Connect to the read-only production Product API database through Hoop."""
    ctx.run(
        "parcellab-infra --env prod proxy connect readonly-product-api-prod "
        f"--port {int(port)} --duration {shlex.quote(duration)}",
        pty=True,
        echo=True,
    )


@invoke.task
def fix_postgres(ctx: invoke.Context, version: int = 15) -> None:
    """Restart Homebrew PostgreSQL after clearing its stale PID file."""
    package = f"postgresql@{int(version)}"
    ctx.run(f"brew services stop {package}", pty=True, echo=True)
    ctx.run(f"rm -f /opt/homebrew/var/{package}/postmaster.pid", pty=True, echo=True)
    ctx.run(f"brew services start {package}", pty=True, echo=True)

@invoke.task
def setup_atlas(ctx):
    ctx.run("atlas deployments setup mongo-atlas-papi --type local --force --port 27017", pty=True, echo=True)

@invoke.task
def atlas_start(ctx):
    ctx.run("python manage.py seed --track", pty=True, echo=True)
    ctx.run("atlas deployments search indexes create default --type local --deploymentName mongo-atlas-papi -f ./track/data/indexes/trackings.json", pty=True)

@invoke.task
def atlas_delete(ctx):
    ctx.run("atlas deployments delete mongo-atlas-papi", pty=True, echo=True)


@invoke.task
def atlas_stop(ctx):
    ctx.run("atlas deployments stop mongo-atlas-papi", pty=True, echo=True)

@invoke.task
def mongo_restart(ctx):
    ctx.run("brew services stop mongodb-community", pty=True)
    ctx.run("brew services start mongodb-community", pty=True)
