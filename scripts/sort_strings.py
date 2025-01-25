"""Sort strings for all translations."""

import json
from pathlib import Path

ALL_STRINGS = Path("custom_components/polestar_api/strings.json")
TRANSLATED_STRINGS_DIR = Path("custom_components/polestar_api/translations")


def sort_strings(filename: str | Path) -> None:
    with open(filename) as fp:
        data = json.load(fp)
    with open(filename, "w") as fp:
        json.dump(data, fp, indent=2, sort_keys=True, ensure_ascii=False)
        fp.write("\n")
    print(f"Sorted {filename}")


sort_strings(ALL_STRINGS)

for filename in Path(TRANSLATED_STRINGS_DIR).glob("*.json"):
    sort_strings(filename)
