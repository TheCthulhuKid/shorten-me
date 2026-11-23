import pytest

from shorten_me.codec import InvalidShortCode, decode, encode


def test_encode_then_decode_returns_the_same_id():
    assert decode(encode(598463)) == 598463


def test_existing_short_codes_still_decode():
    assert decode("p") == 1
    assert decode("vcTJ") == 598463


def test_decode_rejects_codes_with_a_leading_zero_digit():
    with pytest.raises(InvalidShortCode):
        decode("Dp")


def test_decode_rejects_characters_outside_the_alphabet():
    with pytest.raises(InvalidShortCode):
        decode("Oo0")
