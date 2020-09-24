from tkinter import messagebox
from tkinter.ttk import Combobox
from os.path import exists
from walabot_hardware import Walabot
import tkinter as tk
import pandas as pd
import numpy as np

class MainApp(tk.Tk):
    '''Main application class'''

    def __init__(self):
        tk.Tk.__init__(self)
        self.title('Walabot Data Acquisition')

        # ----- Constants ----- #
        # Integer values of the profiles taken from WalabotAPI.py
        # There is PROF_WIDE, but it is not supported for the Developer edition.
        # Likewise PROF_TRACKER does not support raw signals.
        self.PROF_SHORT_RANGE_IMAGING = 'PROF_SHORT_RANGE_IMAGING'
        self.PROF_SENSOR_NARROW = 'PROF_SENSOR_NARROW'
        self.PROF_TRACKER = 'PROF_TRACKER'
        self.PROFILES = {
            self.PROF_SHORT_RANGE_IMAGING: 0x00010000,
            self.PROF_SENSOR_NARROW: 0x00020000 + 1,
            self.PROF_TRACKER: 0x00030000
        }
        self.PROFILE_NAMES = list(self.PROFILES.keys())

        # Filter constants taken from WalabotAPI.py
        self.FILTER_TYPES = {
            'None': 0,
            'Derivative': 1,
            'MTI': 2
        }
        self.FILTER_NAMES = list(self.FILTER_TYPES.keys())

        # Capture types (raw signals, 2D image, 3D image)
        self.SIGNALS = 'signals'
        self.IMAGE_SLICE = 'im_2d'
        self.IMAGE = 'im_3d'

        # ----- Walabot API -----#
        self.walabot = Walabot()

        # ----- Walabot control panel ------ #
        self.walabot_control_panel = tk.LabelFrame(self, text='Walabot control', padx=15, pady=5)
        self.walabot_control_panel.grid(row=0, column=0, padx=5, pady=5)

        self.profile_list_label = tk.Label(self.walabot_control_panel, text='Scan profile:')
        self.profile_list = Combobox(self.walabot_control_panel, values=self.PROFILE_NAMES,
                                     width=20, state='readonly')
        self.profile_list.bind('<<ComboboxSelected>>', self.handle_profile_change)
        self.profile_list.current(0)  # Default to imaging profile
        self.selected_profile = self.profile_list.get()

        self.walabot_settings_button = tk.Button(self.walabot_control_panel, text='Walabot settings', width=20,
                                                 command=self.handle_walabot_settings_window)
        self.connect_disconnect_button = tk.Button(self.walabot_control_panel, text='Connect to Walabot', width=20,
                                                   command=self.handle_walabot_connect_and_setup)

        self.profile_list_label.grid(row=0, column=0, padx=5, pady=5, sticky='W')
        self.profile_list.grid(row=1, column=0, padx=5, pady=5)
        self.walabot_settings_button.grid(row=2, column=0, padx=5, pady=5)
        self.connect_disconnect_button.grid(row=3, column=0, padx=5, pady=5)

        # ----- Acquisition control panel ----- #
        self.acquisition_control_panel = tk.LabelFrame(self, text='Acquisition', padx=5, pady=5)
        self.acquisition_control_panel.grid(row=1, column=0, padx=5, pady=5)

        self.calibrate_button = tk.Button(self.acquisition_control_panel, text='Calibrate (F9)', width=10,
                                          command=self.handle_walabot_calibrate)
        self.trigger_button = tk.Button(self.acquisition_control_panel, text='Trigger (F1)', width=10,
                                        command=self.handle_walabot_trigger)

        self.calibrate_button.grid(row=0, column=0, padx=5, pady=5)
        self.trigger_button.grid(row=0, column=1, padx=5, pady=5)

        # ----- Save control panel ----- #
        self.save_control_panel = tk.LabelFrame(self, text='Save', padx=15, pady=5)
        self.save_control_panel.grid(row=2, column=0, padx=5, pady=5)

        self.acquire_raw_signals = tk.IntVar()
        self.acquire_raw_signals_checkbutton = tk.Checkbutton(self.save_control_panel, text='Raw Signals',
                                                              variable=self.acquire_raw_signals)
        self.acquire_raw_image_slice = tk.IntVar()
        self.acquire_raw_image_slice_checkbutton = tk.Checkbutton(self.save_control_panel, text='Raw Image Slice',
                                                                  variable=self.acquire_raw_image_slice)
        self.acquire_raw_image = tk.IntVar()
        self.acquire_raw_image_checkbutton = tk.Checkbutton(self.save_control_panel, text='Raw Image',
                                                            variable=self.acquire_raw_image)

        self.save_file_prefix_entry_label = tk.Label(self.save_control_panel, anchor='w', text='Save file prefix:')
        self.save_file_prefix = tk.StringVar()
        self.save_file_prefix.set('capture')  # Default save file prefix
        self.save_file_prefix_entry = tk.Entry(self.save_control_panel, width=20, textvariable=self.save_file_prefix)

        self.save_button = tk.Button(self.save_control_panel, text='Save acquisition (F2)', width=20,
                                     command=self.handle_save_capture)

        self.acquire_raw_signals_checkbutton.grid(row=0, column=0, padx=5, pady=5, sticky='W')
        self.acquire_raw_image_slice_checkbutton.grid(row=1, column=0, padx=5, pady=5, sticky='W')
        self.acquire_raw_image_checkbutton.grid(row=2, column=0, padx=5, pady=5, sticky='W')
        self.save_file_prefix_entry_label.grid(row=3, column=0, padx=5, pady=5, sticky='W')
        self.save_file_prefix_entry.grid(row=4, column=0, padx=5, pady=5)
        self.save_button.grid(row=5, column=0, padx=5, pady=5)

        # ----- Variable initialisation ----- #
        self.capture_saved = False  # Used for detecting duplicate saves.
        self.counter = 0               # Number of captures saved with this file prefix

        # Default arena settings (profile dependent)
        self.param_1, self.param_2, self.param_3, self.threshold, self.filter_type = self.init_walabot_settings(self.selected_profile)

        # ----- Start ----- #
        self.bind('<F1>', self.handle_walabot_trigger)
        self.bind('<F9>', self.handle_walabot_calibrate)
        self.bind('<F2>', self.handle_save_capture)
        self.protocol('WM_DELETE_WINDOW', self.handle_app_exit) # Disconnect from Walabot if the application is closed
        self.mainloop()

    def is_walabot_connected(self):
        '''Determines if the Walabot is connected.

        Output:
            True if Walabot is connected. False otherwise.
        '''
        return self.walabot.is_connected

    def init_walabot_settings(self, profile):
        '''
        Sets default arena, threshold, and filter type values.
        These values were obtained from the Walabot API tutorial software.
        '''

        if profile == self.PROF_SHORT_RANGE_IMAGING: # Short range imaging profile
            param_1 = (-4, 4, 0.5)
            param_2 = (-6, 4, 0.5)
            param_3 = (3, 8, 0.5)
            threshold = 35.0
            filter_type = self.FILTER_TYPES['None']
        else:
            # Sensor or sensor narrow profiles
            param_1 = (10, 100, 2)
            param_2 = (40, 50, 2)
            param_3 = (40, 50, 2)
            threshold = 35.0
            filter_type = self.FILTER_TYPES['None']

        return param_1, param_2, param_3, threshold, filter_type

    def get_walabot_settings(self):
        '''
        Returns the current arena, threshold, and filter type values.

        Outputs:
            param_1: 1x3 tuple, parameter is profile-dependent
            param_2: 1x3 tuple, parameter is profile-dependent
            param_3: 1x3 tuple, parameter is profile-dependent
            threshold: double, between 0.1 and 100
            filter_type: integer, refer to Walabot API for filter constants
        '''

        return self.param_1, self.param_2, self.param_3, self.threshold, self.filter_type

    def set_walabot_settings(self, param_1, param_2, param_3, threshold, filter_type):
        '''Sets the arena parameters, threshold, and filter values'''

        self.param_1 = param_1
        self.param_2 = param_2
        self.param_3 = param_3
        self.threshold = threshold
        self.filter_type = self.FILTER_TYPES[filter_type]

    def is_settings_window_open(self):
        '''
        Check to see if the Walabot settings window is already open. If it is, move it to the top.
        '''
        children = list(self.children) # Child widgets of the root Tkinter window
        for child in children:
            if child.startswith('!walabotsettingswindow'):
                return True
        return False

    def handle_profile_change(self, *args):
        '''
        If the scan profile is changed while the Walabot settings window is open,
        close it since it will probably require different options (e.g. spherical instead of cartesian).

        Note that this function ignores input arguments - *args exists as a placeholder for when
        this function is called by a callback function which passes in an event.
        '''

        # Reinitialise the Walabot settings upon changing profile as the new profile might
        # require different settings (e.g. changing from imaging to sensor).
        self.selected_profile = self.profile_list.get()
        self.param_1, self.param_2, self.param_3, self.threshold, self.filter_type = self.init_walabot_settings(self.selected_profile)

        # If the settings window is open while changing profiles, close it and open it again for
        # the same reason as above.
        if self.is_settings_window_open():
            self.walabot_settings_window.close_settings_window()
            self.handle_walabot_settings_window()

        # If the Walabot is connected, it must be reconnected before setting the profile again.
        if self.is_walabot_connected():
            self.handle_walabot_disconnect()
            self.handle_walabot_connect_and_setup()

    def handle_walabot_settings_window(self):
        '''Opens the Walabot settings in a new window. If the window is already open, bring it in focus.'''

        if not self.is_settings_window_open():
            self.walabot_settings_window = WalabotSettingsWindow(self)
        else:
            self.walabot_settings_window.focus()

    def handle_walabot_connect_and_setup(self):
        '''
        Connect to the Walabot with the specified profile and
        arena settings and configure GUI buttons.
        '''

        connect_error = self.walabot.connect()
        if connect_error:
            error_msg = 'Walabot API error: {}'.format(connect_error)
            messagebox.showerror(title='Connect error', message=error_msg)
            return

        profile_error = self.walabot.set_profile(self.PROFILES[self.selected_profile])
        if profile_error:
            self.handle_walabot_disconnect()
            error_msg = 'Walabot API error: {}'.format(profile_error)
            messagebox.showerror(title='Error setting profile', message=error_msg)
            return

        if self.selected_profile == self.PROF_SHORT_RANGE_IMAGING:
            arena_error = self.walabot.set_arena_imaging(self.param_1, self.param_2, self.param_3,
                                                         self.threshold, self.filter_type)
        else:
            arena_error = self.walabot.set_arena_sensor(self.param_1, self.param_2, self.param_3,
                                                        self.threshold, self.filter_type)
        if arena_error:
            self.handle_walabot_disconnect()
            error_msg = 'Walabot API error: {}'.format(arena_error)
            messagebox.showerror(title='Error setting arena', message=error_msg)
            return

        # Toggle button function to disconnect
        self.connect_disconnect_button.configure(text="Disconnect from Walabot",
                                                 command=self.handle_walabot_disconnect)

        self.walabot.start()

    def handle_walabot_disconnect(self):
        '''Disconnect from the Walabot and reconfigure GUI buttons'''

        disconnect_error = self.walabot.disconnect()
        if disconnect_error:
            error_msg = 'Walabot API error {}'.format(disconnect_error)
            messagebox.showerror(title='Disconnect error', message=error_msg)
            return

        # Toggle the connect/disconnect button
        self.connect_disconnect_button.configure(text='Connect to Walabot', command=self.handle_walabot_connect_and_setup)

    def handle_walabot_calibrate(self, *args):
        '''Calibrates the Walabot using the Calibrate() function'''

        if not self.walabot.is_connected:
            messagebox.showerror('Calibrate error', 'The Walabot is not connected!')
            return

        self.walabot.calibrate()

    def handle_walabot_trigger(self, *args):
        '''
        Runs a Trigger() command on the Walabot
        
        Note that this function ignores input arguments - *args exists as a placeholder for when
        this function is called by a callback function which passes in an event.
        '''

        if not self.walabot.is_connected:
            messagebox.showerror('Trigger error', 'The Walabot is not connected!')
            return

        self.walabot.trigger()
        self.capture_saved = False
        print(" _______   _                               _ \n"
              "|__   __| (_)                             | |\n"
              "   | |_ __ _  __ _  __ _  ___ _ __ ___  __| |\n"
              "   | | '__| |/ _` |/ _` |/ _ \ '__/ _ \/ _` |\n"
              "   | | |  | | (_| | (_| |  __/ | |  __/ (_| |\n"
              "   |_|_|  |_|\__, |\__, |\___|_|  \___|\__,_|\n"
              "              __/ | __/ |                    \n"
              "             |___/ |___/                     \n")

    def handle_app_exit(self):
        '''Disconnects from the Walabot if it is still connected and closes the program'''

        if self.is_walabot_connected():
            self.walabot.disconnect()
        self.destroy()


    def generate_file_name(self, capture_type):
        '''
        Generates the file name for the capture and appends a counter and file type in the filename.
        The prefix is automatically fetched from the entry widget.

        Input:
            capture_type: str, capture type for reference purposes (e.g. capture_0_signals.csv, capture_0_im_2d.csv)
        '''

        self.counter = 0
        file_name = '{}_{}_{}.csv'.format(self.save_file_prefix.get(), str(self.counter), str(capture_type))

        # Looks in the current directory for csv files with the entered prefix and
        # increments the suffix counter. This way the user can terminate the
        # program and resume capturing/saving later on.
        while exists(file_name):
            self.counter += 1
            file_name = '{}_{}_{}.csv'.format(self.save_file_prefix.get(), str(self.counter), str(capture_type))

        return file_name

    def handle_save_capture(self, *args):
        '''
        Checks whether or not the user has already capture_saved the current trigger
        and also if they have one of the save checkboxes ticked.

        Note that this function ignores input arguments - *args exists as a placeholder for when
        this function is called by a callback function which passes in an event.
        '''

        if self.acquire_raw_signals.get() + \
           self.acquire_raw_image_slice.get() + \
           self.acquire_raw_image.get() == 0:
            # Check whether at least one acquisition type (signals, 2D image, or 3D image) is selected
            messagebox.showerror('Save error', 'No acquisition type selected!')
            return

        if not self.walabot.is_connected:
            messagebox.showerror('Connect error', 'The Walabot is not connected!')
            return

        if self.capture_saved:
            continue_saving = messagebox.askyesno('Confirm save',
                                                  'The current trigger is the same as the previous one. Do you want to continue saving?',
                                                  icon=messagebox.WARNING)
            if not continue_saving:
                return

        print("   _____             _                   \n"
              "  / ____|           (_)                  \n"
              " | (___   __ ___   ___ _ __   __ _       \n"
              "  \___ \ / _` \ \ / / | '_ \ / _` |      \n"
              "  ____) | (_| |\ V /| | | | | (_| |_ _ _ \n"
              " |_____/ \__,_| \_/ |_|_| |_|\__, (_|_|_)\n"
              "                              __/ |      \n"
              "                             |___/       \n")

        # Save the requested data
        if self.acquire_raw_signals.get() == 1:
            self.save_raw_signals()

        if self.acquire_raw_image_slice.get() == 1:
            self.save_raw_image_slice()

        if self.acquire_raw_image.get() == 1:
            self.save_raw_image()

        print("   _____                     _ \n"
              "  / ____|                   | |\n"
              " | (___   __ ___   _____  __| |\n"
              "  \___ \ / _` \ \ / / _ \/ _` |\n"
              "  ____) | (_| |\ V /  __/ (_| |\n"
              " |_____/ \__,_| \_/ \___|\__,_|\n")
        print('Capture no.: {}'.format(self.counter))

    def save_capture(self, capture, capture_type):
        '''
        Saves the provided capture matrix to a .csv file using the entered prefix.

        Input:
            capture: Pandas DataFrame or Numpy array containing the raw signals or image
            capture_type: signals, raw image slice, or raw image
        '''

        # Generate file name with appropriate suffix based on capture type (e.g. capture_0_signals.csv, capture_0_2d_image.csv)
        file_name = self.generate_file_name(capture_type)

        # Pandas DataFrames have column labels by default.
        # We only want this when we save raw signals and not if we are saving an image.
        if capture_type == self.SIGNALS:
            capture.to_csv(file_name, index=False)
        elif capture_type == self.IMAGE_SLICE:
            # capture.to_csv(file_name, index=False, header=False)
            np.savetxt(file_name, capture, fmt='%.f', comments='', delimiter=',')
        elif capture_type == self.IMAGE:
            # https://stackoverflow.com/questions/3685265/how-to-write-a-multidimensional-array-to-a-text-file
            with open(file_name, 'w') as outfile:
                outfile.write('# Array shape (rows x columns x depth): {}x{}x{}\n'.format(capture.shape[1], capture.shape[2], capture.shape[0]))
                for data_slice in capture:
                    np.savetxt(outfile, data_slice, fmt='%.f', comments='', delimiter=',')
                    outfile.write('# New slice\n')

        self.capture_saved = True

    def save_axes(self, image_dim):
        '''
        Saves the axes for plotting to a separate CSV file.
        Note that although the 2D images only have two axes (X, Y) or (Phi, R),
        all three axes are saved for reference purposes.

        Input:
            image_dim: str, 2D or 3D for file name generation
        '''

        # Min, max, and increment size for either X, Y, Z or
        # R, phi, theta depending on the profile
        axis_1_min = self.param_1[0]
        axis_1_max = self.param_1[1]
        axis_1_res = self.param_1[2]
        axis_2_min = self.param_2[0]
        axis_2_max = self.param_2[1]
        axis_2_res = self.param_2[2]
        axis_3_min = self.param_3[0]
        axis_3_max = self.param_3[1]
        axis_3_res = self.param_3[2]

        # Generate the axis vectors
        axis_1_num_steps = int((axis_1_max - axis_1_min) / axis_1_res)
        axis_1 = [axis_1_min + i*axis_1_res for i in range(axis_1_num_steps+1)]
        axis_2_num_steps = int((axis_2_max - axis_2_min) / axis_2_res)
        axis_2 = [axis_2_min + i*axis_2_res for i in range(axis_2_num_steps+1)]
        axis_3_num_steps = int((axis_3_max - axis_3_min) / axis_3_res)
        axis_3 = [axis_3_min + i*axis_3_res for i in range(axis_3_num_steps+1)]

        # Save the axis vectors to a CSV file with each axis corresponding to a column
        axes = [axis_1, axis_2, axis_3]
        if self.selected_profile == self.PROF_SHORT_RANGE_IMAGING:
            axes_pd = pd.DataFrame(axes, index=['X', 'Y', 'Z'])
        else:
            axes_pd = pd.DataFrame(axes, index=['R', 'theta', 'phi'])
        file_name = self.generate_file_name(image_dim)
        axes_pd = axes_pd.transpose()
        axes_pd.to_csv(file_name, index=False)

    def save_raw_signals(self):
        '''Saves all of the Walabot's raw signals from the current trigger'''

        # One capture (trigger) contains a time column plus all of the raw signals from the antenna pairs.
        # E.g. All 40 pairs using the Sensor profile would result in an array of size 8192 by 41.

        signals_capture, error = self.walabot.get_raw_signals()
        if error:
            error_msg = 'Walabot API error: {}'.format(error)
            messagebox.showerror(title='Error saving raw signals', message=error_msg)
        else:
            self.save_capture(signals_capture, self.SIGNALS)

    def save_raw_image_slice(self):
        '''Saves a 2D image slice from the current trigger'''

        image_slice_capture, error = self.walabot.get_raw_image_slice()
        if error:
            error_msg = 'Walabot API error: {}'.format(error)
            messagebox.showerror(title='Error saving image slice', message=error_msg)
        else:
            self.save_capture(image_slice_capture, self.IMAGE_SLICE)
            self.save_axes('im_2d_axes')

    def save_raw_image(self):
        '''Saves a 3D image from the current trigger'''

        image_capture, error = self.walabot.get_raw_image()
        if error:
            error_msg = 'Walabot API error: {}'.format(error)
            messagebox.showerror(title='Error saving image', message=error_msg)
        else:
            self.save_capture(image_capture, self.IMAGE)
            self.save_axes('im_3d_axes')


class WalabotSettingsWindow(tk.Toplevel):
    '''
    Child window to view and modify additional Walabot settings such as the
    arena settings, threshold value, and filter type.
    '''

    def __init__(self, master):
        tk.Toplevel.__init__(self)
        self.master = master
        self.title('Walabot settings')
        self.apply_button = tk.Button(self, text='Apply', width=10, command=self.handle_apply_button)
        self.cancel_button = tk.Button(self, text='Cancel', width=10, command=self.handle_cancel_button)
        self.apply_button.grid(row=1, column=1, padx=5, pady=5)
        self.cancel_button.grid(row=0, column=1, padx=5, pady=5)

        # ----- Arena control panel ----- #
        self.arena_control_panel = tk.LabelFrame(self, text='Arena parameters', padx=5, pady=5)
        self.arena_control_panel.grid(row=0, column=0, padx=5, pady=5)
        self.min_label = tk.Label(self.arena_control_panel, text='Minimum')
        self.max_label = tk.Label(self.arena_control_panel, text='Maximum')
        self.res_label = tk.Label(self.arena_control_panel, text='Resolution')
        self.min_label.grid(row=0, column=1, padx=5, pady=5)
        self.max_label.grid(row=0, column=2, padx=5, pady=5)
        self.res_label.grid(row=0, column=3, padx=5, pady=5)

        # ----- Input fields for the arena regions ----- #
        # Populate them with default values from the Walabot API tutorial software.
        self.param_1_min_entry = tk.Entry(self.arena_control_panel, width=8)
        self.param_1_max_entry = tk.Entry(self.arena_control_panel, width=8)
        self.param_1_res_entry = tk.Entry(self.arena_control_panel, width=8)
        self.param_2_min_entry = tk.Entry(self.arena_control_panel, width=8)
        self.param_2_max_entry = tk.Entry(self.arena_control_panel, width=8)
        self.param_2_res_entry = tk.Entry(self.arena_control_panel, width=8)
        self.param_3_min_entry = tk.Entry(self.arena_control_panel, width=8)
        self.param_3_max_entry = tk.Entry(self.arena_control_panel, width=8)
        self.param_3_res_entry = tk.Entry(self.arena_control_panel, width=8)

        # Populate with values from the main application
        param_1, param_2, param_3, threshold, filter_type = self.master.get_walabot_settings()
        self.param_1_min_entry.insert(0, param_1[0])
        self.param_1_max_entry.insert(0, param_1[1])
        self.param_1_res_entry.insert(0, param_1[2])
        self.param_2_min_entry.insert(0, param_2[0])
        self.param_2_max_entry.insert(0, param_2[1])
        self.param_2_res_entry.insert(0, param_2[2])
        self.param_3_min_entry.insert(0, param_3[0])
        self.param_3_max_entry.insert(0, param_3[1])
        self.param_3_res_entry.insert(0, param_3[2])

        self.param_1_min_entry.grid(row=1, column=1, padx=5, pady=5)
        self.param_1_max_entry.grid(row=1, column=2, padx=5, pady=5)
        self.param_1_res_entry.grid(row=1, column=3, padx=5, pady=5)
        self.param_2_min_entry.grid(row=2, column=1, padx=5, pady=5)
        self.param_2_max_entry.grid(row=2, column=2, padx=5, pady=5)
        self.param_2_res_entry.grid(row=2, column=3, padx=5, pady=5)
        self.param_3_min_entry.grid(row=3, column=1, padx=5, pady=5)
        self.param_3_max_entry.grid(row=3, column=2, padx=5, pady=5)
        self.param_3_res_entry.grid(row=3, column=3, padx=5, pady=5)

        # ----- Additional settings control panel ----- #
        # These widgets are common amongst the profiles.
        self.additional_control_panel = tk.LabelFrame(self, text='Additional settings', padx=86, pady=5)
        self.additional_control_panel.grid(row=1, column=0, padx=5, pady=5)
        self.threshold_label = tk.Label(self.additional_control_panel, text='Threshold: ')
        self.threshold_entry = tk.Entry(self.additional_control_panel, width=8)
        self.threshold_entry.insert(0, threshold)

        self.filter_label = tk.Label(self.additional_control_panel, text='Filter type:')
        self.filter_list = Combobox(self.additional_control_panel, values=self.master.FILTER_NAMES, state='readonly', width=8)
        self.filter_list.current(filter_type)

        self.threshold_label.grid(row=0, column=0, padx=5, pady=5, sticky='W')
        self.threshold_entry.grid(row=0, column=1, padx=5, pady=5)
        self.filter_label.grid(row=1, column=0, padx=5, pady=5, sticky='W')
        self.filter_list.grid(row=1, column=1, padx=5, pady=5)

        # Change the parameter labels according to the profile selected
        if self.master.selected_profile == self.master.PROF_SHORT_RANGE_IMAGING:
            # Short range imaging.
            # If the imaging profile is selected, the Walabot requires the arena to
            # be set in Cartesian coordinates.

            # ----- Arena control panel widgets (Cartesian) ----- #
            # Here, param_1 is X, param_2 is Y, and param_3 is Z
            self.x_label = tk.Label(self.arena_control_panel, text='Arena X [cm]:')
            self.y_label = tk.Label(self.arena_control_panel, text='Arena Y [cm]:')
            self.z_label = tk.Label(self.arena_control_panel, text='Arena Z [cm]:')

            self.x_label.grid(row=1, column=0, padx=13, pady=5, sticky='W')
            self.y_label.grid(row=2, column=0, padx=13, pady=5, sticky='W')
            self.z_label.grid(row=3, column=0, padx=13, pady=5, sticky='W')

        else:
            # Tracker or sensor narrow profiles.
            # If the sensor/sensor narrow profile is selected, the Walabot requires the arena to
            # be set in spherical coordinates.

            # ----- Arena control panel widgets (spherical) ----- #
            # Here, param_1 is R, param_2 is theta, and param_3 is phi
            self.r_label = tk.Label(self.arena_control_panel, text='Arena R [cm]:')
            self.theta_label = tk.Label(self.arena_control_panel, text='Arena theta [deg]:')
            self.phi_label = tk.Label(self.arena_control_panel, text='Arena phi [deg]:')

            self.r_label.grid(row=1, column=0, padx=2, pady=5, sticky='W')
            self.theta_label.grid(row=2, column=0, padx=2, pady=5, sticky='W')
            self.phi_label.grid(row=3, column=0, padx=2, pady=5, sticky='W')

    def close_settings_window(self):
        '''Closes the settings window'''

        self.destroy()

    def handle_apply_button(self):
        '''Passes the entered parameters back into the main window'''

        if self.master.is_walabot_connected():
            messagebox.showerror('Error setting arena', 'These settings cannot be changed while the Walabot is connected. Please disconnect first and then apply the settings.')
            return

        # TODO: implement error checking for the values
        param_1 = (
            float(self.param_1_min_entry.get()), float(self.param_1_max_entry.get()),
            float(self.param_1_res_entry.get()))
        param_2 = (
            float(self.param_2_min_entry.get()), float(self.param_2_max_entry.get()),
            float(self.param_2_res_entry.get()))
        param_3 = (
            float(self.param_3_min_entry.get()), float(self.param_3_max_entry.get()),
            float(self.param_3_res_entry.get()))

        threshold = float(self.threshold_entry.get())

        filter_type = self.filter_list.get()

        self.master.set_walabot_settings(param_1, param_2, param_3, threshold, filter_type)
        self.close_settings_window()

    def handle_cancel_button(self):
        '''Also closes the settings window'''

        self.close_settings_window()
