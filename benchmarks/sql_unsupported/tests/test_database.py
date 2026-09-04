from app.database import order_items


def test_order_by_id() -> None:
    assert [item.id for item in order_items("id")] == [1, 2, 3]


def test_order_by_name() -> None:
    assert [item.name for item in order_items("name")] == ["Alpha", "Beta", "Gamma"]
