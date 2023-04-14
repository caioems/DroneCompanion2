from database.configs.base import Base
from sqlalchemy import Column, Integer, String

class Motors(Base):
    #declarative base
    __tablename__='motors'
    
    uid = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(String, unique=True)
    drone_uid = Column(String)
    m1_avg_pwm = Column(String)
    m2_avg_pwm = Column(String)
    m3_avg_pwm = Column(String)
    m4_avg_pwm = Column(String)
    
    def __repr__(self):
        return f"Total de registros: {self.uid}"
    
    #TODO: crud
