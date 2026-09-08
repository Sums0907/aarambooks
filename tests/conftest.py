"""
conftest.py — shared test configuration.

Motor (MongoDB async driver) binds its thread pool to the event loop that was
active when the client was created. pytest-asyncio (v1.4.0) gives each test its
own event loop, so a shared Motor client created in session scope would attach to
a different loop than the test's loop and raise RuntimeError.

Solution: each test creates its own Motor connection by forcing
CustomerEngagementRepository._db = None before use. Motor's connection pool
reconnects automatically on each call to _get_db(). This is slightly slower but
correct and safe for integration tests.
"""
