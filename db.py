import invoke

@invoke.task
def fix_postgres(ctx):
    ctx.run("brew services stop postgresql@14", pty=True)
    ctx.run("rm /opt/homebrew/var/postgresql@14/postmaster.pid", pty=True)
    ctx.run("brew services start postgresql@14", pty=True)

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
