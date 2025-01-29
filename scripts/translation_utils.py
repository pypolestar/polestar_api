"""Check and sort strings in all translations."""

import argparse
import json
from pathlib import Path

ALL_STRINGS = Path("custom_components/polestar_api/strings.json")
TRANSLATED_STRINGS_DIR = Path("custom_components/polestar_api/translations")


def get_all_translated_strings_filenames() -> list[Path]:
    """Get all translated strings filenames."""
    return list(Path(TRANSLATED_STRINGS_DIR).glob("*.json"))


def check_strings(all_strings, translated_strings, language_tag: str):
    """Check strings against all translations."""

    all_entity_strings: dict[str, set[str]] = {
        entity_type: set(entity_strings.keys())
        for entity_type, entity_strings in all_strings["entity"].items()
    }

    entity_strings: dict[str, set[str]] = {
        entity_type: set(entity_strings.keys())
        for entity_type, entity_strings in translated_strings["entity"].items()
    }

    for entity_type in all_entity_strings:
        if entity_type not in entity_strings:
            print(f"Missing entity type {entity_type} in {language_tag}")
            print("")
            continue

        missing_strings = all_entity_strings[entity_type] - entity_strings[entity_type]
        superflous_strings = (
            entity_strings[entity_type] - all_entity_strings[entity_type]
        )
        if missing_strings:
            print(f"Missing strings for {entity_type} in {language_tag}")
            for string in missing_strings:
                print(f"- {string}")
            print("")

        if superflous_strings:
            print(f"Superflous strings for {entity_type} in {language_tag}")
            for string in superflous_strings:
                print(f"- {string}")
            print("")


def sort_json_keys(filename: Path) -> None:
    """Sort keys in a JSON file."""

    with open(filename) as fp:
        data = json.load(fp)
    with open(filename, "w") as fp:
        json.dump(data, fp, indent=2, sort_keys=True, ensure_ascii=False)
        fp.write("\n")
    print(f"Sorted {filename}")


def main() -> None:
    """Main function."""

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--check", action=argparse.BooleanOptionalAction, default=True
    )
    arg_parser.add_argument("--sort", action=argparse.BooleanOptionalAction)
    args = arg_parser.parse_args()

    if args.check:
        with open(ALL_STRINGS) as fp:
            all_strings = json.load(fp)

        for filename in get_all_translated_strings_filenames():
            language_tag = filename.stem
            with open(filename) as fp:
                translated_strings = json.load(fp)
            check_strings(all_strings, translated_strings, language_tag)

    if args.sort:
        sort_json_keys(ALL_STRINGS)
        for filename in get_all_translated_strings_filenames():
            sort_json_keys(filename)


if __name__ == "__main__":
    main()
