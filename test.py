import invoke


@invoke.task
def returns(ctx, maxfail: int|None=None, create_db=False):
    """Run returns tests"""
    maxfail_cmd = ""
    if maxfail:
        maxfail = int(maxfail)
        maxfail_cmd = f"--maxfail {maxfail}"
    ctx.run(f'pytest {"--create-db" if create_db else ""}  {maxfail_cmd} -m "not e2e" tests/returns --cov-report=html tests/returns', pty=True, echo=True)

@invoke.task
def e2e(ctx):
    """Run e2e tests"""
    ctx.run('pytest tests/returns --maxfail 10 -m "e2e" --browser chromium --no-migrations ', pty=True, echo=True)

@invoke.task
def test(ctx):
    """Run test without returns and e2e"""
    ctx.run('pytest --maxfail 10 --no-migrations --cov=. -m "not worker and not e2e and not openai" --ignore=tests/returns -n 8', pty=True, echo=True)

@invoke.task
def complete(ctx):
    """Run all tests"""
    test(ctx)
    returns(ctx)
    e2e(ctx)


@invoke.task
def delete_all_db(ctx):
    """Delete all test databases."""
    ctx.run("""
   psql -tc "SELECT datname FROM pg_database WHERE datname LIKE 'test_%';" |xargs -I {} psql -c "DROP DATABASE IF EXISTS \"{}\";"
    """)
