from bioetl.infrastructure.clients.chembl.response_parser import ChemblResponseParser


def test_parse_activities():
    parser = ChemblResponseParser()
    response = {
        "activities": [{"id": 1}, {"id": 2}],
        "page_meta": {"limit": 20}
    }
    records = parser.parse(response)
    assert len(records) == 2
    assert records[0]["id"] == 1


def test_parse_empty():
    parser = ChemblResponseParser()
    response = {"page_meta": {}}
    records = parser.parse(response)
    assert records == []


def test_extract_metadata():
    parser = ChemblResponseParser()
    response = {"page_meta": {"offset": 10}}
    meta = parser.extract_metadata(response)
    assert meta["offset"] == 10
