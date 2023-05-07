import os
import re
import random
import exifread
import simplekml
import numpy as np
import pandas as pd
from pathlib import Path
from internal.concave_hull import concaveHull
from tests.healthtests import HealthTests
from concurrent.futures import ThreadPoolExecutor


# class containing functions for the data extraction/modeling and kml customization
class DayChecker:
    messages = ["CAM", "EV", "BAT", "MSG", "POWR", "RCOU", "VIBE", "TRIG"]

    def __init__(self, flight_log):
        """
        Initialize the instance and run the program. This is the entry point for the class.

        @param flight_log - path to a BIN log file
        """
        self.flight_log = flight_log
        self.run()

    def create_csv(self):
        """
        Create csv files from a list of messages within a flight log. It uses a thread pool to take advantage of asynchronous execution.
        
        """
        log = self.flight_log.as_posix()
        path = self.flight_log.parent

        def mycmd(msg_type):
            """
            Dump specific messages from log to file. This is a wrapper around mavlogdump.py

            @param msg_type - String representing the message type (ex.: "CAM")
            """
            os.system(
                f"mavlogdump.py --planner --format csv --types {msg_type} {str(log)} > {str(path)}/{msg_type}.csv"
            )

        with ThreadPoolExecutor() as executor:
            executor.map(mycmd, DayChecker.messages)

    def create_df(self, csv_name):
        """
        Create a pandas dataframe from a csv file. This is used to create dataframes containing messages that are stored in flight logs.

        @param csv_name - String representing the name of the csv file

        @return pd.DataFrame with index as the column timestamp
        """
        csv_file = os.path.join(self.flight_log.parent, csv_name + ".csv")

        with open(csv_file, "r") as csv:
            df = pd.read_csv(csv, on_bad_lines="skip", index_col="timestamp")
            df.index = pd.to_datetime(df.index, unit="s", origin="unix")
        return df

    def create_df_dict(self):
        """
        Create and return a dictionary of dataframes. Keys are each of DayChecker.messages and values are their respective pandas DataFrames.


        @return Dictionary of dataframes
        """
        self.df_dict = {i: self.create_df(i) for i in DayChecker.messages}
        return self.df_dict

    def delete_csv(self):
        """
        Delete all CSV files in a thread pool to take advantage of asynchronous execution.
        """

        def delete_all_csv(msg_type):
            """
            Delete all csv files of a given message type.
            
            @param msg_type - String representing the message type (ex.: "CAM")
            """
            csv_file = os.path.join(self.flight_log.parent, f"{msg_type}.csv")
            os.remove(csv_file)

        with ThreadPoolExecutor() as executor:
            executor.map(delete_all_csv, DayChecker.messages)

    def metadata_test(self):
        """
        Gets the metadata of random JPG files and run tests on it to make sure the JPG contains specific parameters.

        """
        self.mdata_test = {}
        img_path = self.flight_log.parent

        def get_random_image_metadata():
            """
            Get metadata for a random image. This is useful for getting the EXIF data from an image taken as a sample of a bigger batch of images.


            @return A dictionary of exif data for the image.
            """
            files = [f for f in os.listdir(img_path) if f.endswith(".JPG")]
            random_file = random.choice(files)
            with open(os.path.join(img_path, random_file), "rb") as f:
                exif_data = exifread.process_file(f)
            return exif_data

        try:
            mdata = get_random_image_metadata()

            # Camera's ISO
            if 100 <= mdata["EXIF ISOSpeedRatings"].values[0] <= 1600:
                self.mdata_test["ISO"] = ["OK"]
            else:
                self.mdata_test["ISO"] = ["FAIL", "Check camera ISO."]

            # Camera's shutter speed
            if str(mdata["EXIF ExposureTime"]) == "1/1600":
                self.mdata_test["Shutter"] = ["OK"]
            else:
                self.mdata_test["Shutter"] = ["FAIL", "Check camera shutter speed."]

            # Camera's copyright
            if re.match(r"a[0-9]r[0-9]_[a-z]{3}", mdata["Thumbnail Copyright"].values):
                self.mdata_test["Copyright"] = ["OK"]
            else:
                self.mdata_test["Copyright"] = ["FAIL", "Check camera copyright."]

            # Camera's artist
            if re.match(r"^\d{7}$", mdata["Image Artist"].values):
                self.mdata_test["Artist"] = ["OK"]
            else:
                self.mdata_test["Artist"] = ["FAIL", "Check camera artist."]

            keys = self.mdata_test.keys()
            # This method will set the result of the sensor test.
            if all(self.mdata_test[test][0] == "OK" for test in keys):
                self.mdata_test["Result"] = ["OK", "no sensor issues"]
            else:
                # This method will set the result of all tests in the test dictionary
                for test in keys:
                    # This method is used to test the result of the test.
                    if self.mdata_test[test][0] != "OK":
                        self.mdata_test["Result"] = self.mdata_test[test]
        except Exception as e:
            print(f"Error ocurred in the metadata test: {str(e)}")

    def create_linestring(self, kml):
        """Creates a linestring feature based on the lat and lon of the CAM messages within the log.

        Args:
            kml (simplekml.Kml): The Kml object that will hold the
            linestring

        Returns:
            simplekml.LineString: The LineString object
        """

        ls = kml.newlinestring(name=self.flight_log.name)
        coords_list = [
            (row.Lng, row.Lat) for index, row in self.df_dict["CAM"].iterrows()
        ]
        ls.coords = coords_list
        return ls

    #TODO: add condition for merging polygons of merged flights
    def create_polygon(self, kml, container_index):
        """
         **NEEDS FIX**
         Create and return a polygon for the KML. The polygons are created by using the concave hull technique.
         
         @param kml (simplekml.Kml) - The Kml object that will hold the linestring
         @param container_index - The index of the container that will contain the polygon
         
         @return The polygon created in the KML file and added to
        """
        poly = kml.containers[container_index].newpolygon(name=self.flight_log.name)
        coords_list = [
            (row.Lng, row.Lat) for index, row in self.df_dict["CAM"].iterrows()
        ]
        coords_list = np.array(coords_list)
        poly.outerboundaryis = concaveHull(coords_list, 3)
        return poly

    def rgb_style(self, feature):
        """
         Set the style of the simplekml.LineString. It is used to indicate the sensor used in the flight.
         
         @param feature - linestring to be stylized
        """
        rgb_style = simplekml.Style()
        rgb_style.linestyle.width = 3.0
        
        #Different color line if the test results are good or bad
        try:
            
            if "OK" in self.mdata_test["Result"][0]:
                rgb_style.linestyle.color = simplekml.Color.whitesmoke
            else:
                rgb_style.linestyle.color = simplekml.Color.black
            feature.style = rgb_style
            
        #Ignores the color change if there is an issue with mdata_test
        except:
            rgb_style.linestyle.color = simplekml.Color.whitesmoke
            feature.style = rgb_style

    def agr_style(self, feature):
        """
        Set the style of the simplekml.LineString. It is used to indicate the sensor used in the flight.
         
         @param feature - linestring to be stylized
        """
        agr_style = simplekml.Style()
        agr_style.linestyle.width = 2.0
        try:
            # This method is called when the test result is OK.
            if "OK" in self.mdata_test["Result"][0]:
                agr_style.linestyle.color = simplekml.Color.red
            else:
                agr_style.linestyle.color = simplekml.Color.yellow
            feature.style = agr_style
        except:
            agr_style.linestyle.color = simplekml.Color.red
            feature.style = agr_style

    def run(self):
        """
        This is the main method of the class. It will create the CSV files, the dataframes from the data files, and then delete the CSV files. It also runs the metadata tests and create the health reports.
        """
        self.create_csv()
        self.create_df_dict()
        self.delete_csv()
        self.metadata_test()

        self.flight_timestamp = str(self.df_dict["EV"].index[0].timestamp())
        # TODO: fix a bug where sometimes the version is imported instead of serial number
        self.drone_uid = self.df_dict["MSG"].Message[2][9:].replace(" ", "")
        self.report = HealthTests(
            self.df_dict["RCOU"],
            self.df_dict["VIBE"],
            self.df_dict["POWR"],
            self.df_dict["CAM"],
            self.df_dict["TRIG"],
        )
        self.report.run()

    def create_balloon_report(self, feature):
        """
         Create a report for the linestrings and save it to the KML file. It is used to show a balloon with useful information in google earth.
         
         @param feature - linestring to be stylized
        """
        flight_data = self.df_dict["EV"].index[0]
        flight_time = self.df_dict["EV"].index[-1] - flight_data
        base_path = Path(__file__).parent
        template_path = (base_path / "../internal/motororder-quad-x-2d.png").resolve()

        # TODO: convert html to file instead of raw coding
        # TODO: balloon being displayed as default
        feature.balloonstyle.text = f"""<html>
                                        <table align="center" border="0" cellpadding="0" cellspacing="0" style="border-collapse:collapse; height:270px; width:400px">
                                        <tbody>
                                            <tr>
                                                <td>
                                                <table align="center" border="0" cellpadding="0" cellspacing="0" style="border-collapse:collapse; height:100%; margin-left:auto; margin-right:auto; opacity:0.95; width:100%">
                                                    <tbody>
                                                        <tr>
                                                            <td style="height:90px; text-align:center; vertical-align:middle; width:50%">
                                                            <p><span style="color:#000000"><strong><span style="font-family:Tahoma,Geneva,sans-serif">Flight time:</span></strong></span></p>

                                                            <p><span style="font-size:20px"><strong><span style="font-family:Tahoma,Geneva,sans-serif">{str(flight_time.components.minutes)}m {str(flight_time.components.seconds)}s</span></strong></span></p>
                                                            </td>
                                                            <td style="height:90px; text-align:center; vertical-align:middle; width:50%">
                                                            <p><span style="color:#000000"><strong><span style="font-family:Tahoma,Geneva,sans-serif">Batt. cons.:</span></strong></span></p>

                                                            <p><span style="font-size:20px"><strong><span style="font-family:Tahoma,Geneva,sans-serif">{str(round(self.df_dict['BAT'].CurrTot[-1]))} mAh</span></strong></span></p>
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="height:90px; text-align:center; vertical-align:middle; width:50%">
                                                            <p><span style="color:#000000"><strong><span style="font-family:Tahoma,Geneva,sans-serif">Camera:</span></strong></span></p>

                                                            <p><span style="font-size:20px"><strong><span style="font-family:Tahoma,Geneva,sans-serif">{self.mdata_test['Result'][0]}</span></strong></span></p>

                                                            <p><span style="color:#bdc3c7"><em><span style="font-family:Tahoma,Geneva,sans-serif">{self.mdata_test['Result'][1]}&nbsp;</span></em></span></p>
                                                            </td>
                                                            <td style="height:90px; text-align:center; vertical-align:middle; width:50%">
                                                            <p><span style="color:#000000"><strong><span style="font-family:Tahoma,Geneva,sans-serif">Motors:</span></strong></span></p>

                                                            <p><span style="font-size:20px"><strong><span style="font-family:Tahoma,Geneva,sans-serif">{self.report.motors_status}</span></strong></span></p>

                                                            <p><span style="color:#bdc3c7"><em><span style="font-family:Tahoma,Geneva,sans-serif">{self.report.motors_feedback}&nbsp;</span></em></span></p>
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="height:90px; text-align:center; vertical-align:middle; width:50%">
                                                            <p><span style="color:#000000"><strong><span style="font-family:Tahoma,Geneva,sans-serif">IMU:</span></strong></span></p>

                                                            <p><span style="font-size:20px"><strong><span style="font-family:Tahoma,Geneva,sans-serif">{self.report.imu_status}</span></strong></span></p>

                                                            <p><span style="color:#bdc3c7"><em><span style="font-family:Tahoma,Geneva,sans-serif">{self.report.imu_feedback}</span></em></span></p>

                                                            <p>&nbsp;</p>
                                                            </td>
                                                            <td style="height:90px; text-align:center; vertical-align:middle; width:50%">
                                                            <p><span style="color:#000000"><strong><span style="font-family:Tahoma,Geneva,sans-serif">Board voltage:</span></strong></span></p>

                                                            <p><span style="font-size:20px"><strong><span style="font-family:Tahoma,Geneva,sans-serif">{self.report.vcc_status}</span></strong></span></p>

                                                            <p><span style="color:#bdc3c7"><em><span style="font-family:Tahoma,Geneva,sans-serif">{self.report.vcc_feedback}&nbsp;</span></em></span></p>
                                                            </td>
                                                        </tr>
                                                    </tbody>
                                                </table>

                                                <p>&nbsp;</p>
                                                </td>
                                                <td>&nbsp;
                                                <table align="center" border="0" cellpadding="0" cellspacing="0" style="border-collapse:collapse; height:100%; margin-left:auto; margin-right:auto; width:100%">
                                                    <tbody>
                                                        <tr>
                                                            <td style="height:55px; text-align:center; vertical-align:middle; width:50%"><span style="font-size:24px"><span style="font-family:Tahoma,Geneva,sans-serif"><span style="color:#2ecc71"><strong>{self.report.motors_pwm_list[2]}</strong></span></span></span></td>
                                                            <td style="height:55px; text-align:center; vertical-align:middle; width:50%"><span style="font-size:24px"><span style="font-family:Tahoma,Geneva,sans-serif"><strong><span style="color:#3498db">{self.report.motors_pwm_list[0]}</span></strong></span></span></td>
                                                        </tr>
                                                        <tr>
                                                            <td colspan="2" style="text-align:center; vertical-align:middle"><span style="font-family:Tahoma,Geneva,sans-serif"><img alt="" src="{template_path.as_uri()}" style="border-style:solid; border-width:0px; height:159px; margin-left:20px; margin-right:20px; width:149px" /></span></td>
                                                        </tr>
                                                        <tr>
                                                            <td style="height:55px; text-align:center; vertical-align:middle; width:50%"><span style="font-size:24px"><span style="font-family:Tahoma,Geneva,sans-serif"><strong><span style="color:#3498db">{self.report.motors_pwm_list[1]}</span></strong></span></span></td>
                                                            <td style="height:55px; text-align:center; vertical-align:middle; width:50%"><span style="font-size:24px"><span style="font-family:Tahoma,Geneva,sans-serif"><span style="color:#2ecc71"><strong>{self.report.motors_pwm_list[3]}</strong></span></span></span></td>
                                                        </tr>
                                                    </tbody>
                                                </table>

                                                <p>&nbsp;</p>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </html>"""
