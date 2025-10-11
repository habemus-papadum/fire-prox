import unittest
from unittest.mock import Mock
from ..collection import FireCollection
from ..fire_object import FireObject
from ..state import State


class TestFireCollection(unittest.TestCase):

    def test_initialization(self):
        mock_collection_ref = Mock()
        fire_collection = FireCollection(collection_ref=mock_collection_ref)
        self.assertIs(fire_collection._collection_ref, mock_collection_ref)

    def test_new(self):
        mock_collection_ref = Mock()
        fire_collection = FireCollection(collection_ref=mock_collection_ref)
        new_obj = fire_collection.new()
        self.assertIsInstance(new_obj, FireObject)
        self.assertEqual(new_obj.state, State.DETACHED)
        self.assertIs(new_obj._collection_ref, mock_collection_ref)


if __name__ == '__main__':
    unittest.main()
