from argparse import ArgumentParser
from cuid2.generator import cuid_wrapper

def main() -> None:
    """Print out a CUID generated string. Used by the CLI console script."""
    arguments_parser = ArgumentParser()
    
    arguments_parser.add_argument(nargs="?", dest="length", help="Length of generated cuid2", type=int, default=None)
    cli_arguments = arguments_parser.parse_args()

    print(cuid_wrapper(cli_arguments.length)())  # noqa: T201 (print statement)
