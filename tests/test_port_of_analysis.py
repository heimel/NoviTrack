from inpythotools import load_mat_database
from novitrack import analyse_nttestrecord, results_nttestrecord
from novitrack.get_ethogram import get_ethogram
from pathlib import Path


def test_ethogram_uses_white_background():
    record = {
        "sessionid": "example",
        "measures": {
            "markers": [
                {"marker": "a", "time": 0.0},
                {"marker": "b", "time": 1.0},
            ],
            "min_time": 0.0,
            "max_time": 2.0,
        },
    }
    params = {
        "markers": [
            {"marker": "a", "behavior": True, "description": "approach", "color": [1.0, 0.0, 0.0]},
            {"marker": "b", "behavior": True, "description": "back", "color": [0.0, 1.0, 0.0]},
        ],
        "show_markers": True,
    }

    _ethogram, _t, _motifs, ax = get_ethogram(record, show=True, params=params)
    assert ax.images[0].cmap(0)[:3] == (1.0, 1.0, 1.0)


def test_analysis():
    filename = Path(__file__).resolve().parent.parent / "test_data" / "nttestdb_examples.mat"
    db = load_mat_database(filename)
#    record = db.iloc[-1].to_dict()
    record = db.iloc[1]
    out = analyse_nttestrecord(record, verbose=False)
    results = results_nttestrecord(out, show=False)
    return results


if __name__ == "__main__":
    test_analysis()
