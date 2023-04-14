from database.configs.connection import DataHandler
from database.entities.report import Report
from sqlalchemy.exc import IntegrityError

class RpRepo:
    def select(self):
        with DataHandler() as db:
            try:
                data = db.session.query(Report).all()
                return data
            except Exception as exception:
                db.session.rollback()
                raise exception
                    
    def insert(self, timestamp, drone_uid, motors_status, motors_feedback, imu_status, imu_feedback, vcc_status, vcc_mean, vcc_std):
        with DataHandler() as db:
            try:
                data_insert = Report(
                    timestamp=timestamp,
                    drone_uid=drone_uid,
                    motor_status=motors_status, 
                    motor_feedback=motors_feedback, 
                    imu_status=imu_status, 
                    imu_feedback=imu_feedback,
                    vcc_status=vcc_status,
                    vcc_mean=vcc_mean,
                    vcc_std=vcc_std
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
                db.session.query(Report).filter(Report.vbt == vbt).delete()
                db.session.commit()
            except Exception as exception:
                db.session.rollback()
                raise exception
            
    def update(self, vbt, vat):
        with DataHandler() as db:
            try:
                db.session.query(Report).filter(Report.vbt == vbt).update({Report.vat == vat})
                db.session.commit()
            except Exception as exception:
                db.session.rollback()
                raise exception
