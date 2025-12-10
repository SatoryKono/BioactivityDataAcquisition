from bioetl.domain.enums import ErrorAction


def test_error_action_values():
    assert ErrorAction.FAIL.value == "fail"
    assert ErrorAction.SKIP.value == "skip"
    assert ErrorAction.RETRY.value == "retry"
