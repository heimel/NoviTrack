import numpy as np
import pytest

from novitrack.load_photometry import parse_channels


@pytest.mark.parametrize("comment", [None, "", np.array([])])
def test_parse_channels_accepts_empty_comment_representations(comment):
    assert parse_channels(comment) == {}


def test_parse_channels_accepts_native_string():
    assert parse_channels("channel1 = signal, channel2 = isosbestic.") == {
        "Channel1": "signal",
        "Channel2": "isosbestic",
    }
