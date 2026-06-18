import invoke

@invoke.task
def clima_start(ctx):
    ctx.run("colima start --runtime docker --cpu 4 --memory 8 --disk 60", pty=True)
