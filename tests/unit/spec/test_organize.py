import pytest

from clutchless.spec.organize import any_duplicates, TrackerSpec, FolderAssignment, SpecError


def test_any_duplicates():
    assert any_duplicates([1, 1, 3])
    assert not any_duplicates({1, 2, 3})


def test_folder_assignment_indices():
    assert FolderAssignment("1,2,3=folder").indices == {1, 2, 3}


def test_folder_assignment_folder():
    assert FolderAssignment("1,2,3=folder").folder == "folder"


def test_folder_assignment_non_alphanum_folder_name():
    with pytest.raises(SpecError) as e:
        _ = FolderAssignment._validate_folder_name("notalphanumeric!")

    assert "alphanumeric" in e.value.message


def test_folder_assignment_empty_folder_name():
    with pytest.raises(SpecError) as e:
        _ = FolderAssignment._validate_folder_name("")

    assert "empty" in e.value.message


def test_validate_split_parts_invalid_length():
    with pytest.raises(SpecError) as e:
        _ = FolderAssignment._validate_split_parts(['a', 'a', 'a'])

    assert "delimited" in e.value.message


def test_validate_split_parts():
    with pytest.raises(SpecError) as e:
        _ = FolderAssignment._validate_folder_name("")

    assert "empty" in e.value.message


def test_validate_indices():
    with pytest.raises(SpecError) as e:
        FolderAssignment("a,2=folder")._validate_indices()

    assert "integer" in e.value.message


def test_tracker_spec():
    result = TrackerSpec("1=folder;2=another")

    assert result == {
        1: "folder",
        2: "another"
    }


def test_tracker_spec_merge():
    assignments = [FolderAssignment("1=folder")]
    result = TrackerSpec._merge(assignments)

    assert result == {
        1: "folder"
    }


def test_tracker_spec_merge_duplicate():
    assignments = [FolderAssignment("1=folder"), FolderAssignment("1=another")]

    with pytest.raises(SpecError) as e:
        _ = TrackerSpec._merge(assignments)

    assert "duplicate" in e.value.message
