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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .git import get_git_commit, get_git_root


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Option:
    dest: str
    flag: str
    env: str
    help: str
    # A plain value or a zero-arg callable. Callables are only invoked when no
    # CLI/env/ini value was supplied, so e.g. the git subprocess behind
    # `flakiness_commit_id` is skipped whenever the value is provided.
    default: Any = None
    ini: bool = True
    is_flag: bool = False


_OPTIONS: List[Option] = [
    Option(
        dest="flakiness_output_dir",
        flag="--flakiness-output-dir",
        env="FLAKINESS_OUTPUT_DIR",
        default="flakiness-report",
        help="Directory to dump the raw JSON report instead of uploading to Flakiness.io. Defaults to the 'flakiness-report'.",
    ),
    Option(
        dest="flakiness_commit_id",
        flag="--flakiness-commit-id",
        env="FLAKINESS_COMMIT_ID",
        default=get_git_commit,
        help="Commit ID of the repository under test. Defaults to current git commit.",
    ),
    Option(
        dest="flakiness_name",
        flag="--flakiness-name",
        env="FLAKINESS_NAME",
        default="pytest",
        help="Name for the Flakiness Report environment. Defaults to 'pytest'.",
    ),
    Option(
        dest="flakiness_git_root",
        flag="--flakiness-git-root",
        env="FLAKINESS_GIT_ROOT",
        default=get_git_root,
        help="The root directory to normalize all paths. Defaults to git repository root.",
    ),
    Option(
        dest="flakiness_title",
        flag="--flakiness-title",
        env="FLAKINESS_TITLE",
        help="Optional human-readable report title. Typically used to name a CI run, matrix shard, or other execution group.",
    ),
    Option(
        dest="flakiness_project",
        flag="--flakiness-project",
        env="FLAKINESS_PROJECT",
        help="Flakiness.io project identifier (e.g. 'org/project'). Required for GitHub OIDC authentication.",
    ),
    Option(
        dest="flakiness_access_token",
        flag="--flakiness-access-token",
        env="FLAKINESS_ACCESS_TOKEN",
        ini=False,
        help="The Flakiness Access Token to upload report.",
    ),
    Option(
        dest="flakiness_endpoint",
        flag="--flakiness-endpoint",
        env="FLAKINESS_ENDPOINT",
        default="https://flakiness.io",
        help="Flakiness.io service endpoint. Defaults to https://flakiness.io",
    ),
    Option(
        dest="flakiness_disable_upload",
        flag="--flakiness-disable-upload",
        env="FLAKINESS_DISABLE_UPLOAD",
        is_flag=True,
        default=False,
        help="Disable uploading the report to Flakiness.io. The JSON report is still written to the output directory.",
    ),
]

_BY_DEST: Dict[str, Option] = {opt.dest: opt for opt in _OPTIONS}


def _sources(opt: Option) -> str:
    if opt.ini:
        return f" Can also be set via the {opt.env} env variable or the `{opt.dest}` ini option."
    return f" Can also be set via the {opt.env} env variable."


def add_options(parser) -> None:
    """Register every flakiness option as both a CLI flag and (where allowed) an
    ini option. CLI defaults are intentionally left as `None`/`False` so that
    `resolve()` can tell an explicit flag apart from an unset one."""
    group = parser.getgroup("flakiness")
    for opt in _OPTIONS:
        group.addoption(
            opt.flag,
            action="store_true" if opt.is_flag else "store",
            dest=opt.dest,
            default=None,
            help=opt.help + _sources(opt),
        )
        if opt.ini:
            parser.addini(
                opt.dest,
                help=opt.help,
                type="bool" if opt.is_flag else "string",
                default=False if opt.is_flag else None,
            )


def resolve(config, dest: str) -> Any:
    """Resolve a single option's value with precedence CLI > env > ini > default."""
    opt = _BY_DEST[dest]

    # 1. Explicit CLI flag. For store_true flags an unset value is None, so a
    #    truthy value means the flag was actually passed.
    cli_value = config.getoption(dest)
    if opt.is_flag:
        if cli_value:
            return True
    elif cli_value is not None:
        return cli_value

    # 2. Environment variable.
    env_value = os.environ.get(opt.env)
    if env_value is not None:
        return _is_truthy(env_value) if opt.is_flag else env_value

    # 3. ini file. Unset ini values are falsy ('' or False), so `if` skips them.
    if opt.ini:
        ini_value = config.getini(dest)
        if ini_value:
            return True if opt.is_flag else ini_value

    # 4. Built-in default (possibly computed lazily).
    return opt.default() if callable(opt.default) else opt.default


@dataclass(frozen=True)
class FlakinessConfig:
    """An immutable snapshot of every resolved flakiness option.

    Resolving all options up front (before any test runs) keeps configuration
    stable for the whole session. In particular it freezes the environment
    variables: tests that mutate `FLAKINESS_*` via `monkeypatch.setenv` (or
    otherwise) cannot retroactively change where/whether the report is uploaded
    when `pytest_sessionfinish` runs.
    """

    output_dir: Optional[str]
    commit_id: Optional[str]
    name: str
    git_root: Optional[str]
    title: Optional[str]
    project: Optional[str]
    access_token: Optional[str]
    endpoint: str
    disable_upload: bool


def resolve_config(config) -> FlakinessConfig:
    """Resolve every flakiness option once, capturing a session-stable snapshot."""
    return FlakinessConfig(
        output_dir=resolve(config, "flakiness_output_dir"),
        commit_id=resolve(config, "flakiness_commit_id"),
        name=resolve(config, "flakiness_name"),
        git_root=resolve(config, "flakiness_git_root"),
        title=resolve(config, "flakiness_title"),
        project=resolve(config, "flakiness_project"),
        access_token=resolve(config, "flakiness_access_token"),
        endpoint=resolve(config, "flakiness_endpoint"),
        disable_upload=resolve(config, "flakiness_disable_upload"),
    )
