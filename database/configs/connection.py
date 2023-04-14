from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from os import getcwd, path

class DataHandler:
    def __init__(self, db_path='database/configs/flights_master.db'):
        self.__connection_string = f'sqlite:///{path.join(getcwd(), db_path)}'
        self.__engine = self.__create_db_engine()
        self.session = None
        
    def __create_db_engine(self):
        engine = create_engine(self.__connection_string)
        return engine
    
    def __enter__(self):
        session_make = sessionmaker(bind=self.__engine)
        self.session = session_make()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()    
    
    def get_engine(self):
        return self.__engine
        
