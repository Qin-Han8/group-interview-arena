import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from group_interview_arena_api.db.base import Base

API_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_CONFIG_PATH = API_ROOT / "alembic.ini"
BASELINE_REVISION = "7c6ccd86b3c5"
IDENTITY_REVISION = "4fe43b42641b"
SESSION_FOUNDATION_REVISION = "f1a11d15c001"
QUESTION_PERSONA_FOUNDATION_REVISION = "f1a12b15c002"
SESSION_PHASE_TIMING_REVISION = "f1a13b15c003"


def _alembic_config() -> Config:
    return Config(ALEMBIC_CONFIG_PATH)


def test_alembic_config_uses_project_migration_directory_without_url() -> None:
    config = _alembic_config()

    script_location = config.get_main_option("script_location")

    assert script_location is not None
    assert Path(script_location).resolve() == (API_ROOT / "migrations").resolve()
    assert config.get_main_option("sqlalchemy.url") is None


def test_migration_history_is_linear_with_single_session_phase_timing_head() -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    baseline = script.get_revision(BASELINE_REVISION)
    identity = script.get_revision(IDENTITY_REVISION)
    session_foundation = script.get_revision(SESSION_FOUNDATION_REVISION)
    question_persona = script.get_revision(QUESTION_PERSONA_FOUNDATION_REVISION)
    session_phase_timing = script.get_revision(SESSION_PHASE_TIMING_REVISION)

    assert script.get_heads() == [SESSION_PHASE_TIMING_REVISION]
    assert [revision.revision for revision in script.walk_revisions()] == [
        SESSION_PHASE_TIMING_REVISION,
        QUESTION_PERSONA_FOUNDATION_REVISION,
        SESSION_FOUNDATION_REVISION,
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
    assert session_foundation.revision == SESSION_FOUNDATION_REVISION
    assert session_foundation.down_revision == IDENTITY_REVISION
    assert session_foundation.branch_labels == set()
    assert session_foundation.dependencies is None
    assert question_persona.revision == QUESTION_PERSONA_FOUNDATION_REVISION
    assert question_persona.down_revision == SESSION_FOUNDATION_REVISION
    assert question_persona.branch_labels == set()
    assert question_persona.dependencies is None
    assert session_phase_timing.revision == SESSION_PHASE_TIMING_REVISION
    assert session_phase_timing.down_revision == QUESTION_PERSONA_FOUNDATION_REVISION
    assert session_phase_timing.branch_labels == set()
    assert session_phase_timing.dependencies is None


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


def test_migration_target_metadata_has_exact_product_tables() -> None:
    assert set(Base.metadata.tables) == {
        "auth_sessions",
        "discussion_events",
        "persona_private_stances",
        "persona_templates",
        "question_persona_assignments",
        "question_templates",
        "question_versions",
        "session_actions",
        "simulation_sessions",
        "users",
    }
