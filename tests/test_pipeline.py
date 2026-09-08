import pandas as pd

from src.transformation.transform import transform_dataset
from src.validation.validate import validate_dataset


def test_validation_removes_duplicates_and_invalid_marks(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    for name in ("raw", "staging", "rejected"):
        (data_root / name).mkdir(parents=True)
    monkeypatch.setattr("src.validation.validate.DATA_ROOT", data_root)
    source = tmp_path / "input.csv"
    frame = pd.DataFrame([
        {"school": "GP", "sex": "F", "age": 17, "G1": 12, "G2": 13, "G3": 14},
        {"school": "GP", "sex": "F", "age": 17, "G1": 12, "G2": 13, "G3": 14},
        {"school": "MS", "sex": "M", "age": 18, "G1": 21, "G2": 10, "G3": 9},
    ])
    frame.to_csv(source, index=False)
    output = validate_dataset(source)
    result = pd.read_csv(output)
    assert len(result) == 1
    assert result.loc[0, "G3"] == 14
    rejected = pd.read_csv(next((data_root / "rejected").glob("*.csv")))
    assert set(rejected["reason"]) == {"duplicate_record", "mark_out_of_range_or_non_numeric"}


def test_transformation_creates_required_features(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    (data_root / "cleaned").mkdir(parents=True)
    monkeypatch.setattr("src.transformation.transform.DATA_ROOT", data_root)
    source = tmp_path / "validated.csv"
    pd.DataFrame([{
        "student_id": "S1", "school": "GP", "age": 17, "G1": 12, "G2": 14, "G3": 15,
        "absences": 3, "studytime": 3, "failures": 0,
    }]).to_csv(source, index=False)
    output = transform_dataset(source)
    result = pd.read_csv(output)
    required = {"attendance_percentage", "average_internal_marks", "assignment_completion_rate", "previous_grade", "risk_flag"}
    assert required.issubset(result.columns)
    assert result.loc[0, "pass_flag"] == 1
    assert result.loc[0, "risk_flag"] == 0
