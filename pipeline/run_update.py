"""
The whole pipeline, in order. This is what the daily job runs.

  python pipeline/run_update.py
"""
from fetch import fetch
from transform import transform
from validate_data import validate
from build_site import build


def main():
    fetch()
    transform()
    validate()
    build()
    print("\ndone — open site/index.html to see the result")


if __name__ == "__main__":
    main()
