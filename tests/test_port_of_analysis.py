from inpythotools import load_mat_database
from novitrack import analyse_nttestrecord, results_nttestrecord
from pathlib import Path

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
