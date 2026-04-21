from types import SimpleNamespace


def make_mock_user(
    *,
    user_id: str = "a8e2dc0d-8d09-4e95-a570-8e6bb44a49d2",
    username: str = "demo-user",
    email: str = "demo@example.com",
    is_active: bool = True,
    password: str = "encoded-password",
    source: str = "LOCAL",
):
    return SimpleNamespace(
        id=user_id,
        username=username,
        email=email,
        is_active=is_active,
        password=password,
        source=source,
    )
