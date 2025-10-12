"""
Unit tests for document reference support in FireProx.

Tests Phase 4 Part 1: FireObject/AsyncFireObject as references.
"""

import pytest

from fire_prox.state import State

# =========================================================================
# Basic Reference Assignment Tests (Sync)
# =========================================================================

class TestBasicReferenceAssignment:
    """Test basic FireObject reference assignment."""

    def test_assign_fireobject_to_property(self, db):
        """Test assigning a FireObject creates a DocumentReference."""
        users = db.collection('users')
        posts = db.collection('posts')

        # Create user
        user = users.new()
        user.name = 'Ada Lovelace'
        user.save(doc_id='ada')

        # Create post with reference to user
        post = posts.new()
        post.title = 'My Post'
        post.author = user  # Assign FireObject

        # Verify it's stored as DocumentReference
        assert hasattr(post._data['author'], 'path')
        assert post._data['author'].path == 'users/ada'

    def test_read_reference_back_as_fireobject(self, db):
        """Test reading a reference field returns a FireObject."""
        users = db.collection('users')
        posts = db.collection('posts')

        # Create and save user
        user = users.new()
        user.name = 'Ada Lovelace'
        user.save(doc_id='ada')

        # Create and save post with reference
        post = posts.new()
        post.title = 'My Post'
        post.author = user
        post.save(doc_id='post1')

        # Read back
        retrieved = db.doc('posts/post1')
        retrieved.fetch()

        # Access author - should be FireObject
        author = retrieved.author
        assert hasattr(author, '_doc_ref')
        assert author.path == 'users/ada'
        assert author.state == State.ATTACHED

    def test_lazy_load_referenced_document(self, db):
        """Test lazy loading a referenced document."""
        users = db.collection('users')
        posts = db.collection('posts')

        # Create user
        user = users.new()
        user.name = 'Ada Lovelace'
        user.year = 1815
        user.save(doc_id='ada')

        # Create post with reference
        post = posts.new()
        post.title = 'My Post'
        post.author = user
        post.save(doc_id='post1')

        # Read back
        retrieved = db.doc('posts/post1')
        retrieved.fetch()

        # Access referenced document's data (triggers lazy load)
        assert retrieved.author.name == 'Ada Lovelace'
        assert retrieved.author.year == 1815
        assert retrieved.author.state == State.LOADED


# =========================================================================
# Validation Tests
# =========================================================================

class TestReferenceValidation:
    """Test validation of FireObject references."""

    def test_detached_object_raises_error(self, db):
        """Test that DETACHED objects cannot be assigned as references."""
        collection = db.collection('doc_ref_test')

        # Create two DETACHED objects
        doc1 = collection.new()
        doc1.name = 'Doc 1'

        doc2 = collection.new()
        doc2.name = 'Doc 2'

        # Try to assign DETACHED object as reference
        with pytest.raises(ValueError, match="Cannot assign a DETACHED FireObject"):
            doc1.ref = doc2

    @pytest.mark.asyncio
    async def test_sync_async_mismatch_raises_error(self, db, async_db):
        """Test that mixing sync and async objects raises TypeError."""
        sync_collection = db.collection('doc_ref_test')
        async_collection = async_db.collection('doc_ref_test')

        # Create sync object
        sync_doc = sync_collection.new()
        sync_doc.name = 'Sync'
        sync_doc.save(doc_id='sync1')

        # Create async object and save it
        async_doc = async_collection.new()
        async_doc.name = 'Async'
        await async_doc.save(doc_id='async1')

        # Try to assign async to sync
        with pytest.raises(TypeError, match="Cannot assign async FireObject to sync"):
            sync_doc.ref = async_doc

    def test_attached_object_allowed(self, db):
        """Test that ATTACHED objects can be assigned as references."""
        collection = db.collection('doc_ref_test')

        # Create and save first document
        doc1 = collection.new()
        doc1.name = 'Doc 1'
        doc1.save(doc_id='doc1')

        # Get ATTACHED reference to it
        doc1_attached = db.doc('doc_ref_test/doc1')
        assert doc1_attached.state == State.ATTACHED

        # Create second document and assign reference
        doc2 = collection.new()
        doc2.name = 'Doc 2'
        doc2.ref = doc1_attached  # Should work

        # Verify
        assert doc2._data['ref'].path == 'doc_ref_test/doc1'

    def test_loaded_object_allowed(self, db):
        """Test that LOADED objects can be assigned as references."""
        collection = db.collection('doc_ref_test')

        # Create and save first document
        doc1 = collection.new()
        doc1.name = 'Doc 1'
        doc1.save(doc_id='doc1')

        # Fetch to make it LOADED
        doc1.fetch()
        assert doc1.state == State.LOADED

        # Create second document and assign reference
        doc2 = collection.new()
        doc2.name = 'Doc 2'
        doc2.ref = doc1  # Should work

        # Verify
        assert doc2._data['ref'].path == 'doc_ref_test/doc1'


# =========================================================================
# Nested Reference Tests
# =========================================================================

class TestNestedReferences:
    """Test references nested in lists and dicts."""

    def test_references_in_list(self, db):
        """Test storing references in a list."""
        users = db.collection('users')
        posts = db.collection('posts')

        # Create multiple users
        user1 = users.new()
        user1.name = 'Ada'
        user1.save(doc_id='ada')

        user2 = users.new()
        user2.name = 'Grace'
        user2.save(doc_id='grace')

        user3 = users.new()
        user3.name = 'Margaret'
        user3.save(doc_id='margaret')

        # Create post with list of reviewers
        post = posts.new()
        post.title = 'Research Paper'
        post.reviewers = [user1, user2, user3]
        post.save(doc_id='paper1')

        # Read back
        retrieved = db.doc('posts/paper1')
        retrieved.fetch()

        # Verify list of references
        reviewers = retrieved.reviewers
        assert len(reviewers) == 3
        assert all(hasattr(r, '_doc_ref') for r in reviewers)
        assert reviewers[0].path == 'users/ada'
        assert reviewers[1].path == 'users/grace'
        assert reviewers[2].path == 'users/margaret'

        # Verify lazy loading works
        assert reviewers[0].name == 'Ada'
        assert reviewers[1].name == 'Grace'
        assert reviewers[2].name == 'Margaret'

    def test_references_in_dict(self, db):
        """Test storing references in a dictionary."""
        users = db.collection('users')
        posts = db.collection('posts')

        # Create users
        author = users.new()
        author.name = 'Ada'
        author.save(doc_id='ada')

        editor = users.new()
        editor.name = 'Grace'
        editor.save(doc_id='grace')

        # Create post with dict of references
        post = posts.new()
        post.title = 'Article'
        post.contributors = {
            'author': author,
            'editor': editor
        }
        post.save(doc_id='article1')

        # Read back
        retrieved = db.doc('posts/article1')
        retrieved.fetch()

        # Verify dict of references
        contributors = retrieved.contributors
        assert 'author' in contributors
        assert 'editor' in contributors
        assert contributors['author'].path == 'users/ada'
        assert contributors['editor'].path == 'users/grace'

        # Verify lazy loading works
        assert contributors['author'].name == 'Ada'
        assert contributors['editor'].name == 'Grace'

    def test_mixed_nested_structures(self, db):
        """Test references in complex nested structures."""
        users = db.collection('users')
        posts = db.collection('posts')

        # Create users
        user1 = users.new()
        user1.name = 'Ada'
        user1.save(doc_id='ada')

        user2 = users.new()
        user2.name = 'Grace'
        user2.save(doc_id='grace')

        # Create post with complex nesting
        post = posts.new()
        post.title = 'Complex Document'
        post.metadata = {
            'primary': user1,
            'secondary': [user2],
            'group': {
                'lead': user1,
                'members': [user1, user2]
            }
        }
        post.save(doc_id='complex1')

        # Read back
        retrieved = db.doc('posts/complex1')
        retrieved.fetch()

        # Verify nested references
        meta = retrieved.metadata
        assert meta['primary'].path == 'users/ada'
        assert meta['secondary'][0].path == 'users/grace'
        assert meta['group']['lead'].path == 'users/ada'
        assert len(meta['group']['members']) == 2

        # Verify lazy loading
        assert meta['primary'].name == 'Ada'
        assert meta['secondary'][0].name == 'Grace'

    def test_empty_list_and_dict(self, db):
        """Test empty lists and dicts don't cause issues."""
        collection = db.collection('doc_ref_test')

        doc = collection.new()
        doc.empty_list = []
        doc.empty_dict = {}
        doc.save(doc_id='empty1')

        # Read back
        retrieved = db.doc('doc_ref_test/empty1')
        retrieved.fetch()

        assert retrieved.empty_list == []
        assert retrieved.empty_dict == {}

    def test_none_values_pass_through(self, db):
        """Test that None values are handled correctly."""
        collection = db.collection('doc_ref_test')

        doc = collection.new()
        doc.nullable_ref = None
        doc.nullable_list = [None, None]
        doc.nullable_dict = {'key': None}
        doc.save(doc_id='none1')

        # Read back
        retrieved = db.doc('doc_ref_test/none1')
        retrieved.fetch()

        assert retrieved.nullable_ref is None
        assert retrieved.nullable_list == [None, None]
        assert retrieved.nullable_dict == {'key': None}


# =========================================================================
# Async Tests
# =========================================================================

class TestAsyncReferences:
    """Test document references with async API."""

    @pytest.mark.asyncio
    async def test_async_basic_reference(self, async_db):
        """Test basic reference assignment with async."""
        users = async_db.collection('users')
        posts = async_db.collection('posts')

        # Create user
        user = users.new()
        user.name = 'Ada'
        await user.save(doc_id='ada')

        # Create post with reference
        post = posts.new()
        post.title = 'Async Post'
        post.author = user
        await post.save(doc_id='post1')

        # Read back
        retrieved = async_db.doc('posts/post1')
        await retrieved.fetch()

        # Verify
        author = retrieved.author
        assert author.path == 'users/ada'
        assert author.name == 'Ada'

    @pytest.mark.asyncio
    async def test_async_list_of_references(self, async_db):
        """Test list of references with async."""
        users = async_db.collection('users')
        posts = async_db.collection('posts')

        # Create users
        user1 = users.new()
        user1.name = 'Ada'
        await user1.save(doc_id='ada')

        user2 = users.new()
        user2.name = 'Grace'
        await user2.save(doc_id='grace')

        # Create post with references
        post = posts.new()
        post.title = 'Collaborative Post'
        post.authors = [user1, user2]
        await post.save(doc_id='collab1')

        # Read back
        retrieved = async_db.doc('posts/collab1')
        await retrieved.fetch()

        # Verify
        authors = retrieved.authors
        assert len(authors) == 2
        assert authors[0].name == 'Ada'
        assert authors[1].name == 'Grace'

    @pytest.mark.asyncio
    async def test_async_detached_raises_error(self, async_db):
        """Test DETACHED async object raises error."""
        collection = async_db.collection('doc_ref_test')

        doc1 = collection.new()
        doc1.name = 'Doc 1'

        doc2 = collection.new()
        doc2.name = 'Doc 2'

        # Try to assign DETACHED
        with pytest.raises(ValueError, match="Cannot assign a DETACHED FireObject"):
            doc1.ref = doc2


# =========================================================================
# Edge Cases and Integration Tests
# =========================================================================

class TestReferenceEdgeCases:
    """Test edge cases for document references."""

    def test_raw_document_reference_passthrough(self, db):
        """Test that raw DocumentReference objects pass through."""
        users = db.collection('users')
        posts = db.collection('posts')

        # Create user
        user = users.new()
        user.name = 'Ada'
        user.save(doc_id='ada')

        # Get native DocumentReference
        native_ref = user._doc_ref

        # Create post and assign raw reference
        post = posts.new()
        post.title = 'Post'
        post.author = native_ref  # Assign raw DocumentReference
        post.save(doc_id='post1')

        # Read back
        retrieved = db.doc('posts/post1')
        retrieved.fetch()

        # Should still work
        assert retrieved.author.path == 'users/ada'
        assert retrieved.author.name == 'Ada'

    def test_deeply_nested_references(self, db):
        """Test deeply nested reference structures."""
        users = db.collection('users')
        collection = db.collection('doc_ref_test')

        # Create user
        user = users.new()
        user.name = 'Ada'
        user.save(doc_id='ada')

        # Create deeply nested structure
        doc = collection.new()
        doc.level1 = {
            'level2': {
                'level3': {
                    'ref': user
                }
            }
        }
        doc.save(doc_id='deep1')

        # Read back
        retrieved = db.doc('doc_ref_test/deep1')
        retrieved.fetch()

        # Verify deep access works
        ref = retrieved.level1['level2']['level3']['ref']
        assert ref.path == 'users/ada'
        assert ref.name == 'Ada'

    def test_reference_in_query_results(self, db):
        """Test references work in query results."""
        users = db.collection('users')
        posts = db.collection('posts')

        # Create user
        user = users.new()
        user.name = 'Ada'
        user.save(doc_id='ada')

        # Create multiple posts with references
        for i in range(3):
            post = posts.new()
            post.title = f'Post {i}'
            post.author = user
            post.save(doc_id=f'post{i}')

        # Query for posts
        results = list(posts.get_all())

        # Verify all have references
        assert len(results) == 3
        for post in results:
            assert post.author.path == 'users/ada'
            assert post.author.name == 'Ada'

    def test_update_reference_field(self, db):
        """Test updating a reference field."""
        users = db.collection('users')
        posts = db.collection('posts')

        # Create users
        user1 = users.new()
        user1.name = 'Ada'
        user1.save(doc_id='ada')

        user2 = users.new()
        user2.name = 'Grace'
        user2.save(doc_id='grace')

        # Create post with reference
        post = posts.new()
        post.title = 'Post'
        post.author = user1
        post.save(doc_id='post1')

        # Update reference
        post.author = user2
        post.save()

        # Read back
        retrieved = db.doc('posts/post1')
        retrieved.fetch()

        # Verify updated
        assert retrieved.author.path == 'users/grace'
        assert retrieved.author.name == 'Grace'

    def test_reference_to_dict(self, db):
        """Test to_dict() with references."""
        users = db.collection('users')
        posts = db.collection('posts')

        # Create user
        user = users.new()
        user.name = 'Ada'
        user.save(doc_id='ada')

        # Create post with reference
        post = posts.new()
        post.title = 'Post'
        post.author = user
        post.save(doc_id='post1')

        # Get as dict
        post_dict = post.to_dict()

        # Should have DocumentReference in dict
        assert 'author' in post_dict
        assert hasattr(post_dict['author'], 'path')
        assert post_dict['author'].path == 'users/ada'
