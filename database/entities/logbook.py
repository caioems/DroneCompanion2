from configs.base import Base
from sqlalchemy import Column, Integer, Numeric, String

class Report(Base):
    #declarative base
    __tablename__='logbook'
    
    uid = Column(Integer, primary_key=True, nullable=False)
    vbt = Column(String)
    vat = Column(String)
    aat = Column(String)
    val = Column(String)
    to_time = Column(String)
    land_time = Column(String)
    
    def __repr__(self):
        return f"Total de registros: {self.uid}"
    
    #TODO: crud

