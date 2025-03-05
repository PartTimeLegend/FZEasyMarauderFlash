import glob
import os

from git import Repo


class FirmwareManager:
    """
    A class to manage firmware files from a remote repository.

    Attributes:
        repo_url (str): The URL of the remote repository.
        local_dir (str): The local directory to store the firmware files.

    Methods:
        check_and_download():
            Checks if the local directory exists, and if not, creates it and clones the repository.

        get_latest_firmware(pattern):
            Retrieves the latest firmware file matching the given pattern.
            Args:
                pattern (str): The glob pattern to match firmware files.
            Returns:
                str: The path to the latest firmware file, or None if no files are found.
    """
    def __init__(self, repo_url, local_dir):
        self.repo_url = repo_url
        self.local_dir = local_dir

    def check_and_download(self):
        """
        Checks if the local directory exists and downloads the repository if it does not.

        This method checks if the directory specified by `self.local_dir` exists. If the directory
        does not exist, it prints a message indicating that the directory will be downloaded,
        creates the directory, and clones the repository from `self.repo_url` into the newly
        created directory. If the directory already exists, it prints a message indicating that
        the directory is already present.

        Raises:
            OSError: If the directory cannot be created.
            git.exc.GitError: If there is an error cloning the repository.
        """
        if not os.path.exists(self.local_dir):
            print(f"{self.local_dir} folder does not exist, downloading now...")
            os.makedirs(self.local_dir)
            Repo.clone_from(self.repo_url, self.local_dir)
        else:
            print(f"{self.local_dir} folder exists!")

    def get_latest_firmware(self, pattern):
        """
        Retrieve the latest firmware file matching the given pattern.

        This method searches for firmware files that match the specified
        pattern using the glob module, and returns the most recently
        created file based on its creation time.

        Args:
            pattern (str): The glob pattern to search for firmware files.

        Returns:
            str: The path to the latest firmware file if found, otherwise None.
        """
        firmware_files = glob.glob(pattern)
        if not firmware_files:
            print(f"No firmware files found for pattern: {pattern}")
            return None
        latest_firmware = max(firmware_files, key=os.path.getctime)
        print(f"Latest firmware found: {latest_firmware}")
        return latest_firmware
