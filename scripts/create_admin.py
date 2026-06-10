#!/usr/bin/env python3
"""Create (or ensure) an admin user. Usage:

    python -m scripts.create_admin <username> <password>
"""
from __future__ import annotations

import asyncio
import sys

from app.core.config import settings
from app.db.session import AsyncSessionFactory
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService


async def main(username: str, password: str) -> None:
    async with AsyncSessionFactory() as session:
        service = AuthService(UserRepository(session), settings)
        await service.ensure_bootstrap_admin(username, password)
        await session.commit()
    print(f"Admin '{username}' is ready.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
