# -*- coding: utf-8 -*-
# """
# Created on Thu Apr 21 17:17:20 2022

# Also known as "day checker", it's a tool designed to extract useful data from ArduCopter dataflash logs, to model this data and
# to store it in a sqlite database. It also generates a KML file for easy tracking of the analyzed logs.

# @author: caioems
# """

# TODO: create a windows service for syncing data with cloud db(API)

import simplekml, os
from database.repository.report_repo import RpRepo
from database.repository.motors_repo import MtRepo
from internal.loglist import LogList
from internal.daychecker import DayChecker
from tqdm import tqdm


class PipeLine:
    def __init__(self):
        """
         Initialize the object by creating the log list 
         and the KML object.
         
        """
        self._root = LogList()
        self._log_list = self._root.log_list
        self._kml = self.create_kml()

    def create_kml(self, kml_name="flights"):
        """
         Create KML object which will hold geometries and reports.
         
         @param kml_name - The name of the KML object.
         
         @return The newly created KML object.
         
        """
        self._kml = simplekml.Kml(name=kml_name)
        return self._kml

    def write_to_db(self):
        """
         Write data to sqlite database.
         
        """
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
            self.dc.report.vcc_std,
        )

        m_repo = MtRepo()
        m_repo.insert(
            self.dc.flight_timestamp,
            self.dc.drone_uid,
            self.dc.report.motors_pwm_list[0],
            self.dc.report.motors_pwm_list[1],
            self.dc.report.motors_pwm_list[2],
            self.dc.report.motors_pwm_list[3],
        )

    def run(self, flight_log):
        """
         Creates and runs the DayChecker. This is the main method.
         
         @param flight_log - flight log to be analyzed
         
        """
        self.dc = DayChecker(flight_log)

        # Storing data into db
        self.write_to_db()

        # Creating the kml features
        flight_ls = self.dc.create_linestring(self._kml)
        self.dc.agr_style(flight_ls)
        self.dc.create_balloon_report(flight_ls)


##running when not being imported
if __name__ == "__main__":
    flights = PipeLine()
    kml_file = f"{flights._root.root_folder}/flights.kml"

    ## map method
    results = list(
        tqdm(map(flights.run, flights._log_list), total=len(flights._log_list))
    )

    flights._kml.save(kml_file)
    print("Done.")
    os.startfile(kml_file)
