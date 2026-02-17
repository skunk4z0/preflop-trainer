import json

import pytest

from json_range_repository import JsonRangeRepository


def test_init_fails_when_schema_version_is_unsupported(tmp_path):
    final_tags = {
        "meta": {"schema_version": 999},
        "ranges": {
            "OR": {
                "CO": {
                    "AKO": "RAISE"
                }
            }
        },
    }
    final_tags_path = tmp_path / "final_tags.json"
    final_tags_path.write_text(json.dumps(final_tags), encoding="utf-8")

    with pytest.raises(ValueError, match="schema_version"):
        JsonRangeRepository(final_tags_path)


def test_init_succeeds_when_schema_version_is_missing_backward_compatible(tmp_path):
    final_tags = {
        "meta": {},
        "ranges": {
            "OR": {
                "CO": {
                    "AKO": "RAISE"
                }
            }
        },
    }
    final_tags_path = tmp_path / "final_tags.json"
    final_tags_path.write_text(json.dumps(final_tags), encoding="utf-8")

    repo = JsonRangeRepository(final_tags_path)

    tag, debug = repo.get_tag_for_hand("OR", "CO", "AKo")
    assert tag == "RAISE"
    
