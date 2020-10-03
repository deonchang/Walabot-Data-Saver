import WalabotAPI as walabot
import pandas as pd
import numpy as np

class Walabot():
    '''Interfaces with the Walabot API.'''

    def __init__(self):
        '''Load and initialise the Walabot API.'''

        self.walabot = walabot
        self.walabot.Init()
        self.walabot.Initialize()
        self.is_connected = False
        print('Walabot API initialised')

    def connect(self):
        '''
        Establishes a connection with the Walabot.

        Output:
            walabot_error: None if a successful connection was made. Otherwise, the API error is returned.
        '''

        walabot_error = None
        try:
            print('Connecting to the Walabot...')
            self.walabot.ConnectAny()
            print('Connected to the Walabot!')
            self.is_connected = True
        except self.walabot.WalabotError:
            print('Failed to connect to the Walabot!')
            walabot_error = self.walabot.GetErrorString()
        
        return walabot_error

    def disconnect(self):
        '''
        Stop and close connection with the Walabot.

        Output:
            walabot_error: None if the Walabot was successfully disconnected. Otherwise, the API error is returned.
        '''

        walabot_error = None
        try:
            print('Disconnecting from the Walabot...')
            walabot.Stop()
            walabot.Disconnect()
            print('Disconnected from the Walabot!')
            self.is_connected = False
        except self.walabot.WalabotError:
            print('Failed to disconnect from the Walabot!')
            walabot_error = self.walabot.GetErrorString()

        return walabot_error

    def start(self):
        '''Starts the Walabot'''

        self.walabot.Start()

    def set_profile(self, profile):
        '''
        Sets the Walabot scan profile.

        Inputs:
            profile: refer to WalabotAPI.py profile constants.

        Output:
            walabot_error: None if profile was set successfully. Otherwise, the API error is returned.
        '''

        walabot_error = None
        try:
            self.walabot.SetProfile(profile)
        except self.walabot.WalabotError:
            walabot_error = self.walabot.GetErrorString()

        return walabot_error

    def trigger(self):
        '''Triggers the Walabot and saves data.'''

        self.walabot.Trigger()

    def calibrate(self):
        '''Runs the built-in calibration function.'''

        self.walabot.StartCalibration()

        # According to the API doc, the Walabot requires manual triggers to facilitate calibration.
        while self.walabot.GetStatus()[0] == self.walabot.STATUS_CALIBRATING:
            print('Calibrating: {}%'.format(self.walabot.GetStatus()[1]))
            self.trigger()

    def get_raw_signals(self):
        '''
        Returns all the raw signals from the available antenna pairs.
        Rows are the pairs' amplitude at the particular time instance and columns are the time vector followed by the antenna pairs.
        Run a Trigger() command before getting the raw signals.
        For more information, refer to the Walabot API functions GetAntennaPairs() and GetSignal().

        Output:
            signals_pd: raw signals as an NxM Pandas DataFrame where N is the number of samples and M is the time vector + number of antenna pairs.
            walabot_error: None if no error occurred. Otherwise returns the API error.
        '''
        signals_pd = pd.DataFrame()
        walabot_error = None
        antenna_pairs = self.walabot.GetAntennaPairs()

        try:
            # This bit could do with some optimisation, perhaps allocating a matrix instead of appending to a list.
            # The data is stored row-wise at the momenet, we will transpose it later to make it column-wise.
            headers = ['time']
            signals = []

            # Save the time vector. Since all the pairs will have the
            # same time vector it does not matter whuch pair we grab it from.
            _, time = walabot.GetSignal(antenna_pairs[0])
            signals.append(time)

            # Save the antenna pair signal vectors
            for pair in range(len(antenna_pairs)):
                headers.append('tx={} rx={}'.format(antenna_pairs[pair].txAntenna, antenna_pairs[pair].rxAntenna))
                signal, _ = walabot.GetSignal(antenna_pairs[pair])
                signals.append(signal) # Matrix of the time vector and all antenna pair signals

            # Transpose so that columns are time, pair 1 signal, pair 2 signal, ..., pair n signal and
            # rows are the time ticks/pair's received signal amplitude
            signals_pd = pd.DataFrame(signals, index=headers) # Index not column labels because we transpose
            signals_pd = signals_pd.transpose()
        except self.walabot.WalabotError:
            walabot_error = self.walabot.GetErrorString()

        return signals_pd, walabot_error

    def set_arena_imaging(self, x, y, z, threshold, filter_type):
        '''
        Sets up arena for short-range imaging profile using Cartesian coordinates.

        Inputs:
            x: 1x3 tuple, (x_min, x_max, x_step)
            y: 1x3 tuple, (y_min, y_max, y_step)
            z: 1x3 tuple, (z_min, z_max, z_step)
            threshold: double, between 0.1 and 100
            filter_type: integer, refer to Walabot API for filter constants

        Output:
            walabot_error: Nothing if arena was set successfully. Otherwise, the API error is returned.
        '''
        walabot_error = None
        try:
            self.walabot.SetArenaX(*x)
            self.walabot.SetArenaY(*y)
            self.walabot.SetArenaZ(*z)
            self.walabot.SetThreshold(threshold)
            self.walabot.SetDynamicImageFilter(filter_type)
        except self.walabot.WalabotError:
            walabot_error = self.walabot.GetErrorString()

        return walabot_error

    def set_arena_sensor(self, r, theta, phi, threshold, filter_type):
        '''
        Sets up arena for sensor/tracker profiles using spherical coordinates.

        Inputs:
            r: 1x3 tuple, (theta_min, theta_max, x_step)
            theta: 1x3 tuple, (theta_min, theta_max, theta_step)
            phi: 1x3 tuple, (phi_min, phi_max, phi_step)
            threshold: double, between 0.1 and 100
            filter_type: integer, refer to Walabot API for filter constants

        Output:
            walabot_error: Nothing if arena was set successfully. Otherwise, the API error is returned.
        '''

        walabot_error = None
        try:
            self.walabot.SetArenaR(*r)
            self.walabot.SetArenaTheta(*theta)
            self.walabot.SetArenaPhi(*phi)
            self.walabot.SetThreshold(threshold)
            self.walabot.SetDynamicImageFilter(filter_type)
        except self.walabot.WalabotError:
            walabot_error = self.walabot.GetErrorString()

        return walabot_error

    def get_raw_image_slice(self):
        '''
        Returns a 2D image slice as defined by the arena parameters,
        MTI/derivative filter, and threshold settings.
        For more information, refer to the Walabot API function GetRawImageSlice().

        Outputs:
            image_np: 2D image as a Numpy array if no error occurred.
            walabot_error: None if no error occurred. Otherwise returns the API error.
        '''

        walabot_error = None
        image_slice_np = np.array([])
        try:
            image_slice, _, _, _, _ = self.walabot.GetRawImageSlice()
            image_slice_np = np.transpose(np.array(image_slice)) # Row, column
        except self.walabot.WalabotError:
            walabot_error = self.walabot.GetErrorString()

        return image_slice_np, walabot_error

    def get_image_dimensions(self):
        '''
        Returns the dimensions of a 2D image slice given the current arena configuration.

        Output:
            walabot_error: None if no error occurred. Otherwise returns the API error.
        '''

        width = 0
        height = 0
        walabot_error = None
        try:
            _, width, height, _, _ = self.walabot.GetRawImageSlice()
        except self.walabot.WalabotError:
            walabot_error = self.walabot.GetErrorString()

        return width, height, walabot_error

    def get_raw_image(self):
        '''
        Returns a 3D image as defined by the arena parameters,
        MTI/derivative filter, and threshold settings.
        For more information, refer to the Walabot API function GetRawImage().

        Outputs:
            image_np: 3D image as a Numpy array if no error occurred.
            walabot_error: None if no error occurred. Otherwise returns the API error.
        '''

        walabot_error = None
        image_np = np.array([])
        try:
            image, _, _, _, _ = self.walabot.GetRawImage()
            image_np = np.array(image)
            image_np = np.fliplr(np.transpose(image_np, (2, 0, 1))) # Transpose (row, column, depth) and flip
        except self.walabot.WalabotError:
            walabot_error = self.walabot.GetErrorString()

        return image_np, walabot_error
