from ..db.db_engine import get_db
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated


DBSession = Annotated[AsyncSession, Depends(get_db)]
