import pytest

from api.passkeys import _parse_cose_key


def test_parse_cose_es256_negative_ints():
    """CBOR major type 1 encodes ``-1 - n``; alg -7 must decode from 0x26."""
    x = b"\x01" * 32
    y = b"\x02" * 32
    cose = b"\xa5" + b"\x01\x02" + b"\x03\x26" + b"\x20\x01" + b"\x21\x58\x20" + x + b"\x22\x58\x20" + y

    parsed = _parse_cose_key(cose)

    assert parsed[1] == 2
    assert parsed[3] == -7
    assert parsed[-1] == 1
    assert parsed[-2] == x
    assert parsed[-3] == y


def test_parse_cose_rs256_negative_int_257():
    """RS256 alg ``-257`` is CBOR negative value 256: ``0x39 0x01 0x00``."""
    modulus = b"\x03" * 32
    exponent = b"\x01\x00\x01"
    cose = (
        b"\xa4"
        + b"\x01\x03"
        + b"\x03\x39\x01\x00"
        + b"\x20\x58\x20"
        + modulus
        + b"\x21\x43"
        + exponent
    )

    parsed = _parse_cose_key(cose)

    assert parsed[1] == 3
    assert parsed[3] == -257
    assert parsed[-1] == modulus
    assert parsed[-2] == exponent


def test_parse_cose_rejects_truncated_bytes():
    with pytest.raises(ValueError, match="truncated"):
        _parse_cose_key(b"\xa1\x21\x58\x20\x01\x02")
