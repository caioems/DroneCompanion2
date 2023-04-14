from database.configs.base import Base
from sqlalchemy import Column, Integer, String, Text, Numeric

class Report(Base):
    #declarative base
    __tablename__='report'
    
    uid = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(String, unique=True)
    drone_uid = Column(String)
    motor_status = Column(Text)
    motor_feedback = Column(Text)
    imu_status = Column(Text)
    imu_feedback = Column(Text)
    vcc_status = Column(Text)
    vcc_mean = Column(Numeric)
    vcc_std = Column(Numeric)
    
    def __repr__(self):
        return f"Total de registros: {self.uid}"
    
    #TODO: crud

