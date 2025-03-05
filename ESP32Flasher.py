import esptool
import requests
import serial.tools.list_ports
from colorama import Fore, Style
from git import Repo
import os
import time
from pathlib import Path

from FirmwareManager import FirmwareManager


class ESP32Flasher:
    """
    A class to handle flashing firmware to ESP32 devices.

    Attributes:
    -----------
    serialport : str
        The serial port to which the ESP32 device is connected.
    fwchoice : int or None
        The firmware choice selected by the user.
    selectedfw : str
        The selected firmware.
    selectedboard : str
        The selected board type.
    extraesp32bins : str
        Directory for extra ESP32 binaries.
    scorpbins : str
        Path to Marauder/WROOM binaries.
    BR : str
        Baud rate for serial communication.
    hardresetlist : list
        List of GPIO pins for hard reset.
    choices : str
        Menu options for firmware flashing.
    firmware_manager : FirmwareManager
        Manager for handling firmware downloads and updates.

    Methods:
    --------
    checkforserialport():
        Checks for the connected serial port and identifies the device type.
    print_device_type(device):
        Prints the type of the connected device based on its VID.
    choose_fw():
        Prompts the user to choose a firmware option.
    flash_firmware():
        Flashes the selected firmware to the ESP32 device.
    erase_esp32():
        Erases the firmware on the ESP32 device.
    flashtheboard(eraseparams, flashparams):
        Erases and flashes the firmware to the ESP32 device.
    execute_esptool_command(message, params):
        Executes esptool commands with retries.
    update_option():
        Updates all firmware files by deleting old ones and downloading new ones.
    prereqcheck():
        Checks and downloads necessary prerequisites.
    checkforesp32marauder():
        Checks and downloads the latest Marauder firmware.
    checkforevilportal():
        Checks and downloads the Evil Portal firmware.
    checkfors3bin():
        Checks and sets the path for the ESP32-S3 firmware.
    checkforoldhardwarebin():
        Checks and sets the path for the old hardware firmware.
    checkforminibin():
        Checks and sets the path for the mini hardware firmware.
    checkfornewhardwarebin():
        Checks and sets the path for the new hardware firmware.
    """
    def __init__(self):
        self.serialport = ''
        self.fwchoice = None
        self.selectedfw = ''
        self.selectedboard = ''
        self.extraesp32bins = "Extra_ESP32_Bins"
        self.scorpbins = os.path.join(self.extraesp32bins, "Marauder/WROOM")
        self.BR = "115200"
        self.hardresetlist = [5, 6, 8, 9, 10, 11, 12, 13]
        self.choices = r'''
        //==================================================================\\
        || Options:                                                        ||
        ||  1) Flash Marauder on WiFi Devboard or ESP32-S2                 ||
        ||  2) Save Flipper Blackmagic WiFi settings                       ||
        ||  3) Flash Flipper Blackmagic                                    ||
        ||  4) Flash Marauder on ESP32-WROOM                               ||
        ||  5) Flash Marauder on ESP32 Marauder Mini                       ||
        ||  6) Flash v6 Marauder on ESP32-WROOM (RabbitLabs Minion Marauder)||
        ||  7) Flash Marauder on ESP32-S3 (There is no current S3 bin)     ||
        ||  8) Flash Marauder on AWOK v1-3 or Duoboard                     ||
        ||  9) Flash Marauder on AWOK v4 Chungus Board                     ||
        || 10) Flash Marauder on AWOK v5 ESP32                             ||
        || 11) Flash Marauder on AWOK Dual ESP32 (Orange Port)             ||
        || 12) Flash Marauder on AWOK Dual ESP32 Touch Screen (White Port) ||
        || 13) Flash Marauder on AWOK Dual ESP32 Mini (White Port)         ||
        || 14) Flash Evil Portal on ESP32-WROOM                            ||
        || 15) Flash Evil Portal on ESP32-S2 or WiFi Devboard              ||
        || 16) Just Erase ESP32 - Try this if you think you bricked it     ||
        || 17) Update all files                                            ||
        || 18) Exit                                                        ||
        \\==================================================================//
        '''
        self.firmware_manager = FirmwareManager("https://github.com/UberGuidoZ/Marauder_BINs.git", self.extraesp32bins)

    def checkforserialport(self):
        """
        Checks for the presence of a serial port connected to an ESP32 device.

        If a serial port is already specified, it will not perform the check and will print a message.
        Otherwise, it will search for available serial ports and match them against a list of known
        vendor IDs (VIDs) for ESP32 devices. If a matching device is found, it sets the serial port
        and identifies the device type.

        If no ESP32 device is detected, it prints an error message and prompts the user to connect
        a device. If firmware choice is not preselected, it will call the `choose_fw` method; otherwise,
        it will exit the program.

        The method also prints the detected device type.

        Attributes:
            self.serialport (str): The serial port to check.
            self.fwchoicepreselect (bool): Flag to determine if firmware choice is preselected.
        """
        if self.serialport:
            print(f"Will not check for serial port or possible chip type since it is specified as {self.serialport}")
            return
        print("Checking for serial port...")
        vids = ['303A', '10C4', '1A86', '0483']
        ports = list(serial.tools.list_ports.comports())
        for vid in vids:
            for port in ports:
                if vid in port.hwid:
                    self.serialport = port.device
                    device = vid
        if not self.serialport:
            print(Fore.RED + "No ESP32 device was detected!" + Style.RESET_ALL)
            print(Fore.RED + "Please plug in a Flipper WiFi devboard or an ESP32 chip and try again" + Style.RESET_ALL)
            if not self.fwchoicepreselect:
                self.choose_fw()
            else:
                exit()
        self.print_device_type(device)

    def print_device_type(self, device):
        """
        Prints the type of device based on the provided device identifier.

        Args:
            device (str): The device identifier string.

        Prints:
            str: A message indicating the most likely type of device corresponding to the provided identifier.
        """
        device_types = {
            '303A': "You are most likely using a Flipper Zero WiFi Devboard or an ESP32-S2",
            '10C4': "You are most likely using an ESP32-WROOM, an ESP32-S2-WROVER, or an ESP32-S3-WROOM",
            '1A86': "You are most likely using a knock-off ESP32 chip! Success is not guaranteed!",
            '0483': "You are most likely using an DrB0rk S3 Multiboard"
        }
        print(Fore.BLUE + device_types.get(device, "Unknown device") + Style.RESET_ALL)

    def choose_fw(self):
        """
        Handles the firmware selection process.

        If a firmware choice has been preselected, it confirms the selection and waits for 5 seconds
        to allow the user to cancel if the preselection was unintended. If no preselection is made,
        it prompts the user to enter their choice from the available options.

        Attributes:
            fwchoice (int or None): The preselected firmware choice, if any.
            fwchoicepreselect (bool): Indicates whether a firmware choice has been preselected.
            choices (list): The list of available firmware choices.

        Methods:
            flash_firmware(): Initiates the firmware flashing process based on the selected choice.
        """
        if self.fwchoice is not None:
            self.fwchoicepreselect = True
            print(Fore.BLUE + f"You have preselected option {self.fwchoice}" + Style.RESET_ALL)
            print("If you didn't mean to do this, CTRL-C now!")
            print("Waiting 5 seconds before continuing...")
            time.sleep(5)
        else:
            self.fwchoicepreselect = False
            print(self.choices)
            self.fwchoice = int(input("Please enter the number of your choice: "))
        self.flash_firmware()

    def flash_firmware(self):
        """
        Flash the firmware to the ESP32 device based on the user's selection.

        This method provides various firmware flashing options for different ESP32 boards and configurations.
        It validates the user's choice, sets the appropriate parameters, and performs the flashing process.

        Flash options:
            1: Marauder (ESP32-S2)
            2: Save Flipper Blackmagic WiFi settings (ESP32-S2)
            3: Blackmagic (ESP32-S2)
            4: Marauder (ESP32-WROOM)
            5: Marauder (ESP32 Marauder Mini)
            6: Marauder v6 (ESP32-WROOM)
            7: Marauder (ESP32-S3)
            8: Marauder (AWOK v1-3 or Duoboard)
            9: Marauder (AWOK v4 Chungus Board)
            10: Marauder (AWOK v5 ESP32)
            11: Marauder (AWOK Dual ESP32 - Orange Port)
            12: Marauder (AWOK Dual ESP32 Touch Screen - White Port)
            13: Marauder Mini (AWOK Dual ESP32 Mini - White Port)
            14: Evil Portal (ESP32-WROOM)
            15: Evil Portal (ESP32-S2)
            16: Erase ESP32
            17: Update all files
            18: Exit

        If the user selects option 16, the ESP32 will be erased.
        If the user selects option 17, the update process will be initiated.
        If the user selects option 18, the program will exit.
        For other options, the firmware will be flashed to the ESP32 device.

        Raises:
            SystemExit: If an invalid option is selected or if the user chooses to exit.

        """
        flash_options = {
            1: ("Marauder", "ESP32-S2", '4MB', '0x1000', 'Marauder/bootloader.bin', '0x8000', 'Marauder/partitions.bin', '0x10000', 'esp32marauderfw'),
            2: ("Save Flipper Blackmagic WiFi settings", "ESP32-S2", '4MB', '0x1000', 'Blackmagic/bootloader.bin', '0x8000', 'Blackmagic/partition-table.bin', '0x10000', 'Blackmagic/blackmagic.bin'),
            3: ("Blackmagic", "ESP32-S2", '4MB', '0x1000', 'Blackmagic/bootloader.bin', '0x8000', 'Blackmagic/partition-table.bin', '0x10000', 'Blackmagic/blackmagic.bin'),
            4: ("Marauder", "ESP32-WROOM", '4MB', '0x1000', 'bootloader.bin', '0x8000', 'partitions.bin', '0x10000', 'espoldhardwarefw'),
            5: ("Marauder", "ESP32 Marauder Mini", '4MB', '0x1000', 'bootloader.bin', '0x8000', 'partitions.bin', '0x10000', 'esp32minifw'),
            6: ("Marauder v6", "ESP32-WROOM", '4MB', '0x1000', 'bootloader.bin', '0x8000', 'partitions.bin', '0x10000', 'espnewhardwarefw'),
            7: ("Marauder", "ESP32-S3", '8MB', '0x0', 'S3/bootloader.bin', '0x8000', 'S3/partitions.bin', '0xE000', 'S3/boot_app0.bin', '0x10000', 'esp32s3fw'),
            8: ("Marauder", "AWOK v1-3 or Duoboard", '4MB', '0x1000', 'bootloader.bin', '0x8000', 'partitions.bin', '0x10000', 'espoldhardwarefw'),
            9: ("Marauder", "AWOK v4 Chungus Board", '4MB', '0x1000', 'Marauder/bootloader.bin', '0x8000', 'Marauder/partitions.bin', '0x10000', 'esp32marauderfw'),
            10: ("Marauder", "AWOK v5 ESP32", '4MB', '0x1000', 'Marauder/bootloader.bin', '0x8000', 'Marauder/partitions.bin', '0x10000', 'esp32marauderfw'),
            11: ("Marauder", "AWOK Dual ESP32 (Orange Port)", '4MB', '0x1000', 'Marauder/bootloader.bin', '0x8000', 'Marauder/partitions.bin', '0x10000', 'esp32marauderfw'),
            12: ("Marauder", "AWOK Dual ESP32 Touch Screen (White Port)", '4MB', '0x1000', 'bootloader.bin', '0x8000', 'partitions.bin', '0x10000', 'espnewhardwarefw'),
            13: ("Marauder Mini", "AWOK Dual ESP32 Mini (White Port)", '4MB', '0x1000', 'bootloader.bin', '0x8000', 'partitions.bin', '0x10000', 'esp32minifw'),
            14: ("Evil Portal", "ESP32-WROOM", '4MB', '0x1000', 'evilportalfwwroom'),
            15: ("Evil Portal", "ESP32-S2", '4MB', '0x1000', 'evilportalfws2'),
            16: ("Erase ESP32", None, None, None, None, None, None, None, None),
            17: ("Update all files", None, None, None, None, None, None, None, None),
            18: ("Exit", None, None, None, None, None, None, None, None)
        }

        if self.fwchoice not in flash_options:
            print(Fore.RED + "Invalid option!" + Style.RESET_ALL)
            exit()

        option = flash_options[self.fwchoice]
        self.selectedfw, self.selectedboard, flashsize, offset_one, bootloader_bin, offset_two, partitions_bin, offset_three, fwbin = option

        if self.fwchoice == 16:
            self.erase_esp32()
        elif self.fwchoice == 17:
            self.update_option()
        elif self.fwchoice == 18:
            print("Exiting!")
            exit()
        else:
            self.checkforserialport()
            eraseparams = ['-p', self.serialport, '-b', self.BR, 'erase_flash']
            flashparams = ['-p', self.serialport, '-b', self.BR, '-c', self.selectedboard, '--before', 'default_reset', '-a', 'no_reset', 'write_flash', '--flash_mode', 'dio', '--flash_freq', '80m', '--flash_size', flashsize, offset_one, bootloader_bin, offset_two, partitions_bin, offset_three, fwbin]
            self.flashtheboard(eraseparams, flashparams)

    def erase_esp32(self):
        """
        Erases the firmware on the ESP32 device.

        This method executes the esptool command to erase the flash memory of the
        connected ESP32 device. It is typically used to prepare the device for
        flashing new firmware.

        Raises:
            RuntimeError: If the esptool command fails to execute.
        """
        self.execute_esptool_command("Erasing firmware...", ['erase_flash'])

    def flashtheboard(self, eraseparams, flashparams):
        """
        Flash the ESP32 board with the specified firmware.

        This method first erases the ESP32 board and then flashes it with the
        provided firmware parameters.

        Args:
            eraseparams (list): Parameters to be used for erasing the ESP32 board.
            flashparams (list): Parameters to be used for flashing the ESP32 board.

        Returns:
            None
        """
        self.erase_esp32()
        self.execute_esptool_command(f"Flashing {self.selectedfw} on {self.selectedboard}", flashparams)

    def execute_esptool_command(self, message, params):
        """
        Executes an esptool command with the given parameters, retrying up to three times in case of failure.

        Args:
            message (str): The message to print before executing the command.
            params (list): The list of parameters to pass to the esptool command.

        Raises:
            Exception: If the command fails after three attempts, an exception is raised and the program exits.

        Prints:
            Success message if the command is executed successfully.
            Error message if the command fails.
        """
        tries = 3
        attempts = 0
        for _ in range(tries):
            try:
                attempts += 1
                print(message)
                esptool.main(params)
                print(Fore.GREEN + f"{self.selectedboard} has been flashed with {self.selectedfw}" + Style.RESET_ALL)
                break
            except Exception as err:
                print(err)
                if attempts == 3:
                    print(f"Could not complete the operation on {self.selectedboard}")
                    exit()
                print("Waiting 5 seconds and trying again...")
                time.sleep(5)

    def update_option(self):
        """
        Updates the firmware options by performing the following steps:

        1. Prints a message indicating the start of the update process.
        2. Deletes specific files and directories related to ESP32Marauder and EvilPortal.
        3. Resets and cleans the local repository of extra ESP32 binaries.
        4. Pulls the latest changes from the remote repository.
        5. Calls the `prereqcheck` method to check prerequisites.
        6. Calls the `choose_fw` method to choose the firmware.

        Raises:
            FileNotFoundError: If any of the specified directories or files do not exist.
            GitCommandError: If there is an issue with the git commands.
        """
        print("Checking for and deleting the files before replacing them...")
        cwd = os.getcwd()
        for paths in Path(cwd).rglob('ESP32Marauder/*/*'):
            os.remove(paths)
        for paths in Path(cwd).rglob('EvilPortal/*'):
            os.remove(paths)
        os.rmdir('ESP32Marauder/releases')
        os.rmdir('ESP32Marauder')
        os.rmdir('EvilPortal')
        extrarepo = os.path.join(cwd, "Extra_ESP32_Bins")
        repo = Repo(extrarepo)
        repo.git.reset('--hard')
        repo.git.clean('-xdf')
        repo.remotes.origin.pull()
        self.prereqcheck()
        self.choose_fw()

    def prereqcheck(self):
        """
        Checks for all necessary prerequisites before proceeding with the flashing process.

        This method performs the following checks:
        1. Downloads and verifies the required firmware.
        2. Checks for the presence of the ESP32 Marauder firmware.
        3. Checks for the S3 binary file.
        4. Checks for the old hardware binary file.
        5. Checks for the mini binary file.
        6. Checks for the new hardware binary file.
        7. Checks for the Evil Portal binary file.

        Raises:
            FirmwareDownloadError: If there is an issue downloading the firmware.
            FileNotFoundError: If any of the required binary files are not found.
        """
        print("Checking for prerequisites...")
        self.firmware_manager.check_and_download()
        self.checkforesp32marauder()
        self.checkfors3bin()
        self.checkforoldhardwarebin()
        self.checkforminibin()
        self.checkfornewhardwarebin()
        self.checkforevilportal()

    def checkforesp32marauder(self):
        """
        Checks for the latest ESP32 Marauder releases and downloads them if not already present.

        This method performs the following steps:
        1. Prints a message indicating that it is checking for Marauder releases.
        2. Checks if the "ESP32Marauder/releases" directory exists.
        3. If the directory does not exist, it prints a message, creates the directory, and downloads the latest releases from the GitHub repository.
        4. Iterates through the assets in the latest release and downloads each asset to the "ESP32Marauder/releases" directory.
        5. Updates the `esp32marauderfw` attribute with the latest firmware file path.

        Raises:
            requests.exceptions.RequestException: If there is an issue with the HTTP request.
            OSError: If there is an issue creating the directory or writing the files.

        """
        print("Checking for Marauder releases")
        if not os.path.exists("ESP32Marauder/releases"):
            print("Marauder releases folder does not exist, but that's okay, downloading them now...")
            os.makedirs('ESP32Marauder/releases')
            marauderapi = "https://api.github.com/repos/justcallmekoko/ESP32Marauder/releases/latest"
            response = requests.get(marauderapi, timeout=10)
            jsondata = response.json()
            for assetdl in jsondata['assets']:
                marauderasset = assetdl['browser_download_url']
                filename = marauderasset.rsplit('/', 1)[1]
                downloadfile = requests.get(marauderasset, allow_redirects=True, timeout=10)
                open(f'ESP32Marauder/releases/{filename}', 'wb').write(downloadfile.content)
        self.esp32marauderfw = self.firmware_manager.get_latest_firmware('ESP32Marauder/releases/esp32_marauder_v*_flipper.bin')

    def checkforevilportal(self):
        """
        Checks for the existence of the 'EvilPortal' directory and downloads necessary files if not present.

        This method performs the following steps:
        1. Prints a message indicating the check for the 'EvilPortal' directory.
        2. If the 'EvilPortal' directory does not exist:
            a. Prints a message indicating the directory is not found and will be downloaded.
            b. Creates the 'EvilPortal' directory.
            c. Downloads the 'Evil Portal WROOM' binary file from a specified URL and saves it in the 'EvilPortal' directory.
            d. Downloads the 'Evil Portal WiFi Board or S2' binary file from a specified URL and saves it in the 'EvilPortal' directory.
        3. Sets the paths to the downloaded binary files as instance variables.

        Raises:
            requests.exceptions.RequestException: If there is an issue with downloading the files.
        """
        print("Checking for Evil portal")
        if not os.path.exists('EvilPortal'):
            print("Evil Portal folder not found, but that's okay, downloading it now")
            os.makedirs('EvilPortal')
            evilportalwroomurl = "https://github.com/bigbrodude6119/flipper-zero-evil-portal/raw/main/Single%20File%20Bins/Evil%20Portal%20WROOM.bin"
            downloadfile = requests.get(evilportalwroomurl, timeout=10)
            open("EvilPortal/EvilPortalWROOM.bin", 'wb').write(downloadfile.content)
            evilportals2url = "https://github.com/bigbrodude6119/flipper-zero-evil-portal/raw/main/Single%20File%20Bins/Evil%20Portal%20WiFi%20Board%20or%20S2.bin"
            downloadfile = requests.get(evilportals2url, timeout=10)
            open("EvilPortal/EvilPortalS2.bin", 'wb').write(downloadfile.content)
        self.evilportalfwwroom = "EvilPortal/EvilPortalWROOM.bin"
        self.evilportalfws2 = "EvilPortal/EvilPortalS2.bin"

    def checkfors3bin(self):
        """
        Checks for the latest ESP32 Marauder firmware binary for the S3 model.

        This method queries the firmware manager to retrieve the latest firmware
        binary file that matches the pattern 'ESP32Marauder/releases/esp32_marauder_v*ultiboardS3.bin'.
        The retrieved firmware is then assigned to the instance variable `esp32s3fw`.

        Returns:
            None
        """
        self.esp32s3fw = self.firmware_manager.get_latest_firmware('ESP32Marauder/releases/esp32_marauder_v*ultiboardS3.bin')

    def checkforoldhardwarebin(self):
        """
        Checks for the latest firmware binary for old ESP32 Marauder hardware.

        This method queries the firmware manager to get the latest firmware
        binary file that matches the pattern 'ESP32Marauder/releases/esp32_marauder_v*_old_hardware.bin'.

        Sets the `espoldhardwarefw` attribute to the path of the latest firmware binary.

        Returns:
            None
        """
        self.espoldhardwarefw = self.firmware_manager.get_latest_firmware('ESP32Marauder/releases/esp32_marauder_v*_old_hardware.bin')

    def checkforminibin(self):
        """
        Checks for the latest ESP32 Marauder mini firmware binary.

        This method uses the firmware manager to retrieve the latest firmware
        binary file that matches the pattern 'ESP32Marauder/releases/esp32_marauder_v*_mini.bin'.
        The retrieved firmware is then assigned to the instance variable `esp32minifw`.

        Returns:
            None
        """
        self.esp32minifw = self.firmware_manager.get_latest_firmware('ESP32Marauder/releases/esp32_marauder_v*_mini.bin')

    def checkfornewhardwarebin(self):
        """
        Checks for the latest ESP32 Marauder hardware firmware binary.

        This method queries the firmware manager to get the latest firmware
        binary file matching the pattern 'ESP32Marauder/releases/esp32_marauder_v*_v6.bin'.
        The result is stored in the instance variable `espnewhardwarefw`.

        Returns:
            None
        """
        self.espnewhardwarefw = self.firmware_manager.get_latest_firmware('ESP32Marauder/releases/esp32_marauder_v*_v6.bin')

