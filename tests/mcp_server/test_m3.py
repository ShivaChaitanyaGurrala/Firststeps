"""M3 tests — error normalization, response contract validation, pagination,
and response shaping. Same pattern as test_tools.py/test_m2.py: each test
opens `mcp_client` itself with `async with` (see conftest.py's mcp_client
docstring for why), nothing here touches a real running data_service or a
real TMDB call.
"""

import pytest

from data_service.models import Credit, Person, Title


async def test_get_title_details_not_found_returns_clean_tool_error(mcp_client):
    """Regression test for the whole errors.py chain: a 404 from data_service
    must surface as a clean is_error tool result, not an unhandled exception
    / raw traceback reaching the client."""
    async with mcp_client as connected:
        result = await connected.call_tool("get_title_details", {"title_id": 999999})
    assert result.is_error
    error_text = " ".join(getattr(block, "text", "") for block in result.content)
    assert "Traceback" not in error_text
    assert error_text  # some clean message actually made it through


async def test_search_titles_offset(mcp_client, db_session):
    titles = [
        Title(id=90001, title="Zorder Movie A", popularity=30.0, vote_average=7.0, adult=False),
        Title(id=90002, title="Zorder Movie B", popularity=20.0, vote_average=7.0, adult=False),
        Title(id=90003, title="Zorder Movie C", popularity=10.0, vote_average=7.0, adult=False),
    ]
    db_session.add_all(titles)
    db_session.commit()

    async with mcp_client as connected:
        page1 = await connected.call_tool(
            "search_titles", {"query": "Zorder", "limit": 1, "offset": 0}
        )
        page2 = await connected.call_tool(
            "search_titles", {"query": "Zorder", "limit": 1, "offset": 1}
        )
        page3 = await connected.call_tool(
            "search_titles", {"query": "Zorder", "limit": 1, "offset": 2}
        )

    assert page1.structured_content["results"][0]["title"] == "Zorder Movie A"
    assert page2.structured_content["results"][0]["title"] == "Zorder Movie B"
    assert page3.structured_content["results"][0]["title"] == "Zorder Movie C"


async def test_get_title_details_include_cast_crew(mcp_client, sample_title, db_session):
    person = Person(id=95001, name="Test Actor")
    db_session.add(person)
    db_session.flush()
    db_session.add(
        Credit(title_id=sample_title.id, person_id=person.id, role="cast", character="Hero", order=0)
    )
    db_session.commit()

    async with mcp_client as connected:
        with_cast = await connected.call_tool(
            "get_title_details", {"title_id": sample_title.id}
        )
        without_cast = await connected.call_tool(
            "get_title_details", {"title_id": sample_title.id, "include_cast_crew": False}
        )

    assert len(with_cast.structured_content["cast"]) == 1
    assert with_cast.structured_content["cast"][0]["name"] == "Test Actor"
    assert without_cast.structured_content["cast"] == []
    assert without_cast.structured_content["crew"] == []


def test_validate_model_wraps_validation_error_as_upstream_error():
    """Direct unit test of the schemas.py gap fix: a shape mismatch from
    data_service must become errors.UpstreamError, not a raw
    pydantic.ValidationError escaping unnormalized."""
    import errors
    import http_client
    import schemas

    with pytest.raises(errors.UpstreamError):
        http_client._validate_model(schemas.TitleSummary, {"title": "missing required id"})


def test_validate_list_wraps_validation_error_as_upstream_error():
    import errors
    import http_client
    import schemas
    from pydantic import TypeAdapter

    adapter = TypeAdapter(list[schemas.TitleSummary])
    with pytest.raises(errors.UpstreamError):
        http_client._validate_list(adapter, [{"title": "missing required id"}])
