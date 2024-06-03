from argparse import ArgumentParser
from cuid2.generator import cuid_wrapper, MAXIMUM_LENGTH

def main() -> None:
    """Print out a CUID generated string. Used by the CLI console script."""

    # parse cli arguments
    arguments_parser = ArgumentParser()
    arguments_parser.add_argument(
        nargs="?",
        dest="length",
        help="Length of generated cuid2",
        type=int,
        default=24)
    arguments_parser.add_argument(
        "-p", "--pretty", 
        help="Pretty print generated cuid2 in blocks",
        action="store_true",
        default=False)
    arguments_parser.add_argument(
        "-pl", "--pretty_length",
        metavar="BLOCK-LENGTH",
        help="Set the custom length of pretty blocks",
        type=int,
        default=-5)
    arguments_parser.add_argument(
        "--alphabet",
        metavar="ABCDE..",
        help="Set the custom alphabet to generate cuid2",
        type=str,
        default=None)
    cli_arguments = arguments_parser.parse_args()

    # generate cuid of arbitrary length
    cuid2: str = ""
    while len(cuid2) < cli_arguments.length:
        cuid2 += cuid_wrapper(min(MAXIMUM_LENGTH, cli_arguments.length - len(cuid2)), alphabet=cli_arguments.alphabet)()

    # print
    if cli_arguments.pretty or cli_arguments.pretty_length > 0:
        cuid2_list: list[str] = [cuid2[i:i + abs(cli_arguments.pretty_length)] for i in
                 range(0, len(cuid2), abs(cli_arguments.pretty_length))]
        print("-".join(cuid2_list))
    else:
        print(cuid2) # noqa: T201 (print statement)
