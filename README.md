# Walabot Data Saver

Acquire and visualise data obtained from a Walabot Developer edition. Three different types of data captures are available with the Walabot Developer: raw signals, 2D images (3D image slice), and 3D raw images. This application allows you to save all three of these to CSV files for further processing.


## Requirements

Please ensure that you have the [Python Walabot API](https://api.walabot.com/_pythonapi.html#_installingwalabotapi) installed. NumPy and Pandas are also required which can both be installed using Pip.

## Usage

Lauching the application:
```bash
python main.py
```

The following steps give a brief explanantion on how to use the program. For more detailed information regarding the Walabot, please see their API documentation both on their [website](https://api.walabot.com/) and in the WalabotAPI.py file.

### Walabot setup

The first step involves selecting a scan profile. Not all data types are available depending on the profile selected. If you plan on capturing images, the scan region (arena) can also be adjusted to your requirements along with other settings such as the moving target indicatior (MTI) filter and pixel thresholds. Once these are set, connect to the Walabot device.


### Triggering
Before capturing data, the Walabot should be calibrated to zero out the images. If you are capturing raw signals, then don't calibrate as it does affect the signals but in an unexpected way which is not documented in the API. The Walabot captures data using the concept of triggers — each trigger is a capture of whatever the Walabot was picking up at that point in time. This is the data that is saved and is only updated with subsequent triggers.


### Saving
The captures can then be saved by checking the data types you wish to save. The output CSV files are saved in the same directory.

## License
This project is licensed under the [GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html) licence.