"""Primary Configuration System

Base classes and environment detection for configuration. Code will be initialized in a variety of environments,
so maintenance of configuration will be of heightened importance.

"""

__author__ = 'Koan Briggs'

# Primary Imports
from configparser import ConfigParser
from os.path import isdir, isfile, dirname, abspath
from os import walk
from funcs import UniformDirectory, StitchFilenameAndPath

AbsDir = UniformDirectory(dirname(abspath(__file__)))

class ConfigBase(object):
    ConfigDir: str
    ConfigFile: str

    def __init__(self, ConfigDir: str = "", ConfigFile: str = "", *args, **kargs):
        super(ConfigBase, self).__init__(*args, **kargs)
        # Set Initial and Default Values
        if ConfigDir != "":
            self.SetConfigDir(ConfigDir)
        else:
            DefaultConfigDir = f"{AbsDir}../../config_files/"
            self.SetConfigDir(DefaultConfigDir)
        if ConfigFile != "":
            self.SetConfigFile(ConfigFile)
        else:
            DefaultConfigFile = "primary.ini"
            self.SetConfigFile(DefaultConfigFile)

        # Instantiate Central Config Parser and load initial data
        self.Config = ConfigParser()
        self.LoadConfig()

    def SetConfigDir(self, ConfigDir: str):
        """
        Set the directory which contains the configuration files.
        Does NOT update the config, run LoadConfig after setting File and Dir.

        This is only for changing the directory if you are keeping the same config file:
        Use SetConfigPath is you want to change both the file and path.

        :param ConfigDir: str
        :return:
        """
        self.ConfigDir = UniformDirectory(ConfigDir)

    def SetConfigPath(self, ConfigDir: str = "", ConfigFile: str = ""):
        """
        Set the config file and directory and updates the config.

        :param ConfigDir: str
        :param ConfigFile: str
        :return:
        """
        self.SetConfigDir(ConfigDir)
        self.SetConfigFile(ConfigFile)
        self.LoadConfig()

    def SetConfigFile(self, ConfigFile: str):
        """
        Set the configuration file for the Config object.
        Does NOT update the config, run LoadConfig after setting File and Dir.

        :param ConfigFile:
        :return:
        """
        self.ConfigFile = ConfigFile

    @property
    def ConfigFileFullPath(self):
        return StitchFilenameAndPath(self.ConfigFile, self.ConfigDir)

    def PrintPathSpace(self):
        print(f"Current Config File DIR : {self.ConfigDir}")
        print("----- Config Files -----")
        [print(x) for x in walk(self.ConfigDir)]
        print("------------------------")
        print(f"Current Path: {self.ConfigDir}")
        print(f"Current File: {self.ConfigFile}")
        print(f"Current Full: {self.ConfigFileFullPath}")
        print("------------------------")
        return None

    def LoadConfig(self):
        if not isdir(self.ConfigDir): raise NotADirectoryError(self.ConfigDir)
        if not isfile(self.ConfigFileFullPath): raise FileNotFoundError(self.ConfigFileFullPath)
        self.Config.read(self.ConfigFileFullPath)
        return self.Config

if __name__ == '__main__':
    pass