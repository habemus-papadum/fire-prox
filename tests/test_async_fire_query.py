"""
Integration tests for AsyncFireQuery (Phase 2.5, asynchronous).

Tests the async chainable query builder for Firestore collections against
the Firestore emulator.
"""

import pytest
from src.fire_prox.testing import async_testing_client
from src.fire_prox import AsyncFireProx


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
