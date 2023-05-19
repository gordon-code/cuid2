from cuid2.generator import cuid_wrapper

generate_cuid = cuid_wrapper()


def main() -> None:
    """Print out a CUID generated string. Used by the CLI console script."""
    print(generate_cuid())  # noqa: T201 (print statement)
