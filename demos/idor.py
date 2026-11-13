"""Isolated BOLA demonstration: no server, database, or application imports."""


def vulnerable_read(documents, document_id, actor):
    return documents[document_id]


def protected_read(documents, document_id, actor):
    document = documents.get(document_id)
    if document is None or document["owner"] != actor:
        raise LookupError("Not found")
    return document


def check_isolation(reader):
    documents = {"known-id": {"owner": "alice", "content": "Fictional private text"}}
    assert reader(documents, "known-id", "alice")["owner"] == "alice"
    try:
        reader(documents, "known-id", "bob")
    except LookupError:
        return
    raise AssertionError("BOLA: Bob read Alice's document")


if __name__ == "__main__":
    try:
        check_isolation(vulnerable_read)
    except AssertionError:
        print("DETECTED: vulnerable lookup exposes another user's document")
    else:
        raise SystemExit("Demonstration failed to detect the vulnerability")
    check_isolation(protected_read)
    print("PASS: owner check prevents the same attack")
