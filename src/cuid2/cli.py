"""Command-line interface for generating CUID2 identifiers."""

from __future__ import annotations

from argparse import ArgumentParser
from typing import TYPE_CHECKING

from cuid2.generator import create_id
from cuid2.utils import DEFAULT_LENGTH

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(args: Sequence[str] | None = None) -> None:
    """Print out a CUID generated string. Used by the CLI console script."""
    arguments_parser = ArgumentParser()
    arguments_parser.add_argument(
        nargs="?",
        dest="length",
        help="Length of generated cuid2",
        type=int,
        default=DEFAULT_LENGTH,
    )
    cli_arguments = arguments_parser.parse_args(args)

    print(create_id(cli_arguments.length))  # noqa: T201 (print statement)
