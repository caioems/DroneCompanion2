import pandas as pd
from statistics import mean

# TODO: motor efficiency = Thrust (grams) x Power (watts)
class HealthTests:
    def __init__(self, rcou_df, vibe_df, powr_df, cam_df, trig_df):
        """
         Initialize the object. It stores dataframes and apply logical
         tests to point out status and feedback of UAV hardware.
         
         @param rcou_df - dataframe with RCOU data (motors)
         @param vibe_df - dataframe with VIBE data (vibration)
         @param powr_df - dataframe with POWR data (board voltage)
         @param cam_df - dataframe with CAM data (camera messages)
         @param trig_df - dataframe with TRIG data (camera trigger)
        """
        self._rcou_df = rcou_df
        self._vibe_df = vibe_df
        self._powr_df = powr_df
        self._cam_df = cam_df
        self._trig_df = trig_df

        self.motors_status = "UNKNOWN"
        self.motors_feedback = ""
        self.imu_status = "UNKNOWN"
        self.imu_feedback = ""
        self.gps_status = "UNKNOWN"
        self.gps_feedback = ""
        self.vcc_status = None
        self.vcc_mean = None
        self.vcc_std = None

    def __repr__(self):
        return f"""motors_status = {self.motors_status} 
motors_feedback = {self.motors_feedback}
imu_status = {self.imu_status}
imu_feedback = {self.imu_feedback}
gps_status = {self.gps_status}
gps_feedback = {self.gps_feedback}
trig_status = {self.trig_status}
trig_feedback = {self.trig_feedback}"""

    def motor_test(self):
        """
         This is a test to see if it's possible to predict 
         motors maintenance. It compares each servo channel 
         output to detect imbalance. Change warn and fail 
         levels as needed.
         
        """
        self.motors_status = "OK"
        self.motors_feedback = "balanced"
        self.motors_pwm_list = []

        pwm_df = pd.DataFrame(
            {
                "1": [mean(self._rcou_df.C1), max(self._rcou_df.C1)],
                "2": [mean(self._rcou_df.C2), max(self._rcou_df.C2)],
                "3": [mean(self._rcou_df.C3), max(self._rcou_df.C3)],
                "4": [mean(self._rcou_df.C4), max(self._rcou_df.C4)],
            }
        ).T
        pwm_df.columns = ["mean", "max"]

        self.motors_pwm_list = [int(x) for x in pwm_df["mean"]]

        # Comparing frontal motors and back motors
        fmotors = abs(self.motors_pwm_list[0] - self.motors_pwm_list[2])
        bmotors = abs(self.motors_pwm_list[1] - self.motors_pwm_list[3])
        
        warn_level = 30
        if fmotors >= warn_level or bmotors >= warn_level:
            bad_pwm = None
            bad_motor = None
            if fmotors >= warn_level:
                bad_pwm = max([self.motors_pwm_list[0], self.motors_pwm_list[2]])
                bad_motor = str(self.motors_pwm_list.index(bad_pwm) + 1)
            elif bmotors >= warn_level:
                bad_pwm = max([self.motors_pwm_list[1], self.motors_pwm_list[3]])
                bad_motor = str(self.motors_pwm_list.index(bad_pwm) + 1)

            fail_level = 45
            if fmotors >= fail_level or bmotors >= fail_level:
                self.motors_status = "FAIL"
                self.motors_feedback = f'Big difference in {"frontal" if fmotors >= fail_level else "back"} motors PWM\'s avg. Check motor {bad_motor}.'
            else:
                self.motors_status = "WARN"
                self.motors_feedback = f'Small difference between {"frontal" if fmotors >= warn_level else "back"} motors PWM. Check motor {bad_motor}.'

    def vibe_test(self):
        """
        This is a test to make sure there are no issues related 
        with UAV vibration.
        
        """
        self.imu_status = "OK"
        self.imu_feedback = "no vibe issues"

        clips = (
            self._vibe_df.Clip0[-1],
            self._vibe_df.Clip1[-1],
            self._vibe_df.Clip2[-1],
        )
        vibes = (
            mean(self._vibe_df.VibeX),
            mean(self._vibe_df.VibeY),
            mean(self._vibe_df.VibeZ),
        )

        # Check if the vibration is enough for accel clipping
        if any(v > 30 for v in vibes):
            max_vibes = str(round(max(vibes), 1))
            self.imu_status = "WARN"
            self.imu_feedback = f"Several vibration ({max_vibes} m/s/s)."
        elif any(c > 0 for c in clips):
            max_clips = str(max(clips))
            self.imu_status = "FAIL"
            self.imu_feedback = f"Accel was clipped {max_clips} times."
    
    def vcc_test(self):
        """
         This is a test to see if there are voltage issues going on at the 
         flight controller.
         
        """
        self.vcc_mean = round(self._powr_df.Vcc.mean(), 2)
        self.vcc_std = round(self._powr_df.Vcc.std(), 2)

        self.vcc_status = "OK"
        self.vcc_feedback = (
            f"No board voltage issues (avg: {self.vcc_mean}v, std: {self.vcc_std}v)."
        )

        # Check the voltage deviation of the board
        if self.vcc_std >= 0.1:
            self.vcc_status = "WARN"
            self.vcc_feedback = (
                f"Small voltage deviation ({self.vcc_std}v), please check the board."
            )
        # Check the board to see if the voltage deviation is greater than 0.15v
        if self.vcc_std >= 0.15:
            self.vcc_status = "FAIL"
            self.vcc_feedback = (
                f"Big voltage deviation ({self.vcc_std}v), please check the board."
            )

    def trig_test(self):
        """
         Test the trigger and camera messages to see if the camera is
         shooting properly.
         
        """
        triggers = self._trig_df.shape[0]
        feedbacks = self._cam_df.shape[0]
        # This function is called when the camera has skipped the triggers.
        if triggers == feedbacks:
            self.trig_status = "OK"
            self.trig_feedback = f"No photos skipped ({triggers})."
        elif triggers > feedbacks:
            self.trig_status = "FAIL"
            self.trig_feedback = (
                f"{triggers - feedbacks} photos were taken without feedback."
            )
        elif triggers < feedbacks:
            self.trig_status = "FAIL"
            self.trig_feedback = f"The camera skipped {feedbacks - triggers} photos."

    def run(self):
        """
         Run all the tests. This is the main method.
         
         
         @return self
        """
        self.motor_test()
        self.vibe_test()
        self.vcc_test()
        self.trig_test()
        return self
