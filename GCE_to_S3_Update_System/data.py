"""Database Connection Configurations

Configuration for database connections

Read, setup, and prepare database connection libraries

"""

__author__ = 'Koan Briggs'

# DB Imports
from base import ConfigBase

def UniformDirectory(Directory:str) -> str:
    # noinspection PyTypeChecker
    """
        Set uniform presence of tailing slash for directory paths. Tracking errors in these is a pain.

        Standard: Switch to Unix style slashes and always leave a single valid trailing slash, unless string is empty.

        Leave a single trailing slash, do nothing if there is already one.

        >>> UniformDirectory('/directory/  ')
        '/directory/'

        >>> UniformDirectory('directory/  ')
        'directory/'

        >>> UniformDirectory('/directory  ')
        '/directory/'

        >>> UniformDirectory('/directory//  ')
        '/directory/'

        >>> UniformDirectory(r"\win_directory\")
        '/win_directory/'

        >>> UniformDirectory(r"C:\directory\other_directory")
        'C:/directory/other_directory/'

        >>> UniformDirectory('')
        Traceback (most recent call last):
        ValueError: Blank string is not a valid directory.

        >>> UniformDirectory('/')
        '/'

        >>> UniformDirectory('//')
        '/'

        >>> UniformDirectory(5)
        Traceback (most recent call last):
        TypeError: Directory should be passed as a string.

        :param Directory: str
        :return: str
        """
    # print(f'Initial Uniform Directory Entry: {Directory}')
    if type(Directory) != str:
        raise TypeError("Directory should be passed as a string.")
    if Directory == "":
        raise ValueError("Blank string is not a valid directory.")
    if Directory == '//':
        return '/'
    if Directory.startswith(r'/') or Directory.startswith('\\'):
        Absolute = True
    else:
        Absolute = True
    SplitDirectory = Directory.replace('\\','/').rstrip().rstrip('/').split('/')
    if len(Directory) == 0:
        return '/'
    JoinedDirectory = '/'.join(SplitDirectory).rstrip('/')+'/'
    if not Absolute:
        JoinedDirectory = JoinedDirectory.lstrip('/')
    # print(f'Returned Uniform Directory Entry: {JoinedDirectory}')
    return JoinedDirectory

def StitchFilenameAndPath(Filename: str, Path:str = "") -> str:
    """
    Combines Filename and Path together in a uniform way.

    >>> StitchFilenameAndPath('filename.ext','/directory/')
    '/directory/filename.ext'

    >>> StitchFilenameAndPath('filename.ext','/directory//')
    '/directory/filename.ext'

    >>> StitchFilenameAndPath('filename.ext','/')
    '/filename.ext'

    >>> StitchFilenameAndPath('filename.ext')
    'filename.ext'

    :param Filename: str
    :param Path: str
    :return: str
    """
    if Path:
        return f"{UniformDirectory(Path)}{Filename}"
    return Filename


# File handles
from io import BytesIO, FileIO
from zipfile import ZipFile
from _io import BufferedReader

def ConvertToStandardBinaryStream(FileObject):
    if type(FileObject) == bytes:
        FileObject = BytesIO(FileObject)
    elif type(FileObject) == BufferedReader:
        FileObject = BufferedReader(FileObject)
    elif type(FileObject) == str:
        FileIOHolder = FileIO(FileObject, 'rb')
        FileObject = BufferedReader(FileIOHolder)
    return FileObject

class FileHandleBase(object):
    def __init__(self, FileObject, *args, **kargs):
        super(FileHandleBase, self).__init__(*args, **kargs)
        self.FileObject = ConvertToStandardBinaryStream(FileObject)

class ZipFileHandle(FileHandleBase):
    def __init__(self, FileObject, *args, **kargs):
        super(ZipFileHandle, self).__init__(FileObject, *args, **kargs)
        self.FileObject = ZipFile(self.FileObject)

    def ArchiveFileList(self):
        FileList = [y for y in sorted(self.FileObject.namelist())]
        return FileList

# S3 Imports
import boto3
import botocore
import warnings

def S3PathLeadingSlashFix(Path:str):
    return Path.lstrip('/')

def keys(s3_paginator, bucket_name, prefix='/', delimiter='/', start_after=''):
    prefix = prefix[1:] if prefix.startswith(delimiter) else prefix
    start_after = (start_after or prefix) if prefix.endswith(delimiter) else start_after
    for page in s3_paginator.paginate(Bucket=bucket_name, Prefix=prefix, StartAfter=start_after):
        for content in page.get('Contents', ()):
            yield content['Key']

class S3Connector(object):
    def __init__(self, *args, Config = '', **kargs):
        """
        Note: Config is not currently in use, S3 access credentials will almost certainly be needed in the future.
        Config defaults to the built-in config unless an alternate config is passed.

        :param args:
        :param Config:
        :param kargs:
        """
        if Config == '':
            Config = ConfigBase()
        super(S3Connector, self).__init__(*args, **kargs)

        # S3 client does not always close out the SSL request cleanly, this is especially problematic for tests
        warnings.filterwarnings(action="ignore", message="unclosed",category=ResourceWarning)
        # Not optimal, but it works for now.

        self.Config = Config.LoadConfig()
        try:
            self.S3Session = boto3.session.Session(
                aws_access_key_id=self.Config['s3']['aws_access_key_id'],
                aws_secret_access_key=self.Config['s3']['aws_secret_access_key']
            )
        except:
            # TODO: reduce to minimal exception
            self.S3Session = boto3.session.Session()

        self.S3Client = self.S3Session.client('s3')
        self.S3Resource = self.S3Session.resource('s3')

    def S3GetFileObject(self, S3Bucket, S3Filename, S3Path=""):
        S3FilenameWPath = S3PathLeadingSlashFix(StitchFilenameAndPath(S3Filename,S3Path))
        S3Object = self.S3Client.get_object(Bucket=S3Bucket, Key=S3FilenameWPath)
        if not S3Object['ResponseMetadata']['HTTPStatusCode'] == 200:
            raise ValueError
        FileData = S3Object['Body'].read()
        return FileData

    def S3GetFilesIn(self, bucket_name, prefix='/', delimiter='/', start_after=''):
        return keys(self.S3Client.get_paginator('list_objects_v2'), bucket_name, prefix, delimiter, start_after)

    def S3CheckObject(self, S3Bucket: str, S3Filename: str, S3Path:str = "") -> bool:
        """
        bucket=msd-gis-raw
        path=USBoundaries/
        CountyDataFilename = cb_2017_us_county_500k.zip
        StateDataFilename  = cb_2017_us_state_500k.zip

        >>> S3 = S3Connector()
        >>> S3.S3CheckObject("msd-gis-raw", "cb_2017_us_county_500k.zip", "USBoundaries/")
        True

        >>> S3 = S3Connector()
        >>> S3.S3CheckObject("msd-gis-raw", "USBoundaries/cb_2017_us_county_500k.zip")
        True

        >>> S3 = S3Connector()
        >>> S3.S3CheckObject("msd-gis-raw", "invalid_path/cb_2017_us_county_500k.zip")
        False

        >>> S3 = S3Connector()
        >>> S3.S3CheckObject("invalid_bucket", "invalid_path/cb_2017_us_county_500k.zip")
        False

        >>> S3 = S3Connector()
        >>> S3.S3CheckObject("msd-gis-raw", "invalid_path/cb_2017_us_county_500k.zip", "USBoundaries/")
        False

        :param S3Bucket: str
        :param S3Filename: str
        :param S3Path: str
        :return: bool
        """
        S3FilenameWPath = S3PathLeadingSlashFix(StitchFilenameAndPath(S3Filename,S3Path))
        try:
            self.S3Resource.Object(S3Bucket, S3FilenameWPath).load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
        return True

    def S3PutFileObject(self, S3Bucket, S3Filename, S3Path, BinaryObject, Overwrite=False):
        S3FilenameWPath = S3PathLeadingSlashFix(StitchFilenameAndPath(S3Filename, S3Path))
        if not Overwrite and self.S3CheckObject(S3Bucket, S3Filename, S3Path):
            raise FileExistsError
        self.S3Client.upload_fileobj(BinaryObject, S3Bucket, S3FilenameWPath)

    def _S3DeleteObject(self, S3Bucket, S3Key):
        if not self.S3CheckObject(S3Bucket, S3Key):
            raise FileNotFoundError('Attempting to remove S3 Object which does not exist.')
        Target = self.S3Resource.Object(S3Bucket, S3Key)
        Target.delete()

    def S3DeleteFolder(self, S3Bucket, S3Path):
        S3Key = S3PathLeadingSlashFix(StitchFilenameAndPath("", S3Path))
        self._S3DeleteObject(S3Bucket, S3Key)

    def S3DeleteFile(self, S3Bucket, S3Filename, S3Path):
        if S3Filename == '':
            raise FileNotFoundError("Filename can't be blank")
        S3Key = S3PathLeadingSlashFix(StitchFilenameAndPath(S3Filename, S3Path))
        self._S3DeleteObject(S3Bucket, S3Key)

    def S3CreateFolder(self, S3Bucket, S3Path):
        S3Key = S3PathLeadingSlashFix(StitchFilenameAndPath("", S3Path))
        if self.S3CheckObject(S3Bucket, S3Key):
            raise FileExistsError(f"There is already an S3 object at the location: {S3Path}")
        Target = self.S3Resource.Object(S3Bucket, S3Key)
        Target.put()

if __name__ == '__main__':
    pass