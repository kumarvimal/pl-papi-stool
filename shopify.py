import sys

import invoke


APP_DIR = "integrations/shopify/apps"

@invoke.task
def ngrok(ctx):
    ctx.run("ngrok http 8000 --url annabelle-clothbound-maribeth.ngrok-free.dev", pty=True)


@invoke.task
def build(ctx):
    with ctx.cd(APP_DIR):
        ctx.run("npm run build", echo=True)

@invoke.task
def link(ctx):
    with ctx.cd(APP_DIR):
        ctx.run('shopify app config link --organization "Kumar\'s Dev store (Dev Dashboard)"', echo=True)

@invoke.task
def ci(ctx):
    with ctx.cd(APP_DIR):
        ctx.run("npm ci", pty=True)

@invoke.task
def dev(ctx, config="kumar"):
    with ctx.cd(APP_DIR):
        ctx.run('npm run dev -- --config kumar', pty=True, echo=True)

@invoke.task
def test(ctx):
    with ctx.cd(APP_DIR):
        ctx.run('npm run test', pty=True, echo=True)


@invoke.task
def validate(ctx):
    with ctx.cd(APP_DIR):
        ctx.run('shopify app config validate --json', pty=True, echo=True)
