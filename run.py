# -*- coding: utf-8 -*-
# """
# Created on Thu Apr 21 17:17:20 2022

# Also known as "day checker", it's a tool designed to extract useful data from ArduCopter dataflash logs, to model this data and 
# to store it in a sqlite database. It also generates a KML file for easy tracking of the analyzed logs.

# @author: caioems
# """

#TODO: create a auto update function
#TODO: create a windows service for syncing data with cloud db(API)

import simplekml, os
from database.repository.report_repo import RpRepo
from database.repository.motors_repo import MtRepo
from internal.loglist import LogList
from internal.daychecker import DayChecker
from tests.healthtests import HealthTests
from tqdm import tqdm


class PipeLine:    
    def __init__(self):
        self._root = LogList()
        self._log_list = self._root.log_list
        self._kml = self.create_kml('flights')      
        
    def create_kml(self, kml_name):
        self._kml = simplekml.Kml(name=kml_name)
        self._kml.newfolder(name='RGB')
        self._kml.newfolder(name='AGR')
        return self._kml
    
    def write_to_db(self):
        rp_repo = RpRepo()
        rp_repo.insert(
            self.dc.flight_timestamp,
            self.dc.drone_uid,
            self.dc.report.motors_status,
            self.dc.report.motors_feedback, 
            self.dc.report.imu_status, 
            self.dc.report.imu_feedback,
            self.dc.report.vcc_status,
            self.dc.report.vcc_mean,
            self.dc.report.vcc_std
            )
        
        m_repo = MtRepo()
        m_repo.insert(
            self.dc.flight_timestamp, 
            self.dc.drone_uid,
            self.dc.report.motors_pwm_list[0], 
            self.dc.report.motors_pwm_list[1], 
            self.dc.report.motors_pwm_list[2], 
            self.dc.report.motors_pwm_list[3]
            )
    #TODO: move this method to daychecker.py
    def run(self, flight_log):
        self.dc = DayChecker(flight_log)
        
        #Storing data into db
        self.write_to_db()
          
        #Creating the kml features
        flight_alt = self.dc.df_dict['TERR']['CHeight'].median()
        if flight_alt < 105:
            rgb = self.dc.create_linestring(flights._kml, 0)
            self.dc.rgb_style(rgb)
            self.dc.create_balloon_report(rgb)
        elif flight_alt > 105:
            agr = self.dc.create_linestring(flights._kml, 1)
            self.dc.agr_style(agr)
            self.dc.create_balloon_report(agr)

##running when not being imported
if __name__ == "__main__":
    flights = PipeLine()
    kml = f'{flights._root.root_folder}/flights.kml'
       
    ## map method
    results = list(tqdm(map(flights.run, flights._log_list), total=len(flights._log_list)))
    
    flights._kml.save(kml)
    print('Done.')
    os.startfile(kml)