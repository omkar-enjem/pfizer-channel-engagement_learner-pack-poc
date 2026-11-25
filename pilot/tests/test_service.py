"""The API's work without a web framework or a model key."""
import json

import pytest

from agent import pipeline as P
from agent import service as S


class FakeGraph:
    """Stands in for the compiled graph: runs the plain-Python steps."""
    def invoke(self, state):
        raise NotImplementedError


def test_health_counts_rows():
    assert S.health() == {"claims": 4503, "emails": 30}


def test_emails_list():
    e = S.emails()
    assert len(e) == 30 and set(e[0]) == {"email_id", "from", "subject"}


@pytest.mark.parametrize("bad", ["", "   ", None, "x" * 4001], ids=["empty", "blank", "none", "too_long"])
def test_bad_input(bad):
    with pytest.raises(S.BadInput):
        S.check(bad, graph=None)
