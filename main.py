import sys


def main():
    if len(sys.argv) != 3:
        print("Usage: python main.py <firstname> <lastname>")
        return 0

    first_name = sys.argv[1]
    last_name = sys.argv[2]
    print(first_name)
    print(last_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
