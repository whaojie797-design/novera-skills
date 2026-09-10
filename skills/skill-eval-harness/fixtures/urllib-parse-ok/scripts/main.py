import argparse

from urllib.parse import urlparse


def main():
    parsed = urlparse("https://example.com/path")
    print(parsed.netloc)


if __name__ == "__main__":
    main()
