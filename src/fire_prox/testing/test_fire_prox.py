import unittest
from unittest.mock import Mock, patch
from ..fire_prox import FireProx
from ..fire_object import FireObject
from ..collection import FireCollection


class TestFireProx(unittest.TestCase):

    def test_initialization(self):
        mock_client = Mock()
        fire_prox = FireProx(client=mock_client)
        self.assertIs(fire_prox._client, mock_client)

    @patch('fire_prox.fire_prox.FireObject')
    def test_doc(self, mock_fire_object):
        mock_client = Mock()
        fire_prox = FireProx(client=mock_client)
        fire_prox.doc('users/test')
        mock_client.document.assert_called_once_with('users/test')
        mock_fire_object.assert_called_once_with(doc_ref=mock_client.document.return_value)

    @patch('fire_prox.fire_prox.FireCollection')
    def test_collection(self, mock_fire_collection):
        mock_client = Mock()
        fire_prox = FireProx(client=mock_client)
        fire_prox.collection('users')
        mock_client.collection.assert_called_once_with('users')
        mock_fire_collection.assert_called_once_with(collection_ref=mock_client.collection.return_value)


if __name__ == '__main__':
    unittest.main()
