from invstruct.utils.trace import new_trace_id


def test_trace_id_format_and_uniqueness() -> None:
    first = new_trace_id()
    second = new_trace_id()

    assert first != second
    assert len(first) == 36
    assert first.count("-") == 4

