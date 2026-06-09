"""Central definition and resolution of every flakiness config option.

Each option can be supplied in up to four places. They are resolved with the
following precedence (highest first):

    1. explicit CLI flag   (e.g. --flakiness-project=...)
    2. environment variable (e.g. FLAKINESS_PROJECT)
    3. ini file            (pytest.ini / tox.ini / setup.cfg / pyproject.toml)
    4. built-in default    (static value or computed lazily)

`ini` controls whether the option can be set from an ini file. The access
token is intentionally excluded: ini files are usually committed to version
control and should never hold secrets.
"""

import os
from typing import Any, Callable, Dict, List, Optional, Union

from .git import get_git_commit, get_git_root


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


# Default may be a plain value or a zero-arg callable. Callables are only
# invoked when no CLI/env/ini value was supplied, so e.g. the git subprocess
# behind `flakiness_commit_id` is skipped whenever the value is provided.
Default = Union[None, str, bool, Callable[[], Optional[str]]]

_OPTIONS: List[Dict[str, Any]] = [
    {
        "dest": "flakiness_output_dir",
        "flag": "--flakiness-output-dir",
        "env": "FLAKINESS_OUTPUT_DIR",
        "ini": True,
        "default": "flakiness-report",
        "help": "Directory to dump the raw JSON report instead of uploading to Flakiness.io. Defaults to the 'flakiness-report'.",
    },
    {
        "dest": "flakiness_commit_id",
        "flag": "--flakiness-commit-id",
        "env": "FLAKINESS_COMMIT_ID",
        "ini": True,
        "default": get_git_commit,
        "help": "Commit ID of the repository under test. Defaults to current git commit.",
    },
    {
        "dest": "flakiness_name",
        "flag": "--flakiness-name",
        "env": "FLAKINESS_NAME",
        "ini": True,
        "default": "pytest",
        "help": "Name for the Flakiness Report environment. Defaults to 'pytest'.",
    },
    {
        "dest": "flakiness_git_root",
        "flag": "--flakiness-git-root",
        "env": "FLAKINESS_GIT_ROOT",
        "ini": True,
        "default": get_git_root,
        "help": "The root directory to normalize all paths. Defaults to git repository root.",
    },
    {
        "dest": "flakiness_title",
        "flag": "--flakiness-title",
        "env": "FLAKINESS_TITLE",
        "ini": True,
        "default": None,
        "help": "Optional human-readable report title. Typically used to name a CI run, matrix shard, or other execution group.",
    },
    {
        "dest": "flakiness_project",
        "flag": "--flakiness-project",
        "env": "FLAKINESS_PROJECT",
        "ini": True,
        "default": None,
        "help": "Flakiness.io project identifier (e.g. 'org/project'). Required for GitHub OIDC authentication.",
    },
    {
        "dest": "flakiness_access_token",
        "flag": "--flakiness-access-token",
        "env": "FLAKINESS_ACCESS_TOKEN",
        "ini": False,
        "default": None,
        "help": "The Flakiness Access Token to upload report.",
    },
    {
        "dest": "flakiness_endpoint",
        "flag": "--flakiness-endpoint",
        "env": "FLAKINESS_ENDPOINT",
        "ini": True,
        "default": "https://flakiness.io",
        "help": "Flakiness.io service endpoint. Defaults to https://flakiness.io",
    },
    {
        "dest": "flakiness_disable_upload",
        "flag": "--flakiness-disable-upload",
        "env": "FLAKINESS_DISABLE_UPLOAD",
        "ini": True,
        "is_flag": True,
        "default": False,
        "help": "Disable uploading the report to Flakiness.io. The JSON report is still written to the output directory.",
    },
]

_BY_DEST: Dict[str, Dict[str, Any]] = {opt["dest"]: opt for opt in _OPTIONS}


def _sources(opt: Dict[str, Any]) -> str:
    if opt.get("ini"):
        return f" Can also be set via the {opt['env']} env variable or the `{opt['dest']}` ini option."
    return f" Can also be set via the {opt['env']} env variable."


def add_options(parser) -> None:
    """Register every flakiness option as both a CLI flag and (where allowed) an
    ini option. CLI defaults are intentionally left as `None`/`False` so that
    `resolve()` can tell an explicit flag apart from an unset one."""
    group = parser.getgroup("flakiness")
    for opt in _OPTIONS:
        help_text = opt["help"] + _sources(opt)
        if opt.get("is_flag"):
            group.addoption(
                opt["flag"],
                action="store_true",
                dest=opt["dest"],
                default=None,
                help=help_text,
            )
        else:
            group.addoption(
                opt["flag"],
                action="store",
                dest=opt["dest"],
                default=None,
                help=help_text,
            )
        if opt.get("ini"):
            parser.addini(
                opt["dest"],
                help=help_text,
                type="bool" if opt.get("is_flag") else "string",
                default=False if opt.get("is_flag") else None,
            )


def resolve(config, dest: str) -> Any:
    """Resolve a single option's value with precedence CLI > env > ini > default."""
    opt = _BY_DEST[dest]
    is_flag = opt.get("is_flag", False)

    # 1. Explicit CLI flag. For store_true flags an unset value is None, so a
    #    truthy value means the flag was actually passed.
    cli_value = config.getoption(dest)
    if is_flag:
        if cli_value:
            return True
    elif cli_value is not None:
        return cli_value

    # 2. Environment variable.
    env_value = os.environ.get(opt["env"])
    if env_value is not None:
        return _is_truthy(env_value) if is_flag else env_value

    # 3. ini file. Unset ini values are falsy ('' or False), so `if` skips them.
    if opt.get("ini"):
        ini_value = config.getini(dest)
        if ini_value:
            return True if is_flag else ini_value

    # 4. Built-in default (possibly computed lazily).
    default = opt["default"]
    return default() if callable(default) else default
