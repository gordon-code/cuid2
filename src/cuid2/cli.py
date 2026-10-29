"""Command-line interface for generating and validating CUID2 identifiers."""

from __future__ import annotations

import sys
from argparse import Action, ArgumentParser, ArgumentTypeError, RawDescriptionHelpFormatter
from functools import partial
from typing import TYPE_CHECKING

from cuid2.generator import Cuid, is_cuid
from cuid2.utils import BIG_LENGTH, DEFAULT_LENGTH, MAXIMUM_LENGTH, MIN_LENGTH, create_fingerprint

__all__ = ["main"]

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Sequence

_SLUG_LENGTH: int = 5


def _write_output(text: str) -> None:
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except BrokenPipeError:
        return


class _VersionAction(Action):
    def __call__(
        self: _VersionAction,
        parser: ArgumentParser,
        namespace: Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        """Print package version to stdout and exit."""
        del namespace, values, option_string
        from importlib.metadata import version  # noqa: PLC0415

        _write_output(f"{parser.prog} {version('cuid2')}\n")
        parser.exit(0)


def _parse_length(raw: str) -> int:
    try:
        value = int(raw, 10)
    except ValueError as err:
        msg = f"invalid int value: {raw!r}"
        raise ArgumentTypeError(msg) from err
    if value < 1:
        msg = "length must be at least 1 character"
        raise ArgumentTypeError(msg)
    if value > MAXIMUM_LENGTH:
        msg = f"length must never exceed {MAXIMUM_LENGTH} characters"
        raise ArgumentTypeError(msg)
    return value


def _parse_count(raw: str) -> int:
    try:
        value = int(raw, 10)
    except ValueError as err:
        msg = f"invalid int value: {raw!r}"
        raise ArgumentTypeError(msg) from err
    if value < 1:
        msg = "count must be at least 1"
        raise ArgumentTypeError(msg)
    return value


def _parse_fingerprint(raw: str) -> str:
    if not raw:
        msg = "fingerprint must not be empty"
        raise ArgumentTypeError(msg)
    return raw


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="cuid2",
        description=(
            f"Generate or validate collision-resistant CUID2 identifiers "
            f"(default length: {DEFAULT_LENGTH}, spec range: {MIN_LENGTH}..{BIG_LENGTH})."
        ),
        epilog=(
            "examples:\n"
            "  cuid2\n"
            "  cuid2 -l 10\n"
            "  cuid2 --slug\n"
            "  cuid2 -n 5\n"
            "  cuid2 -f server-1\n"
            "  cuid2 --check <id>\n"
            "  cuid2 -n 5 | cuid2 --check -"
        ),
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "length",
        nargs="?",
        type=_parse_length,
        default=None,
        help=f"Length of CUID2 to generate or validate (default: {DEFAULT_LENGTH}, spec: {MIN_LENGTH}..{BIG_LENGTH}).",
    )
    parser.add_argument(
        "-V",
        "-v",
        "--version",
        action=_VersionAction,
        nargs=0,
        default="==SUPPRESS==",
        help="Show program's version number and exit.",
    )
    parser.add_argument(
        "-l",
        "--length",
        dest="opt_length",
        metavar="LENGTH",
        type=_parse_length,
        default=None,
        help=f"Length of CUID2 to generate or validate (default: {DEFAULT_LENGTH}, spec: {MIN_LENGTH}..{BIG_LENGTH}).",
    )
    parser.add_argument(
        "--slug",
        action="store_true",
        help="Generate or validate a 5-character short CUID2 slug.",
    )
    parser.add_argument(
        "-n",
        "-c",
        "--count",
        dest="count",
        metavar="COUNT",
        type=_parse_count,
        default=None,
        help="Number of CUID2 identifiers to generate (default: 1).",
    )
    parser.add_argument(
        "-f",
        "--fingerprint",
        dest="fingerprint",
        metavar="FINGERPRINT",
        type=_parse_fingerprint,
        default=None,
        help="Custom host/process fingerprint seed string.",
    )
    parser.add_argument(
        "--check",
        "--validate",
        dest="check",
        metavar="ID",
        default=None,
        help="Validate a CUID2 identifier (or '-' to read newline-delimited IDs from stdin).",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress stdout output in --check/--validate mode.",
    )
    return parser


def _resolve_length(parser: ArgumentParser, cli_args: Namespace) -> int | None:
    sources = [
        val
        for val in (cli_args.length, cli_args.opt_length, _SLUG_LENGTH if cli_args.slug else None)
        if val is not None
    ]
    if len(sources) > 1:
        parser.error("conflicting length arguments: specify at most one of [length], -l/--length, or --slug")
    return sources[0] if sources else None


def _validate_mode_flags(parser: ArgumentParser, cli_args: Namespace) -> None:
    if cli_args.check is None and cli_args.quiet:
        parser.error("argument -q/--quiet: only allowed with --check/--validate")
    if cli_args.check is not None and (cli_args.count is not None or cli_args.fingerprint is not None):
        parser.error("arguments -n/-c/--count and -f/--fingerprint are not allowed with --check/--validate")


def _run_check(check_arg: str, target_length: int | None, *, quiet: bool) -> int:
    candidates = [line.rstrip("\r\n") for line in sys.stdin] if check_arg == "-" else [check_arg]
    if not candidates:
        candidates = [""]
    min_len = target_length if target_length is not None else MIN_LENGTH
    max_len = target_length if target_length is not None else MAXIMUM_LENGTH
    all_valid = True
    lines: list[str] = []
    for candidate in candidates:
        valid = is_cuid(candidate, min_length=min_len, max_length=max_len)
        all_valid = all_valid and valid
        lines.append(f"{candidate or '<empty>'}: {'valid' if valid else 'invalid'}\n")
    if not quiet:
        _write_output("".join(lines))
    return 0 if all_valid else 1


def main(args: Sequence[str] | None = None) -> None:
    """Execute the ``cuid2`` command-line interface.

    Parameters
    ----------
    args : Sequence[str] | None, optional
        Command-line argument tokens to parse, by default ``None`` (which reads
        ``sys.argv[1:]``).

    Raises
    ------
    SystemExit
        Raised with exit code ``0`` or ``1`` in ``--check``/``--validate`` or
        ``--version``/``--help`` modes, or exit code ``2`` on invalid arguments.
    """
    parser = _build_parser()
    cli_args = parser.parse_args(args)
    target_length = _resolve_length(parser, cli_args)
    _validate_mode_flags(parser, cli_args)

    if cli_args.check is not None:
        exit_code = _run_check(cli_args.check, target_length, quiet=cli_args.quiet)
        raise SystemExit(exit_code)

    resolved_length = target_length if target_length is not None else DEFAULT_LENGTH
    count = cli_args.count if cli_args.count is not None else 1
    cuid_generator = (
        Cuid(length=resolved_length)
        if cli_args.fingerprint is None
        else Cuid(
            length=resolved_length,
            fingerprint=partial(create_fingerprint, fingerprint_data=cli_args.fingerprint),
        )
    )
    output = "".join(f"{cuid_generator.generate()}\n" for _ in range(count))
    _write_output(output)
