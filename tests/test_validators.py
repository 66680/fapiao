from invstruct.validators.engine import run_validators


def test_validators_required_and_gt() -> None:
    record_dict = {
        "merchant_name": None,
        "total_amount_gross": 0,
        "invoice_number": "123",
    }
    validators = [
        {"type": "required", "field": "merchant_name", "severity": "critical"},
        {"type": "gt", "field": "total_amount_gross", "value": 0, "severity": "critical"},
    ]

    issues = run_validators(record_dict, validators)
    assert len(issues) == 2
    assert issues[0]["type"] == "required"
    assert issues[1]["type"] == "gt"

