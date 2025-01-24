"""Cross check strings against all translations."""

import json
from pathlib import Path

ALL_STRINGS = "custom_components/polestar_api/strings.json"
TRANSLATED_STRINGS_DIR = "custom_components/polestar_api/translations"

with open(ALL_STRINGS) as fp:
    all_strings = json.load(fp)


all_entity_strings: dict[str, set[str]] = {
    entity_type: set(entity_strings.keys())
    for entity_type, entity_strings in all_strings["entity"].items()
}


for filename in Path(TRANSLATED_STRINGS_DIR).glob("*.json"):
    language_tag = filename.stem
    with open(filename) as fp:
        translated_strings = json.load(fp)

    entity_strings: dict[str, set[str]] = {
        entity_type: set(entity_strings.keys())
        for entity_type, entity_strings in translated_strings["entity"].items()
    }

    for entity_type in all_entity_strings:
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
