import argparse
import csv
from pathlib import Path


def read_row_values(dataset_path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    with dataset_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            rows.append(list(row.values()))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read a CSV dataset and print values for each row."
    )
    parser.add_argument("dataset", type=Path, help="Path to the CSV dataset.")
    args = parser.parse_args()

    row_values = read_row_values(args.dataset)
    for values in row_values:
        print(values)


if __name__ == "__main__":
    main()
