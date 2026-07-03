import invoke


@invoke.task(aliases=["clear"])
def clear_used_port(ctx, port: int = 8000):
    """Kill the process listening on PORT."""
    port = int(port)
    ctx.run(
        f'pids=$(lsof -ti tcp:{port} -sTCP:LISTEN); '
        f'if [ -n "$pids" ]; then kill $pids; '
        f'else echo "No process listening on port {port}"; fi',
        pty=True,
        echo=True,
    )
