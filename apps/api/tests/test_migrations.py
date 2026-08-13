import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from group_interview_arena_api.db.base import Base

API_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_CONFIG_PATH = API_ROOT / "alembic.ini"
BASELINE_REVISION = "7c6ccd86b3c5"


def _alembic_config() -> Config:
    return Config(ALEMBIC_CONFIG_PATH)


def test_alembic_config_uses_project_migration_directory_without_url() -> None:
    config = _alembic_config()

    script_location = config.get_main_option("script_location")

    assert script_location is not None
    assert Path(script_location).resolve() == (API_ROOT / "migrations").resolve()
    assert config.get_main_option("sqlalchemy.url") is None


def test_migration_history_has_single_baseline_head() -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    revision = script.get_revision(BASELINE_REVISION)

    assert script.get_heads() == [BASELINE_REVISION]
    assert revision.revision == BASELINE_REVISION
    assert revision.down_revision is None
    assert revision.branch_labels == set()
    assert revision.dependencies is None


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


def test_migration_target_metadata_has_no_business_tables() -> None:
    assert len(Base.metadata.tables) == 0
