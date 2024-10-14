"""General Functions

Helper functions for pyYield

"""

__author__ = 'Koan Briggs'

def Flatten(list_to_be_flattened: list):
    """
    Flattens lists of lists.
    """
    return [item for sublist in list_to_be_flattened for item in sublist]

import time

def PrettyTimeDelta(seconds):
    """
    Print pretty version of time from seconds.

    >>> PrettyTimeDelta(0.001)
    '0.001s'

    >>> PrettyTimeDelta(1.0)
    '1.000s'

    >>> PrettyTimeDelta(60.0)
    '1m0.000s'

    >>> PrettyTimeDelta(3660.01)
    '1h1m0.010s'

    >>> PrettyTimeDelta(-3660.01)
    '-1h1m0.010s'

    :param seconds:
    :return:
    """
    sign_string = '-' if seconds < 0 else ''
    seconds = abs(seconds)
    fsecs = seconds
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    seconds = fsecs - minutes*60 - hours*3600 - days*216000
    if days > 0:
        return f'{sign_string:s}{days:.0f}d{hours:.0f}h{minutes:.0f}m{seconds:.3f}s'
    elif hours > 0:
        return f'{sign_string:s}{hours:.0f}h{minutes:.0f}m{seconds:.3f}s'
    elif minutes > 0:
        return f'{sign_string:s}{minutes:.0f}m{seconds:.3f}s'
    else:
        return f'{sign_string:s}{seconds:.3f}s'

def FormatByteSizeStr(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti']:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0

def FileExtension(Filename: str):
    """
    Uniform method for returning just the file extension for a filename.
    :param Filename: str
    :return: str
    """
    return Filename.split('.')[-1].lower()

def FileNameWOExtension(Filename: str, LeavePath = False):
    """
    Uniform method for returning just the primary name portion of a filename.
    :param LeavePath: bool
    :param Filename: str
    :return: str
    """
    if not LeavePath:
        FilenameWOPath = Filename.split('/')[-1].split('\\')[-1]
    else:
        FilenameWOPath = Filename
    return ''.join(FilenameWOPath.split('.')[:-1])

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
