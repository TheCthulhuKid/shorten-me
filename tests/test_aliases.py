import pytest

from shorten_me.aliases import InvalidAlias, validate_alias


def test_alias_that_could_be_a_generated_code_is_rejected():
    with pytest.raises(InvalidAlias):
        validate_alias("news")
