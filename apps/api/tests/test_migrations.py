import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from group_interview_arena_api.db.base import Base

API_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_CONFIG_PATH = API_ROOT / "alembic.ini"
BASELINE_REVISION = "7c6ccd86b3c5"
IDENTITY_REVISION = "4fe43b42641b"


def _alembic_config() -> Config:
    return Config(ALEMBIC_CONFIG_PATH)


def test_alembic_config_uses_project_migration_directory_without_url() -> None:
    config = _alembic_config()

    script_location = config.get_main_option("script_location")

    assert script_location is not None
    assert Path(script_location).resolve() == (API_ROOT / "migrations").resolve()
    assert config.get_main_option("sqlalchemy.url") is None


def test_migration_history_is_linear_with_single_identity_head() -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    baseline = script.get_revision(BASELINE_REVISION)
    identity = script.get_revision(IDENTITY_REVISION)

    assert script.get_heads() == [IDENTITY_REVISION]
    assert [revision.revision for revision in script.walk_revisions()] == [
        IDENTITY_REVISION,
        BASELINE_REVISION,
    ]
    assert baseline.revision == BASELINE_REVISION
    assert baseline.down_revision is None
    assert baseline.branch_labels == set()
    assert baseline.dependencies is None
    assert identity.revision == IDENTITY_REVISION
    assert identity.down_revision == BASELINE_REVISION
    assert identity.branch_labels == set()
    assert identity.dependencies is None


def test_baseline_upgrade_and_downgrade_are_zero_op() -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    revision = script.get_revision(BASELINE_REVISION)
    module = ast.parse(Path(revision.path).read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name in {"upgrade", "downgrade"}
    }

    assert set(functions) == {"upgrade", "downgrade"}
    for function in functions.values():
        assert len(function.body) == 2
        assert isinstance(function.body[0], ast.Expr)
        assert isinstance(function.body[0].value, ast.Constant)
        assert isinstance(function.body[0].value.value, str)
        assert isinstance(function.body[1], ast.Pass)


def test_migration_target_metadata_has_exact_identity_tables() -> None:
    assert set(Base.metadata.tables) == {"auth_sessions", "users"}
