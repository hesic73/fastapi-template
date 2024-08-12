from ..base import Base

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship


class Address(Base):
    __tablename__ = 'addresses'
    id: Mapped[int] = mapped_column(primary_key=True)
    email_address: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    user: Mapped['User'] = relationship(  # type: ignore
        back_populates='addresses')

    def __repr__(self):
        return f'<Address(id={self.id},email_address={self.email_address!r})>'
