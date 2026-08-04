import unittest
from unittest.mock import patch

from app.db import vector_store


class SeedSchemaDescriptionsTests(unittest.IsolatedAsyncioTestCase):
    async def test_seed_schema_descriptions_handles_initialization_failure(self) -> None:
        with (
            patch.object(
                vector_store,
                "_load_table_descriptions",
                return_value=[{"table": "users", "description": "user table"}],
            ),
            patch.object(vector_store, "get_vector_store", side_effect=RuntimeError("boom")),
        ):
            result = await vector_store.seed_schema_descriptions()

        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
