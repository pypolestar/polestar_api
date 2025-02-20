"""Check and sort strings in all translations."""

import argparse
import json
import logging
from pathlib import Path

ALL_STRINGS = Path("custom_components/polestar_api/strings.json")
TRANSLATED_STRINGS_DIR = Path("custom_components/polestar_api/translations")


def get_all_translated_strings_filenames() -> list[Path]:
    """Get all translated strings filenames."""
    return list(Path(TRANSLATED_STRINGS_DIR).glob("*.json"))


def cross_check_strings(all_strings, translated_strings, language_tag: str):
    """Cross check strings against all translations."""

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
            logging.warning(f"Missing entity type {entity_type} in {language_tag}")
            continue

        missing_strings = all_entity_strings[entity_type] - entity_strings[entity_type]
        superflous_strings = (
            entity_strings[entity_type] - all_entity_strings[entity_type]
        )
        for string in missing_strings:
            logging.warning(
                f"Missing string for {entity_type} in {language_tag}, {string}"
            )

        for string in superflous_strings:
            logging.warning(
                f"Superflous string for {entity_type} in {language_tag}, {string}"
            )


def sort_json_keys(filename: Path, check_only: bool = False) -> None:
    """Sort keys in a JSON file."""

    with open(filename) as fp:
        input_data = fp.read()
        data = json.loads(input_data)

    output_data = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    # Compare input and output
    if input_data == output_data:
        if not check_only:
            logging.info(f"Input already sorted {filename}")
        return

    if check_only:
        logging.error(f"Input not sorted: {filename}")
        raise SystemExit(1)

    with open(filename, "w") as fp:
        fp.write(output_data)
    logging.info(f"Sorted {filename}")


def main() -> None:
    """Main function."""

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--sort", action=argparse.BooleanOptionalAction)
    arg_parser.add_argument("--test", action=argparse.BooleanOptionalAction)
    args = arg_parser.parse_args()

    check_only = args.test or not args.sort

    with open(ALL_STRINGS) as fp:
        all_strings = json.load(fp)

    for filename in get_all_translated_strings_filenames():
        language_tag = filename.stem
        with open(filename) as fp:
            translated_strings = json.load(fp)
        cross_check_strings(all_strings, translated_strings, language_tag)

    sort_json_keys(ALL_STRINGS, check_only=check_only)
    for filename in get_all_translated_strings_filenames():
        sort_json_keys(filename, check_only=check_only)


if __name__ == "__main__":
    main()
