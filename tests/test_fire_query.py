"""
Integration tests for FireQuery (Phase 2.5, synchronous).

Tests the chainable query builder for Firestore collections against
the Firestore emulator.
"""

import pytest
from src.fire_prox.testing import testing_client
from src.fire_prox import FireProx


@pytest.fixture
def db():
    """Create a FireProx instance connected to the emulator."""
    client = testing_client()
    return FireProx(client)


@pytest.fixture
def test_collection(db):
    """Return a test collection with sample data."""
    collection = db.collection('query_test_collection')

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
        doc.save(doc_id=f'user{i+1}')

    yield collection


class TestBasicQueries:
    """Test basic query operations."""

    def test_where_single_condition(self, test_collection):
        """Test simple where clause with single condition."""
        # Query for users born after 1900
        query = test_collection.where('birth_year', '>', 1900)
        results = query.get()

        assert len(results) == 3  # John (1903), Grace (1906), Alan (1912)
        years = {user.birth_year for user in results}
        assert years == {1903, 1906, 1912}

    def test_where_equality(self, test_collection):
        """Test where clause with equality operator."""
        # Query for users from England
        query = test_collection.where('country', '==', 'England')
        results = query.get()

        assert len(results) == 3  # Ada, Charles, Alan
        for user in results:
            assert user.country == 'England'

    def test_where_less_than(self, test_collection):
        """Test where clause with less than operator."""
        # Query for users born before 1850
        query = test_collection.where('birth_year', '<', 1850)
        results = query.get()

        assert len(results) == 2  # Ada and Charles
        for user in results:
            assert user.birth_year < 1850

    def test_where_greater_or_equal(self, test_collection):
        """Test where clause with >= operator."""
        # Query for users with score >= 95
        query = test_collection.where('score', '>=', 95)
        results = query.get()

        assert len(results) == 3  # Ada (95), Alan (98), John (97)
        for user in results:
            assert user.score >= 95

    def test_where_not_equal(self, test_collection):
        """Test where clause with != operator."""
        # Query for users not from England
        query = test_collection.where('country', '!=', 'England')
        results = query.get()

        assert len(results) == 2  # Grace and John
        for user in results:
            assert user.country != 'England'


class TestChainedQueries:
    """Test chaining multiple query operations."""

    def test_multiple_where_conditions(self, test_collection):
        """Test chaining multiple where clauses."""
        # Query for English users born after 1850
        query = (test_collection
                 .where('country', '==', 'England')
                 .where('birth_year', '>', 1850))
        results = query.get()

        assert len(results) == 1  # Only Alan (1912) - Ada was born in 1815
        for user in results:
            assert user.country == 'England'
            assert user.birth_year > 1850

    def test_where_with_order_by(self, test_collection):
        """Test combining where and order_by."""
        # Query for users born after 1800, ordered by birth year
        query = (test_collection
                 .where('birth_year', '>', 1800)
                 .order_by('birth_year'))
        results = query.get()

        # Should be ordered: Ada (1815), John (1903), Grace (1906), Alan (1912)
        assert len(results) == 4
        years = [user.birth_year for user in results]
        assert years == sorted(years)  # Verify ascending order

    def test_where_order_by_limit(self, test_collection):
        """Test chaining where, order_by, and limit."""
        # Get top 2 scorers from England
        query = (test_collection
                 .where('country', '==', 'England')
                 .order_by('score', direction='DESCENDING')
                 .limit(2))
        results = query.get()

        assert len(results) == 2
        # Should be Alan (98) and Ada (95)
        assert results[0].score == 98
        assert results[1].score == 95


class TestOrderBy:
    """Test ordering query results."""

    def test_order_by_ascending(self, test_collection):
        """Test ordering results in ascending order."""
        query = test_collection.order_by('birth_year')
        results = query.get()

        years = [user.birth_year for user in results]
        assert years == sorted(years)

    def test_order_by_descending(self, test_collection):
        """Test ordering results in descending order."""
        query = test_collection.order_by('birth_year', direction='DESCENDING')
        results = query.get()

        years = [user.birth_year for user in results]
        assert years == sorted(years, reverse=True)

    def test_order_by_multiple_fields(self, test_collection):
        """Test ordering by multiple fields."""
        # Order by country, then by birth_year
        query = (test_collection
                 .order_by('country')
                 .order_by('birth_year'))
        results = query.get()

        # Results should be grouped by country and ordered by year within each group
        assert len(results) == 5
        # Verify England group is ordered correctly
        england_users = [u for u in results if u.country == 'England']
        england_years = [u.birth_year for u in england_users]
        assert england_years == sorted(england_years)

    def test_order_by_invalid_direction_raises_error(self, test_collection):
        """Test that invalid direction raises ValueError."""
        with pytest.raises(ValueError, match="Invalid direction"):
            test_collection.order_by('birth_year', direction='INVALID')


class TestLimit:
    """Test limiting query results."""

    def test_limit_results(self, test_collection):
        """Test limiting the number of results."""
        query = test_collection.limit(3)
        results = query.get()

        assert len(results) == 3

    def test_limit_with_order_by(self, test_collection):
        """Test limit combined with ordering."""
        # Get 2 oldest users
        query = (test_collection
                 .order_by('birth_year')
                 .limit(2))
        results = query.get()

        assert len(results) == 2
        assert results[0].birth_year == 1791  # Charles
        assert results[1].birth_year == 1815  # Ada

    def test_limit_zero_raises_error(self, test_collection):
        """Test that limit(0) raises ValueError."""
        with pytest.raises(ValueError, match="Limit count must be positive"):
            test_collection.limit(0)

    def test_limit_negative_raises_error(self, test_collection):
        """Test that negative limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit count must be positive"):
            test_collection.limit(-1)


class TestQueryExecution:
    """Test different query execution methods."""

    def test_get_returns_list(self, test_collection):
        """Test that get() returns a list of FireObjects."""
        query = test_collection.where('country', '==', 'England')
        results = query.get()

        assert isinstance(results, list)
        assert len(results) > 0
        for obj in results:
            assert obj.is_loaded()
            assert hasattr(obj, 'name')

    def test_stream_returns_iterator(self, test_collection):
        """Test that stream() returns an iterator."""
        query = test_collection.where('country', '==', 'England')
        results = query.stream()

        # Should be an iterator/generator
        count = 0
        for obj in results:
            assert obj.is_loaded()
            assert hasattr(obj, 'name')
            count += 1

        assert count == 3

    def test_empty_query_returns_empty_list(self, test_collection):
        """Test that query with no matches returns empty list."""
        query = test_collection.where('birth_year', '>', 2000)
        results = query.get()

        assert results == []

    def test_get_all_returns_all_documents(self, test_collection):
        """Test that get_all() returns all documents in collection."""
        results = list(test_collection.get_all())

        assert len(results) == 5  # All 5 sample users
        for obj in results:
            assert obj.is_loaded()


class TestImmutableQueryPattern:
    """Test that queries follow immutable pattern."""

    def test_where_returns_new_instance(self, test_collection):
        """Test that where() returns a new FireQuery instance."""
        query1 = test_collection.where('country', '==', 'England')
        query2 = query1.where('birth_year', '>', 1850)

        # query2 should have different results than query1
        results1 = query1.get()
        results2 = query2.get()

        assert len(results1) > len(results2)

    def test_order_by_returns_new_instance(self, test_collection):
        """Test that order_by() returns a new FireQuery instance."""
        query1 = test_collection.where('country', '==', 'England')
        query2 = query1.order_by('birth_year')

        # Both should have same count but query2 is ordered
        results1 = query1.get()
        results2 = query2.get()

        assert len(results1) == len(results2)

    def test_limit_returns_new_instance(self, test_collection):
        """Test that limit() returns a new FireQuery instance."""
        query1 = test_collection.where('country', '==', 'England')
        query2 = query1.limit(2)

        # query2 should have fewer results
        results1 = query1.get()
        results2 = query2.get()

        assert len(results1) > len(results2)
        assert len(results2) == 2


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_query_on_empty_collection(self, db):
        """Test querying an empty collection."""
        empty_collection = db.collection('empty_collection')
        query = empty_collection.where('field', '==', 'value')
        results = query.get()

        assert results == []

    def test_query_with_nonexistent_field(self, test_collection):
        """Test querying for a field that doesn't exist."""
        query = test_collection.where('nonexistent_field', '==', 'value')
        results = query.get()

        # Should return empty results, not error
        assert results == []

    def test_stream_can_be_consumed_once(self, test_collection):
        """Test that stream iterator can only be consumed once."""
        query = test_collection.where('country', '==', 'England')
        stream = query.stream()

        # Consume the stream
        first_consumption = list(stream)
        assert len(first_consumption) == 3

        # Try to consume again - should be empty
        second_consumption = list(stream)
        assert len(second_consumption) == 0


class TestQueryPagination:
    """Test cursor-based pagination with start_at, start_after, end_at, end_before."""

    def test_start_at_with_field_value(self, test_collection):
        """Test start_at with field value dictionary (inclusive)."""
        # Order by birth_year: Charles (1791), Ada (1815), John (1903), Grace (1906), Alan (1912)
        # Start at 1903 (inclusive) - should include John, Grace, Alan
        query = (test_collection
                 .order_by('birth_year')
                 .start_at({'birth_year': 1903}))
        results = query.get()

        assert len(results) == 3
        years = [user.birth_year for user in results]
        assert years == [1903, 1906, 1912]
        assert results[0].name == 'John von Neumann'
        assert results[1].name == 'Grace Hopper'
        assert results[2].name == 'Alan Turing'

    def test_start_after_excludes_cursor(self, test_collection):
        """Test start_after excludes the cursor document (exclusive)."""
        # Order by birth_year: Charles (1791), Ada (1815), John (1903), Grace (1906), Alan (1912)
        # Start after 1903 (exclusive) - should include Grace, Alan only
        query = (test_collection
                 .order_by('birth_year')
                 .start_after({'birth_year': 1903}))
        results = query.get()

        assert len(results) == 2
        years = [user.birth_year for user in results]
        assert years == [1906, 1912]
        assert results[0].name == 'Grace Hopper'
        assert results[1].name == 'Alan Turing'

    def test_end_at_with_field_value(self, test_collection):
        """Test end_at with field value dictionary (inclusive)."""
        # Order by birth_year: Charles (1791), Ada (1815), John (1903), Grace (1906), Alan (1912)
        # End at 1903 (inclusive) - should include Charles, Ada, John
        query = (test_collection
                 .order_by('birth_year')
                 .end_at({'birth_year': 1903}))
        results = query.get()

        assert len(results) == 3
        years = [user.birth_year for user in results]
        assert years == [1791, 1815, 1903]
        assert results[0].name == 'Charles Babbage'
        assert results[1].name == 'Ada Lovelace'
        assert results[2].name == 'John von Neumann'

    def test_end_before_excludes_cursor(self, test_collection):
        """Test end_before excludes the cursor document (exclusive)."""
        # Order by birth_year: Charles (1791), Ada (1815), John (1903), Grace (1906), Alan (1912)
        # End before 1903 (exclusive) - should include Charles, Ada only
        query = (test_collection
                 .order_by('birth_year')
                 .end_before({'birth_year': 1903}))
        results = query.get()

        assert len(results) == 2
        years = [user.birth_year for user in results]
        assert years == [1791, 1815]
        assert results[0].name == 'Charles Babbage'
        assert results[1].name == 'Ada Lovelace'

    def test_pagination_chain(self, test_collection):
        """Test typical pagination pattern: order_by + limit + start_after."""
        # Simulate pagination: get first page, then get next page

        # Page 1: Get first 2 users ordered by birth year
        page1_query = (test_collection
                      .order_by('birth_year')
                      .limit(2))
        page1_results = page1_query.get()

        assert len(page1_results) == 2
        assert page1_results[0].birth_year == 1791  # Charles
        assert page1_results[1].birth_year == 1815  # Ada

        # Page 2: Start after the last document from page 1
        last_year = page1_results[-1].birth_year
        page2_query = (test_collection
                      .order_by('birth_year')
                      .start_after({'birth_year': last_year})
                      .limit(2))
        page2_results = page2_query.get()

        assert len(page2_results) == 2
        assert page2_results[0].birth_year == 1903  # John
        assert page2_results[1].birth_year == 1906  # Grace

        # Page 3: Start after the last document from page 2
        last_year = page2_results[-1].birth_year
        page3_query = (test_collection
                      .order_by('birth_year')
                      .start_after({'birth_year': last_year})
                      .limit(2))
        page3_results = page3_query.get()

        assert len(page3_results) == 1  # Only Alan left
        assert page3_results[0].birth_year == 1912  # Alan

    def test_cursor_with_snapshot(self, test_collection):
        """Test using DocumentSnapshot as cursor instead of field values."""
        # Get all users ordered by birth year
        query = test_collection.order_by('birth_year')
        all_results = query.get()

        # Get the document reference for the middle user (John, 1903)
        john = [u for u in all_results if u.birth_year == 1903][0]
        john_ref = john._doc_ref
        john_snapshot = john_ref.get()

        # Use snapshot as cursor for start_after
        query_after = (test_collection
                      .order_by('birth_year')
                      .start_after(john_snapshot))
        results_after = query_after.get()

        # Should get Grace (1906) and Alan (1912)
        assert len(results_after) == 2
        assert results_after[0].birth_year == 1906
        assert results_after[1].birth_year == 1912

        # Use snapshot as cursor for end_at
        query_end = (test_collection
                    .order_by('birth_year')
                    .end_at(john_snapshot))
        results_end = query_end.get()

        # Should get Charles (1791), Ada (1815), John (1903)
        assert len(results_end) == 3
        assert results_end[0].birth_year == 1791
        assert results_end[1].birth_year == 1815
        assert results_end[2].birth_year == 1903

    def test_range_query_with_start_and_end(self, test_collection):
        """Test combining start_at and end_at for range queries."""
        # Get users between 1815 and 1906 (inclusive)
        query = (test_collection
                .order_by('birth_year')
                .start_at({'birth_year': 1815})
                .end_at({'birth_year': 1906}))
        results = query.get()

        assert len(results) == 3
        years = [user.birth_year for user in results]
        assert years == [1815, 1903, 1906]
        assert results[0].name == 'Ada Lovelace'
        assert results[1].name == 'John von Neumann'
        assert results[2].name == 'Grace Hopper'

    def test_descending_order_with_pagination(self, test_collection):
        """Test pagination works with descending order."""
        # Order descending: Alan (1912), Grace (1906), John (1903), Ada (1815), Charles (1791)
        # Get first 2, then continue from there
        page1_query = (test_collection
                      .order_by('birth_year', direction='DESCENDING')
                      .limit(2))
        page1_results = page1_query.get()

        assert len(page1_results) == 2
        assert page1_results[0].birth_year == 1912  # Alan
        assert page1_results[1].birth_year == 1906  # Grace

        # Continue after Grace (1906)
        page2_query = (test_collection
                      .order_by('birth_year', direction='DESCENDING')
                      .start_after({'birth_year': 1906})
                      .limit(2))
        page2_results = page2_query.get()

        assert len(page2_results) == 2
        assert page2_results[0].birth_year == 1903  # John
        assert page2_results[1].birth_year == 1815  # Ada


class TestProjections:
    """Test query projections with .select() method."""

    def test_select_single_field(self, test_collection):
        """Test selecting a single field returns dictionaries."""
        # Select only the name field
        query = test_collection.select('name')
        results = query.get()

        assert len(results) == 5
        # Results should be dictionaries, not FireObjects
        for result in results:
            assert isinstance(result, dict)
            assert 'name' in result
            # Only the selected field should be present
            assert set(result.keys()) == {'name'}

    def test_select_multiple_fields(self, test_collection):
        """Test selecting multiple fields."""
        # Select name and birth_year
        query = test_collection.select('name', 'birth_year')
        results = query.get()

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

    def test_select_with_where_filter(self, test_collection):
        """Test combining select with where clause."""
        # Select name and score for English users
        query = (test_collection
                 .where('country', '==', 'England')
                 .select('name', 'score'))
        results = query.get()

        assert len(results) == 3  # Ada, Charles, Alan
        for result in results:
            assert isinstance(result, dict)
            assert set(result.keys()) == {'name', 'score'}
            assert result['score'] >= 90

    def test_select_with_order_by(self, test_collection):
        """Test combining select with order_by."""
        # Select name and birth_year, ordered by birth_year
        query = (test_collection
                 .select('name', 'birth_year')
                 .order_by('birth_year'))
        results = query.get()

        assert len(results) == 5
        # Verify ordering
        years = [r['birth_year'] for r in results]
        assert years == sorted(years)
        # Verify only selected fields present
        for result in results:
            assert set(result.keys()) == {'name', 'birth_year'}

    def test_select_with_limit(self, test_collection):
        """Test combining select with limit."""
        # Select name for first 3 users
        query = (test_collection
                 .select('name')
                 .order_by('birth_year')
                 .limit(3))
        results = query.get()

        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)
            assert 'name' in result
            assert set(result.keys()) == {'name'}

    def test_select_stream_returns_dicts(self, test_collection):
        """Test that select with stream() yields dictionaries."""
        query = test_collection.select('name', 'country')
        results = []

        for result in query.stream():
            assert isinstance(result, dict)
            assert set(result.keys()) == {'name', 'country'}
            results.append(result)

        assert len(results) == 5

    def test_select_no_fields_raises_error(self, test_collection):
        """Test that select() with no fields raises ValueError."""
        with pytest.raises(ValueError, match="select\\(\\) requires at least one field"):
            test_collection.select()

    def test_select_returns_new_query_instance(self, test_collection):
        """Test that select() follows immutable pattern."""
        query1 = test_collection.where('country', '==', 'England')
        query2 = query1.select('name')

        # query1 should still return FireObjects
        results1 = query1.get()
        assert len(results1) == 3
        for result in results1:
            assert hasattr(result, 'name')  # FireObject
            assert hasattr(result, 'is_loaded')

        # query2 should return dictionaries
        results2 = query2.get()
        assert len(results2) == 3
        for result in results2:
            assert isinstance(result, dict)
            assert set(result.keys()) == {'name'}

    def test_select_with_chaining(self, test_collection):
        """Test complex query chain with select."""
        # Complex chain: where + select + order_by + limit
        query = (test_collection
                 .where('birth_year', '>', 1850)
                 .select('name', 'birth_year', 'score')
                 .order_by('score', direction='DESCENDING')
                 .limit(2))
        results = query.get()

        assert len(results) == 2
        # Should be Alan (98) and John (97)
        assert results[0]['score'] == 98
        assert results[1]['score'] == 97
        # Verify only selected fields
        for result in results:
            assert set(result.keys()) == {'name', 'birth_year', 'score'}

    def test_select_empty_results(self, test_collection):
        """Test select with query that returns no results."""
        query = (test_collection
                 .where('birth_year', '>', 2000)
                 .select('name'))
        results = query.get()

        assert results == []


@pytest.fixture
def test_collection_with_refs(db):
    """Create test collection with DocumentReference fields."""
    # Create users collection
    users = db.collection('projection_users')
    user1 = users.new()
    user1.name = 'Alice'
    user1.email = 'alice@example.com'
    user1.save(doc_id='alice')

    user2 = users.new()
    user2.name = 'Bob'
    user2.email = 'bob@example.com'
    user2.save(doc_id='bob')

    # Create posts collection with author references
    posts = db.collection('projection_posts')

    post1 = posts.new()
    post1.title = 'First Post'
    post1.content = 'Hello World'
    post1.author = users.doc('alice')  # DocumentReference
    post1.save(doc_id='post1')

    post2 = posts.new()
    post2.title = 'Second Post'
    post2.content = 'More content'
    post2.author = users.doc('bob')  # DocumentReference
    post2.save(doc_id='post2')

    yield posts


class TestProjectionsWithReferences:
    """Test projections with DocumentReference fields."""

    def test_select_converts_reference_to_fireobject(self, test_collection_with_refs):
        """Test that DocumentReferences in projections are converted to FireObjects."""
        query = test_collection_with_refs.select('title', 'author')
        results = query.get()

        assert len(results) == 2
        for result in results:
            assert isinstance(result, dict)
            assert 'title' in result
            assert 'author' in result

            # Author should be a FireObject, not a DocumentReference
            from src.fire_prox.fire_object import FireObject
            assert isinstance(result['author'], FireObject)
            # Should be in ATTACHED state
            assert result['author'].is_attached()
            # Can be fetched
            result['author'].fetch()
            assert result['author'].is_loaded()
            assert hasattr(result['author'], 'name')

    def test_select_reference_field_only(self, test_collection_with_refs):
        """Test selecting only a reference field."""
        query = test_collection_with_refs.select('author')
        results = query.get()

        assert len(results) == 2
        for result in results:
            assert isinstance(result, dict)
            assert set(result.keys()) == {'author'}

            from src.fire_prox.fire_object import FireObject
            assert isinstance(result['author'], FireObject)

    def test_select_with_stream_converts_references(self, test_collection_with_refs):
        """Test that stream() also converts DocumentReferences."""
        query = test_collection_with_refs.select('title', 'author')

        count = 0
        for result in query.stream():
            assert isinstance(result, dict)
            assert 'author' in result

            from src.fire_prox.fire_object import FireObject
            assert isinstance(result['author'], FireObject)
            count += 1

        assert count == 2
