"""
Tests for ChemblPaginator.
"""
from bioetl.clients.chembl.paginator import ChemblPaginator


def test_get_items():
    """Test extracting items from response."""
    paginator = ChemblPaginator()
    response = {"activities": [{"id": 1}, {"id": 2}], "page_meta": {}}
    items = paginator.get_items(response)
    assert len(items) == 2
    assert items[0]["id"] == 1


def test_get_next_marker_has_next():
    """Test getting next marker when pages exist."""
    paginator = ChemblPaginator()
    response = {
        "page_meta": {
            "next": "/url?offset=20&limit=20",
            "limit": 20,
            "offset": 0,
            "total_count": 100
        }
    }
    marker = paginator.get_next_marker(response)
    assert marker == 20  # offset + limit
    assert paginator.has_more(response) is True


def test_get_next_marker_no_next():
    """Test getting next marker when no more pages."""
    paginator = ChemblPaginator()
    response = {
        "page_meta": {
            "next": None,
            "limit": 20,
            "offset": 80,
            "total_count": 100
        }
    }
    marker = paginator.get_next_marker(response)
    assert marker is None
    assert paginator.has_more(response) is False
