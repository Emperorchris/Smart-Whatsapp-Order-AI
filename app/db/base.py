"""
Shared base for all SQLAlchemy models.
Every model file imports Base from here so they all share the same metadata.
"""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()