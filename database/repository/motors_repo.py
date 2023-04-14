from database.configs.connection import DataHandler
from database.entities.motors import Motors
from sqlalchemy.exc import IntegrityError

class MtRepo:
    def select(self):
        with DataHandler() as db:
            try:
                data = db.session.query(Motors).all()
                return data
            except Exception as exception:
                db.session.rollback()
                raise exception
                    
    def insert(self, timestamp, drone_uid, m1_avg_pwm, m2_avg_pwm, m3_avg_pwm, m4_avg_pwm):
        with DataHandler() as db:
            try:
                data_insert = Motors(
                timestamp=timestamp, 
                drone_uid=drone_uid, 
                m1_avg_pwm=m1_avg_pwm, 
                m2_avg_pwm=m2_avg_pwm,
                m3_avg_pwm=m3_avg_pwm,
                m4_avg_pwm=m4_avg_pwm
                )
                db.session.add(data_insert)
                db.session.commit()
            except IntegrityError:
                pass
            except Exception as exception:
                db.session.rollback()
                raise exception
    #TODO: format following considering the new entities        
    def delete(self, vbt):
        with DataHandler() as db:
            try:
                db.session.query(Motors).filter(Motors.vbt == vbt).delete()
                db.session.commit()
            except Exception as exception:
                db.session.rollback()
                raise exception
            
    def update(self, vbt, vat):
        with DataHandler() as db:
            try:
                db.session.query(Motors).filter(Motors.vbt == vbt).update({Motors.vat == vat})
                db.session.commit()
            except Exception as exception:
                db.session.rollback()
                raise exception
