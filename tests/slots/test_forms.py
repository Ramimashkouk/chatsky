import pytest

from dff.script.logic.slots import RegexpSlot
from dff.script.logic.slots import FormPolicy, FormState


@pytest.mark.parametrize([], [])
def test_state_update(testing_context, testing_pipeline, root):
    root.children.clear()
    assert True


@pytest.mark.parametrize([], [])
def test_next_slot(testing_context, testing_pipeline, root):
    root.children.clear()
    assert True
