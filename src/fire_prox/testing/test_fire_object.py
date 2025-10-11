import unittest
import asyncio
from unittest.mock import Mock
from ..fire_object import FireObject
from ..state import State


class TestFireObject(unittest.TestCase):

    def test_initialization_detached(self):
        fire_obj = FireObject()
        self.assertEqual(fire_obj.state, State.DETACHED)
        self.assertIsNone(fire_obj._doc_ref)
        self.assertEqual(fire_obj._data, {})
        self.assertFalse(fire_obj.is_dirty())

    def test_initialization_attached(self):
        mock_doc_ref = Mock()
        fire_obj = FireObject(doc_ref=mock_doc_ref)
        self.assertEqual(fire_obj.state, State.ATTACHED)
        self.assertIs(fire_obj._doc_ref, mock_doc_ref)
        self.assertFalse(fire_obj.is_dirty())

    def test_attribute_access(self):
        fire_obj = FireObject()
        fire_obj.name = "test"
        self.assertEqual(fire_obj.name, "test")
        self.assertTrue(fire_obj.is_dirty())
        self.assertEqual(fire_obj._dirty_fields, {"name"})

    def test_state_inspection(self):
        fire_obj = FireObject()
        self.assertEqual(fire_obj.state, State.DETACHED)
        self.assertFalse(fire_obj.is_loaded())
        self.assertFalse(fire_obj.is_attached())
        self.assertFalse(fire_obj.is_deleted())

        mock_doc_ref = Mock()
        fire_obj_attached = FireObject(doc_ref=mock_doc_ref)
        self.assertEqual(fire_obj_attached.state, State.ATTACHED)
        self.assertTrue(fire_obj_attached.is_attached())

    def test_methods(self):
        fire_obj = FireObject()
        # In Phase 1, these methods are stubs and don't do anything.
        # We just need to ensure they can be called without errors.
        async def run():
            await fire_obj.fetch()
            await fire_obj.delete()
            await fire_obj.save()
        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
