import git
import os
import shutil
import logging
import tempfile
import hashlib
from pathlib import Path
from contextlib import contextmanager
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


def _sanitize_url_for_logging(url: str) -> str:
    """Strip any embedded tokens from URL before logging."""
    parsed = urlparse(url)
    safe = parsed._replace(netloc=parsed.hostname)  # drop user:token@ part
    return urlunparse(safe)


def _inject_token(url: str, token: str) -> str:
    """Embed PAT into HTTPS URL."""
    parsed = urlparse(url)
    authed = parsed._replace(netloc=f"{token}@{parsed.hostname}")
    return urlunparse(authed)


def _validate_github_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme in ("https", "http")
        and "github.com" in parsed.netloc
        and len(parsed.path.strip("/").split("/")) == 2  # owner/repo
    )


def _get_clone_dir(base_dir: str, repo_url: str) -> str:
    """
    Deterministic clone path based on URL hash.
    Avoids collisions if cloning multiple repos to same base dir.
    """
    url_hash = hashlib.md5(repo_url.encode()).hexdigest()[:8]
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    return os.path.join(base_dir, f"{repo_name}_{url_hash}")


@contextmanager
def cloned_repo(
    repo_url: str,
    github_token: str | None = None,
    base_dir: str | None = None,
    depth: int = 1,
    branch: str | None = None,
    cleanup: bool = True,
):
    """
    Context manager that clones a repo, yields the local path,
    then cleans up automatically.

    Usage:
        with cloned_repo("https://github.com/owner/repo") as repo_path:
            files = list(repo_path.rglob("*.py"))
    """
    if not _validate_github_url(repo_url):
        raise ValueError(f"Invalid or unsupported GitHub URL: {repo_url}")

    # Use a system temp dir if no base_dir specified
    base = base_dir or tempfile.gettempdir()
    local_dir = _get_clone_dir(base, repo_url)

    # Inject auth token for private repos
    clone_url = _inject_token(repo_url, github_token) if github_token else repo_url
    safe_url = _sanitize_url_for_logging(repo_url)

    # If already cloned (e.g. retry scenario), wipe it first
    if os.path.exists(local_dir):
        logger.warning(f"Clone dir already exists, removing: {local_dir}")
        shutil.rmtree(local_dir)

    logger.info(f"Cloning {safe_url} → {local_dir}")

    try:
        clone_kwargs = {"depth": depth}
        if branch:
            clone_kwargs["branch"] = branch

        repo = git.Repo.clone_from(clone_url, local_dir, **clone_kwargs)

        logger.info(
            f"Cloned successfully | "
            f"branch={repo.active_branch.name} | "
            f"commit={repo.head.commit.hexsha[:7]}"
        )
        # yield repo
        yield Path(local_dir)

    except git.exc.GitCommandError as e:
        # Don't log the error message directly — may contain the token
        logger.error(f"Git clone failed for {safe_url}. Git exit code: {e.status}")
        raise RuntimeError(f"Failed to clone {safe_url}") from e

    finally:
        if cleanup and os.path.exists(local_dir):
            shutil.rmtree(local_dir)
            logger.info(f"Cleaned up clone dir: {local_dir}")


def get_python_files(repo_path: Path) -> list[Path]:
    """
    Walk the repo and return all .py files,
    excluding virtual envs, caches, and test dirs.
    """
    EXCLUDE_DIRS = {
        ".venv",
        "venv",
        "env",
        ".env",
        "__pycache__",
        ".git",
        "node_modules",
        "dist",
        "build",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
    }

    return [
        f
        for f in repo_path.rglob("*.py")
        if not any(part in EXCLUDE_DIRS for part in f.parts)
    ]


# if __name__ == "__main__":
#     import logging

#     logging.basicConfig(level=logging.INFO)

#     # Public repo — no token needed
#     with cloned_repo("https://github.com/unslothai/unsloth") as repo_path:
#         files = get_python_files(repo_path)
#         print(f"Found {len(files)} Python files")

#     # # Private repo — pass token
#     # with cloned_repo(
#     #     "https://github.com/yourorg/private-repo",
#     #     github_token=os.environ["GITHUB_TOKEN"],  # never hardcode
#     #     branch="develop",
#     # ) as repo_path:
#     #     files = get_python_files(repo_path)
