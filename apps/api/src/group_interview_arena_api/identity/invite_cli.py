import argparse
import asyncio
from collections.abc import Sequence

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.identity.invitations import (
    DEFAULT_INVITATION_LIFETIME_DAYS,
    generate_invitations,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Closed Beta invitation operator tool")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("--count", type=int, required=True)
    generate.add_argument(
        "--expires-in-days",
        type=int,
        default=DEFAULT_INVITATION_LIFETIME_DAYS,
    )
    generate.add_argument("--label", required=True)
    return parser


async def _generate(args: argparse.Namespace) -> int:
    settings = DatabaseSettings()  # pyright: ignore[reportCallIssue]
    engine = create_database_engine(settings)
    session_factory = create_database_session_factory(engine)
    try:
        async with session_factory() as session:
            generated = await generate_invitations(
                session,
                count=args.count,
                expires_in_days=args.expires_in_days,
                label=args.label,
            )
        for invitation in generated:
            print(invitation.raw_code)
    finally:
        await dispose_database_engine(engine)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "generate":
        return asyncio.run(_generate(args))
    raise AssertionError("Unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
