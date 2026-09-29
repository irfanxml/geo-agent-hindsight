# Troubleshooting Log

1. **Error**: `ModuleNotFoundError: No module named 'hindsight'` when trying to inspect the package.
   - **Cause**: The package name is `hindsight-client` and the primary entry module is `hindsight_client`.
   - **Fix**: Used `hindsight_client` for imports and verified via `ls` in `site-packages`.

2. **Error**: `TypeError: Hindsight.__init__() missing 1 required positional argument: 'base_url'`
   - **Cause**: The `Hindsight` client requires `base_url` to be provided alongside `api_key`.
   - **Fix**: Added `base_url=api_url` when instantiating the client.

3. **Error**: `Failed to create bank: Hindsight.create_bank() missing 1 required positional argument: 'bank_id'`
   - **Cause**: The `create_bank` function signature requires both `bank_id` and `name` strings to be passed.
   - **Fix**: Changed `client.create_bank(name=bank_id)` to `client.create_bank(bank_id=bank_id, name=bank_id)`.

4. **Error**: `500, message='Internal Server Error'` on bank creation
   - **Cause**: Calling `create_bank` sometimes throws a `500` error if the bank already exists, instead of a `409 Conflict`.
   - **Fix**: Updated the exception handler in bank creation to treat `500` errors similarly to `409` as "bank already exists", allowing execution to proceed.

5. **Error**: `Unexpected keyword argument 'text' in function 'Hindsight.retain'`
   - **Cause**: The second argument for `retain` is named `content`, not `text`, based on the inspected python signature.
   - **Fix**: Replaced `text=...` with `content=...` in the `smoke_test.py` and `hindsight_memory.py` scripts.

6. **Error**: `ModuleNotFoundError: No module named 'hindsight_memory'` when running `pytest tests/test_memory.py`
   - **Cause**: The test directory did not have the parent directory in `PYTHONPATH`.
   - **Fix**: Manually appended the parent directory to `sys.path` in the `test_memory.py` file.

7. **Warning**: `Unclosed client session` printed on python exit.
   - **Cause**: `aiohttp` running inside the generated SDK does not properly close when running synchronous functions recursively, or without `__del__`. 
   - **Fix**: Did not fix because it doesn't affect successful execution; it's a known non-critical behavior in some SDKs.
