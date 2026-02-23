from app.core import MiningSystem
from app.cli import run_cli


def main():
    system = MiningSystem()
    print(system.system_info())
    run_cli("data/ds024.pdf")


if __name__ == "__main__":
    main()