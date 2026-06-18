"""Shared fake-Motor classes for Cogent tests.

These are importable directly (``from conftest_helpers import ...``) so they
can be used from both the conftest fixtures and standalone test functions.
"""

from __future__ import annotations

from typing import Any, Dict, List


class _FakeMotorCursor:
    """Async cursor that wraps a list of dicts."""

    def __init__(self, results: list) -> None:
        self._results = results

    def sort(self, key_or_list: Any, direction: int = 1) -> "_FakeMotorCursor":
        return self

    async def to_list(self, length: int = 200) -> list:
        return self._results[:length]

    def __aiter__(self):
        return self._AsyncIter(iter(self._results))

    class _AsyncIter:
        def __init__(self, it):
            self._it = it
        async def __anext__(self):
            try:
                return next(self._it)
            except StopIteration:
                raise StopAsyncIteration


class _FakeMotorCollection:
    """Minimal in-memory collection that mirrors a subset of Motor's API."""

    def __init__(self) -> None:
        self._docs: Dict[str, Any] = {}
        self._id_field = "id"

    async def find_one(self, filter: Dict[str, Any], *args: Any, **kwargs: Any) -> Any | None:
        for doc in self._docs.values():
            if all(doc.get(k) == v for k, v in filter.items()):
                return dict(doc)
        return None

    def find(self, filter: Dict[str, Any] | None = None,
             *args: Any, **kwargs: Any) -> _FakeMotorCursor:
        filter = filter or {}
        results = [dict(d) for d in self._docs.values()
                   if all(d.get(k) == v for k, v in filter.items())]
        return _FakeMotorCursor(results)

    async def insert_one(self, doc: Dict[str, Any]) -> Any:
        doc = dict(doc)
        if self._id_field not in doc:
            import uuid
            doc[self._id_field] = str(uuid.uuid4())
        doc_id = doc.get("_id", doc[self._id_field])
        self._docs[str(doc_id)] = dict(doc)
        return type("Obj", (), {"inserted_id": doc_id})()

    async def update_one(self, filter: Dict[str, Any],
                         update: Dict[str, Any], upsert: bool = False,
                         *args: Any, **kwargs: Any) -> Any:
        import uuid
        for doc in list(self._docs.values()):
            if all(doc.get(k) == v for k, v in filter.items()):
                for op, fields in update.items():
                    if op == "$set":
                        doc.update(fields)
                    elif op == "$push":
                        for k, v in fields.items():
                            doc.setdefault(k, []).append(v)
                self._docs[str(doc[self._id_field])] = doc
                return type("Obj", (), {"modified_count": 1})()
        if upsert:
            new_doc = dict(filter)
            for op, fields in update.items():
                if op == "$set" and isinstance(fields, dict):
                    new_doc.update(fields)
            if self._id_field not in new_doc:
                new_doc[self._id_field] = str(uuid.uuid4())
            self._docs[str(new_doc.get("_id", new_doc[self._id_field]))] = new_doc
            return type("Obj", (), {"modified_count": 1, "upserted_id": new_doc.get("_id", new_doc[self._id_field])})()
        return type("Obj", (), {"modified_count": 0})()

    async def delete_one(self, filter: Dict[str, Any]) -> Any:
        for doc_id, doc in list(self._docs.items()):
            if all(doc.get(k) == v for k, v in filter.items()):
                del self._docs[doc_id]
                return type("Obj", (), {"deleted_count": 1})()
        return type("Obj", (), {"deleted_count": 0})()

    async def delete_many(self, filter: Dict[str, Any]) -> Any:
        ids = [doc_id for doc_id, doc in self._docs.items()
               if all(doc.get(k) == v for k, v in filter.items())]
        for doc_id in ids:
            del self._docs[doc_id]
        return type("Obj", (), {"deleted_count": len(ids)})()

    def aggregate(self, pipeline: list) -> _FakeMotorCursor:
        return _FakeMotorCursor(list(self._docs.values()))


class FakeMotorDatabase:
    """Stand-in for a Motor database object."""

    def __init__(self) -> None:
        self._collections: Dict[str, _FakeMotorCollection] = {}

    def __getattr__(self, name: str) -> _FakeMotorCollection:
        if name not in self._collections:
            self._collections[name] = _FakeMotorCollection()
        return self._collections[name]

    def get_collection(self, name: str) -> _FakeMotorCollection:
        return getattr(self, name)


# Export friendly alias for conftest use
FakeMotorCursor = _FakeMotorCursor
FakeMotorCollection = _FakeMotorCollection
