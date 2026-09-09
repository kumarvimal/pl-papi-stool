import re
import subprocess
from pathlib import Path

import invoke

MANAGED_BLOCK_START = "# >>> stool npm GitHub token >>>"
MANAGED_BLOCK_END = "# <<< stool npm GitHub token <<<"
MANAGED_BLOCK = f"""{MANAGED_BLOCK_START}
if command -v gh >/dev/null 2>&1; then
    export NPM_GITHUB_TOKEN="$(gh auth token --hostname github.com 2>/dev/null)"
fi
{MANAGED_BLOCK_END}"""


def _verify_github_token() -> None:
    result = subprocess.run(
        ["gh", "auth", "token", "--hostname", "github.com"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise SystemExit(
            "GitHub CLI is not authenticated. Run `gh auth login --hostname "
            "github.com --web --scopes repo,read:org,read:packages` first."
        )


def _update_zprofile(content: str) -> str:
    managed_block_pattern = re.compile(
        rf"\n?{re.escape(MANAGED_BLOCK_START)}.*?"
        rf"{re.escape(MANAGED_BLOCK_END)}\n?",
        flags=re.DOTALL,
    )
    content = managed_block_pattern.sub("\n", content)
    content = re.sub(
        r"(?m)^\s*export\s+NPM_GITHUB_TOKEN=.*(?:\n|$)",
        "",
        content,
    )
    return f"{content.rstrip()}\n\n{MANAGED_BLOCK}\n"


@invoke.task(name="setup-token")
def setup_token(ctx) -> None:
    """Load the GitHub Packages npm token from gh in login shells."""
    zprofile = Path.home() / ".zprofile"
    content = zprofile.read_text() if zprofile.exists() else ""
    zprofile.write_text(_update_zprofile(content))
    _verify_github_token()
    print(
        "Configured NPM_GITHUB_TOKEN in ~/.zprofile. "
        "Run `source ~/.zprofile` to update this shell."
    )
