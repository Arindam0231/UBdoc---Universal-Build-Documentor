from services.ast_parser import get_chunks_from_file
from services.git_util import get_python_files, cloned_repo
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
chunks = {}
# Public repo — no token needed
with cloned_repo("https://github.com/unslothai/unsloth") as repo_path:
    files = get_python_files(repo_path)
    for f in files:

        chunks[str(f)] = {
            "code": Path(f).read_text(),
            "chunks": get_chunks_from_file(f),
        }


