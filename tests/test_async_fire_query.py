"""
Integration tests for AsyncFireQuery (Phase 2.5, asynchronous).

Tests the async chainable query builder for Firestore collections against
the Firestore emulator.
"""

import pytest

from src.fire_prox import AsyncFireProx
from src.fire_prox.testing import async_testing_client


@pytest.fixture
async def async_db():
    """Create an AsyncFireProx instance connected to the emulator."""
    client = async_testing_client()
    return AsyncFireProx(client)


@pytest.fixture
async def async_test_collection(async_db):
    """Return a test collection with sample data."""
    collection = async_db.collection('async_query_test_collection')

    # Create sample documents for testing
    users = [
        {'name': 'Ada Lovelace', 'birth_year': 1815, 'country': 'England', 'score': 95},
        {'name': 'Charles Babbage', 'birth_year': 1791, 'country': 'England', 'score': 90},
        {'name': 'Alan Turing', 'birth_year': 1912, 'country': 'England', 'score': 98},
        {'name': 'Grace Hopper', 'birth_year': 1906, 'country': 'USA', 'score': 92},
        {'name': 'John von Neumann', 'birth_year': 1903, 'country': 'Hungary', 'score': 97},
    ]

    for i, user_data in enumerate(users):
        doc = collection.new()
        for key, value in user_data.items():
            setattr(doc, key, value)
        await doc.save(doc_id=f'user{i+1}')

    yield collection


@pytest.mark.asyncio
class TestBasicQueriesAsync:
    """Test basic async query operations."""

    async def test_where_single_condition(self, async_test_collection):
        """Test simple where clause with single condition."""
        # Query for users born after 1900
        query = async_test_collection.where('birth_year', '>', 1900)
        results = await query.get()

        assert len(results) == 3  # John (1903), Grace (1906), Alan (1912)
        years = {user.birth_year for user in results}
        assert years == {1903, 1906, 1912}

    async def test_where_equality(self, async_test_collection):
        """Test where clause with equality operator."""
        # Query for users from England
        query = async_test_collection.where('country', '==', 'England')
        results = await query.get()

        assert len(results) == 3  # Ada, Charles, Alan
        for user in results:
            assert user.country == 'England'

    async def test_where_less_than(self, async_test_collection):
        """Test where clause with less than operator."""
        # Query for users born before 1850
        query = async_test_collection.where('birth_year', '<', 1850)
        results = await query.get()

        assert len(results) == 2  # Ada and Charles
        for user in results:
            assert user.birth_year < 1850

    async def test_where_greater_or_equal(self, async_test_collection):
        """Test where clause with >= operator."""
        # Query for users with score >= 95
        query = async_test_collection.where('score', '>=', 95)
        results = await query.get()

        assert len(results) == 3  # Ada (95), Alan (98), John (97)
        for user in results:
            assert user.score >= 95

    async def test_where_not_equal(self, async_test_collection):
        """Test where clause with != operator."""
        # Query for users not from England
        query = async_test_collection.where('country', '!=', 'England')
        results = await query.get()

        assert len(results) == 2  # Grace and John
        for user in results:
            assert user.country != 'England'


@pytest.mark.asyncio
class TestChainedQueriesAsync:
    """Test chaining multiple async query operations."""

    async def test_multiple_where_conditions(self, async_test_collection):
        """Test chaining multiple where clauses."""
        # Query for English users born after 1850
        query = (async_test_collection
                 .where('country', '==', 'England')
                 .where('birth_year', '>', 1850))
        results = await query.get()

        assert len(results) == 1  # Only Alan (1912) - Ada was born in 1815
        for user in results:
            assert user.country == 'England'
            assert user.birth_year > 1850

    async def test_where_with_order_by(self, async_test_collection):
        """Test combining where and order_by."""
        # Query for users born after 1800, ordered by birth year
        query = (async_test_collection
                 .where('birth_year', '>', 1800)
                 .order_by('birth_year'))
        results = await query.get()

        # Should be ordered: Ada (1815), John (1903), Grace (1906), Alan (1912)
        assert len(results) == 4
        years = [user.birth_year for user in results]
        assert years == sorted(years)  # Verify ascending order

    async def test_where_order_by_limit(self, async_test_collection):
        """Test chaining where, order_by, and limit."""
        # Get top 2 scorers from England
        query = (async_test_collection
                 .where('country', '==', 'England')
                 .order_by('score', direction='DESCENDING')
                 .limit(2))
        results = await query.get()

        assert len(results) == 2
        # Should be Alan (98) and Ada (95)
        assert results[0].score == 98
        assert results[1].score == 95


@pytest.mark.asyncio
class TestOrderByAsync:
    """Test ordering async query results."""

    async def test_order_by_ascending(self, async_test_collection):
        """Test ordering results in ascending order."""
        query = async_test_collection.order_by('birth_year')
        results = await query.get()

        years = [user.birth_year for user in results]
        assert years == sorted(years)

    async def test_order_by_descending(self, async_test_collection):
        """Test ordering results in descending order."""
        query = async_test_collection.order_by('birth_year', direction='DESCENDING')
        results = await query.get()

        years = [user.birth_year for user in results]
        assert years == sorted(years, reverse=True)

    async def test_order_by_multiple_fields(self, async_test_collection):
        """Test ordering by multiple fields."""
        # Order by country, then by birth_year
        query = (async_test_collection
                 .order_by('country')
                 .order_by('birth_year'))
        results = await query.get()

        # Results should be grouped by country and ordered by year within each group
        assert len(results) == 5
        # Verify England group is ordered correctly
        england_users = [u for u in results if u.country == 'England']
        england_years = [u.birth_year for u in england_users]
        assert england_years == sorted(england_years)

    async def test_order_by_invalid_direction_raises_error(self, async_test_collection):
        """Test that invalid direction raises ValueError."""
        with pytest.raises(ValueError, match="Invalid direction"):
            async_test_collection.order_by('birth_year', direction='INVALID')


@pytest.mark.asyncio
class TestLimitAsync:
    """Test limiting async query results."""

    async def test_limit_results(self, async_test_collection):
        """Test limiting the number of results."""
        query = async_test_collection.limit(3)
        results = await query.get()

        assert len(results) == 3

    async def test_limit_with_order_by(self, async_test_collection):
        """Test limit combined with ordering."""
        # Get 2 oldest users
        query = (async_test_collection
                 .order_by('birth_year')
                 .limit(2))
        results = await query.get()

        assert len(results) == 2
        assert results[0].birth_year == 1791  # Charles
        assert results[1].birth_year == 1815  # Ada

    async def test_limit_zero_raises_error(self, async_test_collection):
        """Test that limit(0) raises ValueError."""
        with pytest.raises(ValueError, match="Limit count must be positive"):
            async_test_collection.limit(0)

    async def test_limit_negative_raises_error(self, async_test_collection):
        """Test that negative limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit count must be positive"):
            async_test_collection.limit(-1)


@pytest.mark.asyncio
class TestQueryExecutionAsync:
    """Test different async query execution methods."""

    async def test_get_returns_list(self, async_test_collection):
        """Test that get() returns a list of AsyncFireObjects."""
        query = async_test_collection.where('country', '==', 'England')
        results = await query.get()

        assert isinstance(results, list)
        assert len(results) > 0
        for obj in results:
            assert obj.is_loaded()
            assert hasattr(obj, 'name')

    async def test_stream_returns_async_iterator(self, async_test_collection):
        """Test that stream() returns an async iterator."""
        query = async_test_collection.where('country', '==', 'England')
        results = query.stream()

        # Should be an async iterator/generator
        count = 0
        async for obj in results:
            assert obj.is_loaded()
            assert hasattr(obj, 'name')
            count += 1

        assert count == 3

    async def test_empty_query_returns_empty_list(self, async_test_collection):
        """Test that query with no matches returns empty list."""
        query = async_test_collection.where('birth_year', '>', 2000)
        results = await query.get()

        assert results == []

    async def test_get_all_returns_all_documents(self, async_test_collection):
        """Test that get_all() returns all documents in collection."""
        results = []
        async for doc in async_test_collection.get_all():
            results.append(doc)

        assert len(results) == 5  # All 5 sample users
        for obj in results:
            assert obj.is_loaded()


@pytest.mark.asyncio
class TestImmutableQueryPatternAsync:
    """Test that async queries follow immutable pattern."""

    async def test_where_returns_new_instance(self, async_test_collection):
        """Test that where() returns a new AsyncFireQuery instance."""
        query1 = async_test_collection.where('country', '==', 'England')
        query2 = query1.where('birth_year', '>', 1850)

        # query2 should have different results than query1
        results1 = await query1.get()
        results2 = await query2.get()

        assert len(results1) > len(results2)

    async def test_order_by_returns_new_instance(self, async_test_collection):
        """Test that order_by() returns a new AsyncFireQuery instance."""
        query1 = async_test_collection.where('country', '==', 'England')
        query2 = query1.order_by('birth_year')

        # Both should have same count but query2 is ordered
        results1 = await query1.get()
        results2 = await query2.get()

        assert len(results1) == len(results2)

    async def test_limit_returns_new_instance(self, async_test_collection):
        """Test that limit() returns a new AsyncFireQuery instance."""
        query1 = async_test_collection.where('country', '==', 'England')
        query2 = query1.limit(2)

        # query2 should have fewer results
        results1 = await query1.get()
        results2 = await query2.get()

        assert len(results1) > len(results2)
        assert len(results2) == 2


@pytest.mark.asyncio
class TestEdgeCasesAsync:
    """Test edge cases and error conditions for async queries."""

    async def test_query_on_empty_collection(self, async_db):
        """Test querying an empty collection."""
        empty_collection = async_db.collection('empty_async_collection')
        query = empty_collection.where('field', '==', 'value')
        results = await query.get()

        assert results == []

    async def test_query_with_nonexistent_field(self, async_test_collection):
        """Test querying for a field that doesn't exist."""
        query = async_test_collection.where('nonexistent_field', '==', 'value')
        results = await query.get()

        # Should return empty results, not error
        assert results == []

    async def test_stream_consumption(self, async_test_collection):
        """Test consuming async stream."""
        query = async_test_collection.where('country', '==', 'England')
        stream = query.stream()

        # Consume the stream
        results = []
        async for obj in stream:
            results.append(obj)

        assert len(results) == 3


@pytest.mark.asyncio
class TestQueryPaginationAsync:
    """Test cursor-based pagination with start_at, start_after, end_at, end_before."""

    async def test_start_at_with_field_value(self, async_test_collection):
        """Test start_at with field value dictionary (inclusive)."""
        # Order by birth_year: Charles (1791), Ada (1815), John (1903), Grace (1906), Alan (1912)
        # Start at 1903 (inclusive) - should include John, Grace, Alan
        query = (async_test_collection
                 .order_by('birth_year')
                 .start_at({'birth_year': 1903}))
        results = await query.get()

        assert len(results) == 3
        years = [user.birth_year for user in results]
        assert years == [1903, 1906, 1912]
        assert results[0].name == 'John von Neumann'
        assert results[1].name == 'Grace Hopper'
        assert results[2].name == 'Alan Turing'

    async def test_start_after_excludes_cursor(self, async_test_collection):
        """Test start_after excludes the cursor document (exclusive)."""
        # Order by birth_year: Charles (1791), Ada (1815), John (1903), Grace (1906), Alan (1912)
        # Start after 1903 (exclusive) - should include Grace, Alan only
        query = (async_test_collection
                 .order_by('birth_year')
                 .start_after({'birth_year': 1903}))
        results = await query.get()

        assert len(results) == 2
        years = [user.birth_year for user in results]
        assert years == [1906, 1912]
        assert results[0].name == 'Grace Hopper'
        assert results[1].name == 'Alan Turing'

    async def test_end_at_with_field_value(self, async_test_collection):
        """Test end_at with field value dictionary (inclusive)."""
        # Order by birth_year: Charles (1791), Ada (1815), John (1903), Grace (1906), Alan (1912)
        # End at 1903 (inclusive) - should include Charles, Ada, John
        query = (async_test_collection
                 .order_by('birth_year')
                 .end_at({'birth_year': 1903}))
        results = await query.get()

        assert len(results) == 3
        years = [user.birth_year for user in results]
        assert years == [1791, 1815, 1903]
        assert results[0].name == 'Charles Babbage'
        assert results[1].name == 'Ada Lovelace'
        assert results[2].name == 'John von Neumann'

    async def test_end_before_excludes_cursor(self, async_test_collection):
        """Test end_before excludes the cursor document (exclusive)."""
        # Order by birth_year: Charles (1791), Ada (1815), John (1903), Grace (1906), Alan (1912)
        # End before 1903 (exclusive) - should include Charles, Ada only
        query = (async_test_collection
                 .order_by('birth_year')
                 .end_before({'birth_year': 1903}))
        results = await query.get()

        assert len(results) == 2
        years = [user.birth_year for user in results]
        assert years == [1791, 1815]
        assert results[0].name == 'Charles Babbage'
        assert results[1].name == 'Ada Lovelace'

    async def test_pagination_chain(self, async_test_collection):
        """Test typical pagination pattern: order_by + limit + start_after."""
        # Simulate pagination: get first page, then get next page

        # Page 1: Get first 2 users ordered by birth year
        page1_query = (async_test_collection
                      .order_by('birth_year')
                      .limit(2))
        page1_results = await page1_query.get()

        assert len(page1_results) == 2
        assert page1_results[0].birth_year == 1791  # Charles
        assert page1_results[1].birth_year == 1815  # Ada

        # Page 2: Start after the last document from page 1
        last_year = page1_results[-1].birth_year
        page2_query = (async_test_collection
                      .order_by('birth_year')
                      .start_after({'birth_year': last_year})
                      .limit(2))
        page2_results = await page2_query.get()

        assert len(page2_results) == 2
        assert page2_results[0].birth_year == 1903  # John
        assert page2_results[1].birth_year == 1906  # Grace

        # Page 3: Start after the last document from page 2
        last_year = page2_results[-1].birth_year
        page3_query = (async_test_collection
                      .order_by('birth_year')
                      .start_after({'birth_year': last_year})
                      .limit(2))
        page3_results = await page3_query.get()

        assert len(page3_results) == 1  # Only Alan left
        assert page3_results[0].birth_year == 1912  # Alan

    async def test_cursor_with_snapshot(self, async_test_collection):
        """Test using DocumentSnapshot as cursor instead of field values."""
        # Get all users ordered by birth year
        query = async_test_collection.order_by('birth_year')
        all_results = await query.get()

        # Get the document reference for the middle user (John, 1903)
        john = [u for u in all_results if u.birth_year == 1903][0]
        john_ref = john._doc_ref
        john_snapshot = await john_ref.get()

        # Use snapshot as cursor for start_after
        query_after = (async_test_collection
                      .order_by('birth_year')
                      .start_after(john_snapshot))
        results_after = await query_after.get()

        # Should get Grace (1906) and Alan (1912)
        assert len(results_after) == 2
        assert results_after[0].birth_year == 1906
        assert results_after[1].birth_year == 1912

        # Use snapshot as cursor for end_at
        query_end = (async_test_collection
                    .order_by('birth_year')
                    .end_at(john_snapshot))
        results_end = await query_end.get()

        # Should get Charles (1791), Ada (1815), John (1903)
        assert len(results_end) == 3
        assert results_end[0].birth_year == 1791
        assert results_end[1].birth_year == 1815
        assert results_end[2].birth_year == 1903

    async def test_range_query_with_start_and_end(self, async_test_collection):
        """Test combining start_at and end_at for range queries."""
        # Get users between 1815 and 1906 (inclusive)
        query = (async_test_collection
                .order_by('birth_year')
                .start_at({'birth_year': 1815})
                .end_at({'birth_year': 1906}))
        results = await query.get()

        assert len(results) == 3
        years = [user.birth_year for user in results]
        assert years == [1815, 1903, 1906]
        assert results[0].name == 'Ada Lovelace'
        assert results[1].name == 'John von Neumann'
        assert results[2].name == 'Grace Hopper'

    async def test_descending_order_with_pagination(self, async_test_collection):
        """Test pagination works with descending order."""
        # Order descending: Alan (1912), Grace (1906), John (1903), Ada (1815), Charles (1791)
        # Get first 2, then continue from there
        page1_query = (async_test_collection
                      .order_by('birth_year', direction='DESCENDING')
                      .limit(2))
        page1_results = await page1_query.get()

        assert len(page1_results) == 2
        assert page1_results[0].birth_year == 1912  # Alan
        assert page1_results[1].birth_year == 1906  # Grace

        # Continue after Grace (1906)
        page2_query = (async_test_collection
                      .order_by('birth_year', direction='DESCENDING')
                      .start_after({'birth_year': 1906})
                      .limit(2))
        page2_results = await page2_query.get()

        assert len(page2_results) == 2
        assert page2_results[0].birth_year == 1903  # John
        assert page2_results[1].birth_year == 1815  # Ada


@pytest.mark.asyncio
class TestProjectionsAsync:
    """Test async query projections with .select() method."""

    async def test_select_single_field(self, async_test_collection):
        """Test selecting a single field returns dictionaries."""
        # Select only the name field
        query = async_test_collection.select('name')
        results = await query.get()

        assert len(results) == 5
        # Results should be dictionaries, not AsyncFireObjects
        for result in results:
            assert isinstance(result, dict)
            assert 'name' in result
            # Only the selected field should be present
            assert set(result.keys()) == {'name'}

    async def test_select_multiple_fields(self, async_test_collection):
        """Test selecting multiple fields."""
        # Select name and birth_year
        query = async_test_collection.select('name', 'birth_year')
        results = await query.get()

        assert len(results) == 5
        for result in results:
            assert isinstance(result, dict)
            assert 'name' in result
            assert 'birth_year' in result
            # Only selected fields should be present
            assert set(result.keys()) == {'name', 'birth_year'}
            # Values should be correct
            assert isinstance(result['name'], str)
            assert isinstance(result['birth_year'], int)

    async def test_select_with_where_filter(self, async_test_collection):
        """Test combining select with where clause."""
        # Select name and score for English users
        query = (async_test_collection
                 .where('country', '==', 'England')
                 .select('name', 'score'))
        results = await query.get()

        assert len(results) == 3  # Ada, Charles, Alan
        for result in results:
            assert isinstance(result, dict)
            assert set(result.keys()) == {'name', 'score'}
            assert result['score'] >= 90

    async def test_select_with_order_by(self, async_test_collection):
        """Test combining select with order_by."""
        # Select name and birth_year, ordered by birth_year
        query = (async_test_collection
                 .select('name', 'birth_year')
                 .order_by('birth_year'))
        results = await query.get()

        assert len(results) == 5
        # Verify ordering
        years = [r['birth_year'] for r in results]
        assert years == sorted(years)
        # Verify only selected fields present
        for result in results:
            assert set(result.keys()) == {'name', 'birth_year'}

    async def test_select_with_limit(self, async_test_collection):
        """Test combining select with limit."""
        # Select name for first 3 users
        query = (async_test_collection
                 .select('name')
                 .order_by('birth_year')
                 .limit(3))
        results = await query.get()

        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)
            assert 'name' in result
            assert set(result.keys()) == {'name'}

    async def test_select_stream_returns_dicts(self, async_test_collection):
        """Test that select with stream() yields dictionaries."""
        query = async_test_collection.select('name', 'country')
        results = []

        async for result in query.stream():
            assert isinstance(result, dict)
            assert set(result.keys()) == {'name', 'country'}
            results.append(result)

        assert len(results) == 5

    async def test_select_no_fields_raises_error(self, async_test_collection):
        """Test that select() with no fields raises ValueError."""
        with pytest.raises(ValueError, match="select\\(\\) requires at least one field"):
            async_test_collection.select()

    async def test_select_returns_new_query_instance(self, async_test_collection):
        """Test that select() follows immutable pattern."""
        query1 = async_test_collection.where('country', '==', 'England')
        query2 = query1.select('name')

        # query1 should still return AsyncFireObjects
        results1 = await query1.get()
        assert len(results1) == 3
        for result in results1:
            assert hasattr(result, 'name')  # AsyncFireObject
            assert hasattr(result, 'is_loaded')

        # query2 should return dictionaries
        results2 = await query2.get()
        assert len(results2) == 3
        for result in results2:
            assert isinstance(result, dict)
            assert set(result.keys()) == {'name'}

    async def test_select_with_chaining(self, async_test_collection):
        """Test complex query chain with select."""
        # Complex chain: where + select + order_by + limit
        query = (async_test_collection
                 .where('birth_year', '>', 1850)
                 .select('name', 'birth_year', 'score')
                 .order_by('score', direction='DESCENDING')
                 .limit(2))
        results = await query.get()

        assert len(results) == 2
        # Should be Alan (98) and John (97)
        assert results[0]['score'] == 98
        assert results[1]['score'] == 97
        # Verify only selected fields
        for result in results:
            assert set(result.keys()) == {'name', 'birth_year', 'score'}

    async def test_select_empty_results(self, async_test_collection):
        """Test select with query that returns no results."""
        query = (async_test_collection
                 .where('birth_year', '>', 2000)
                 .select('name'))
        results = await query.get()

        assert results == []


@pytest.fixture
async def async_test_collection_with_refs(async_db):
    """Create test collection with DocumentReference fields."""
    # Create users collection
    users = async_db.collection('async_projection_users')
    user1 = users.new()
    user1.name = 'Alice'
    user1.email = 'alice@example.com'
    await user1.save(doc_id='alice')

    user2 = users.new()
    user2.name = 'Bob'
    user2.email = 'bob@example.com'
    await user2.save(doc_id='bob')

    # Create posts collection with author references
    posts = async_db.collection('async_projection_posts')

    post1 = posts.new()
    post1.title = 'First Post'
    post1.content = 'Hello World'
    post1.author = users.doc('alice')  # DocumentReference
    await post1.save(doc_id='post1')

    post2 = posts.new()
    post2.title = 'Second Post'
    post2.content = 'More content'
    post2.author = users.doc('bob')  # DocumentReference
    await post2.save(doc_id='post2')

    yield posts


@pytest.mark.asyncio
class TestProjectionsWithReferencesAsync:
    """Test async projections with DocumentReference fields."""

    async def test_select_converts_reference_to_asyncfireobject(self, async_test_collection_with_refs):
        """Test that DocumentReferences in projections are converted to AsyncFireObjects."""
        query = async_test_collection_with_refs.select('title', 'author')
        results = await query.get()

        assert len(results) == 2
        for result in results:
            assert isinstance(result, dict)
            assert 'title' in result
            assert 'author' in result

            # Author should be an AsyncFireObject, not a DocumentReference
            from src.fire_prox.async_fire_object import AsyncFireObject
            assert isinstance(result['author'], AsyncFireObject)
            # Should be in ATTACHED state
            assert result['author'].is_attached()
            # Can be fetched
            await result['author'].fetch()
            assert result['author'].is_loaded()
            assert hasattr(result['author'], 'name')

    async def test_select_reference_field_only(self, async_test_collection_with_refs):
        """Test selecting only a reference field."""
        query = async_test_collection_with_refs.select('author')
        results = await query.get()

        assert len(results) == 2
        for result in results:
            assert isinstance(result, dict)
            assert set(result.keys()) == {'author'}

            from src.fire_prox.async_fire_object import AsyncFireObject
            assert isinstance(result['author'], AsyncFireObject)

    async def test_select_with_stream_converts_references(self, async_test_collection_with_refs):
        """Test that stream() also converts DocumentReferences."""
        query = async_test_collection_with_refs.select('title', 'author')

        count = 0
        async for result in query.stream():
            assert isinstance(result, dict)
            assert 'author' in result

            from src.fire_prox.async_fire_object import AsyncFireObject
            assert isinstance(result['author'], AsyncFireObject)
            count += 1

        assert count == 2
