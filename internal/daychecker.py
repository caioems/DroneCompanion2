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

#class containing functions for the data extraction/modeling and kml customization
class DayChecker:
    types = ["CAM", "EV", "BAT", "MSG", "POWR", "RCOU", "VIBE", "TRIG"]
    
    def __init__(self, flight_log):
        self.flight_log = flight_log
        self.run()
            
    def create_csv(self):
        log = self.flight_log.as_posix()
        path = self.flight_log.parent
        
        def mycmd(type):
            os.system(f"mavlogdump.py --planner --format csv --types {type} {str(log)} > {str(path)}/{type}.csv")
        
        with ThreadPoolExecutor() as executor:       
            executor.map(mycmd, DayChecker.types)
    
    def create_df(self, csv_name):
        csv_file = os.path.join(self.flight_log.parent, csv_name + ".csv")        
        with open(csv_file, "r") as csv:
            df = pd.read_csv(csv, on_bad_lines='skip', index_col='timestamp')
            df.index = pd.to_datetime(df.index, unit='s', origin='unix')
        return df
    
    def create_df_dict(self):
        self.df_dict = {i: self.create_df(i) for i in DayChecker.types}            
        return self.df_dict 
    
    def delete_csv(self):
        def delete_all_csv(type):
            csv_file = os.path.join(self.flight_log.parent, f'{type}.csv')
            os.remove(csv_file)
        
        with ThreadPoolExecutor() as executor:
            executor.map(delete_all_csv, DayChecker.types)  
    
    def metadata_test(self):        
        self.mdata_test = {}
        img_path = self.flight_log.parent 
        
        def get_random_image_metadata():
            files = [f for f in os.listdir(img_path) if f.endswith('.JPG')]
            random_file = random.choice(files)
            with open(os.path.join(img_path, random_file), 'rb') as f:
                exif_data = exifread.process_file(f)
            return exif_data
        
        try:
            mdata = get_random_image_metadata()        
            
            if 100 <= mdata['EXIF ISOSpeedRatings'].values[0] <= 1600:
                self.mdata_test['ISO'] = ['OK']
            else:
                self.mdata_test['ISO'] = ['FAIL', 'Check camera ISO.']
            
            if str(mdata['EXIF ExposureTime']) == '1/1600':
                self.mdata_test['Shutter'] = ['OK']
            else:
                self.mdata_test['Shutter'] = ['FAIL','Check camera shutter speed.']
                
            if re.match(r'a[0-9]r[0-9]_[a-z]{3}', mdata['Thumbnail Copyright'].values):
                self.mdata_test['Copyright'] = ['OK']
            else:
                self.mdata_test['Copyright'] = ['FAIL', 'Check camera copyright.']
        
            if re.match(r'^\d{7}$', mdata['Image Artist'].values):
                self.mdata_test['Artist'] = ['OK']
            else:
                self.mdata_test['Artist'] = ['FAIL', 'Check camera artist.']    
            
            keys = self.mdata_test.keys()
            if all(self.mdata_test[test][0] == 'OK' for test in keys):
                self.mdata_test['Result'] = ['OK', 'no sensor issues']
            else:                
                for test in keys:
                    if self.mdata_test[test][0] != 'OK':
                        self.mdata_test['Result'] = self.mdata_test[test]         
        except Exception as e:
            print(f'Error ocurred in the metadata test: {str(e)}')
            #pass    
    
    def create_linestring(self, kml, container_index=0):
        ls = kml.newlinestring(name=self.flight_log.name)
        coords_list = [
            (row.Lng, row.Lat) for index, row in self.df_dict['CAM'].iterrows()
            ]
        ls.coords = coords_list
        return ls
    
    def create_polygon(self, kml, container_index):
        poly = kml.containers[container_index].newpolygon(name=self.flight_log.name)
        coords_list = [
            (row.Lng, row.Lat) for index, row in self.df_dict['CAM'].iterrows()
            ]
        coords_list = np.array(coords_list)
        poly.outerboundaryis = concaveHull(coords_list, 3)
        return poly
    
    def rgb_style(self, feature):
        rgb_style = simplekml.Style()
        rgb_style.linestyle.width = 3.0
        try:
            if 'OK' in self.mdata_test['Result'][0]:
                rgb_style.linestyle.color = simplekml.Color.whitesmoke
            else:
                rgb_style.linestyle.color = simplekml.Color.black
            feature.style = rgb_style
        except:
            rgb_style.linestyle.color = simplekml.Color.whitesmoke
            feature.style = rgb_style
        
    def agr_style(self, feature):
        agr_style = simplekml.Style()
        agr_style.linestyle.width = 2.0
        try:
            if 'OK' in self.mdata_test['Result'][0]:
                agr_style.linestyle.color = simplekml.Color.red
            else:
                agr_style.linestyle.color = simplekml.Color.yellow
            feature.style = agr_style
        except:
            agr_style.linestyle.color = simplekml.Color.red
            feature.style = agr_style
            
    def run(self):
        self.create_csv()
        self.create_df_dict()         
        self.delete_csv()
        self.metadata_test()
        
        self.flight_timestamp = str(self.df_dict['EV'].index[0].timestamp())
        #TODO: fix a bug where sometimes the version is imported instead of serial number
        self.drone_uid = self.df_dict['MSG'].Message[2][9:].replace(" ", "")
        self.report = HealthTests(
            self.df_dict['RCOU'], 
            self.df_dict['VIBE'], 
            self.df_dict['POWR'], 
            self.df_dict['CAM'],
            self.df_dict['TRIG']
            )
        self.report.run()
    
    def create_balloon_report(self, feature):
        flight_data = self.df_dict['EV'].index[0]
        flight_time = self.df_dict['EV'].index[-1] - flight_data
        base_path = Path(__file__).parent
        template_path = (base_path / "../internal/motororder-quad-x-2d.png").resolve()
        
        #TODO: convert html to file instead of raw coding
        #TODO: balloon being displayed as default          
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
    
            
