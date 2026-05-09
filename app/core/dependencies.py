from ..db.db_engine import get_db
from fastapi import Depends
from sqlalchemy.orm import Session
from typing import Annotated


DBSession = Annotated[Session, Depends(get_db)]