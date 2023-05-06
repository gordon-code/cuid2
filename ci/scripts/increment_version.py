import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
EXISTING_VERSION_DEF_LOCATION = os.path.join(REPO_ROOT, 'src/cuid2/__init__.py')


def main() -> None:
    read_file = ''

    with open(EXISTING_VERSION_DEF_LOCATION, 'r') as file:
        for line in file.readlines():
            if '__version__' in line:
                read_file = line

    version = read_file.split("= '")[1]
    parts = version.split('.')

    major = int(parts[0])
    minor = int(parts[1])
    patch = int(parts[2].split("'")[0])

    minor = minor + 1

    print(f'{major}.{minor}.{patch}')


if __name__ == '__main__':
    main()
