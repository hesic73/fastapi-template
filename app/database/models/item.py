# The Item model is only used for debugging purposes. It is not used in the application.

from ..base import Base

import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Double, Enum

from enum import Enum as _Enum


class ItemType(str, _Enum):
    type1 = "type1"
    type2 = "type2"
    type3 = "type3"


class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Double, nullable=False)
    created_at = Column(DateTime, nullable=False,
                        default=datetime.datetime.now)
    item_type = Column(Enum(ItemType), nullable=False)

    def __repr__(self):
        return f"{self.name}"
