from google.cloud import storage
import sys
from data import S3Connector, ConfigBase, ConvertToStandardBinaryStream, ZipFileHandle
from configparser import ConfigParser
import os
import os.path
import hashlib
import fnmatch
from io import BytesIO
from collections import OrderedDict
import time
import requests
from json import dumps
from datetime import datetime

EnvConfig = ConfigParser(os.environ)

# Running Env
try:
    # "Prod" or "Stage" Set using Env variables within the container, can be passed by the task
    DevLevel = EnvConfig['DEFAULT']['DevLevel']
except KeyError as e:
    # Probably best to default to Stage
    DevLevel = "Stage"
    print(f'Environmental Variable ({e}) not found, default to: {DevLevel}')

try:
    # Set config file
    ConfigFile = EnvConfig['DEFAULT']['ConfigFile']
except KeyError as e:
    # Probably best to default to Stage
    ConfigFile = "primary.ini"
    print(f'Config File Variable ({e}) not found, default to: {ConfigFile}')

CurrentConfig = ConfigBase(
    ConfigDir='./',
    ConfigFile=ConfigFile
)
ConfigData = CurrentConfig.LoadConfig()

# General Settings
Verbosity = int(ConfigData['system']['verbosity'])
if ConfigData['system']['flatten'] == 'True':
    Flatten = True
elif ConfigData['system']['flatten'] == 'False':
    Flatten = False
else:
    Flatten = True

try:
    Archive = ConfigData['system']['archive']
except KeyError as e:
    Archive = False

if ConfigData['system']['unzip_targets'] == 'True':
    UnZip = True
elif ConfigData['system']['unzip_targets'] == 'False':
    UnZip = False
else:
    UnZip = False

if ConfigData['system']['strip_prefix'] == 'True':
    StripPrefix = True
elif ConfigData['system']['strip_prefix'] == 'False':
    StripPrefix = False
else:
    StripPrefix = False

try:
    if ConfigData['system']['update'] == 'True':
        Update = True
    elif ConfigData['system']['update'] == 'False':
        Update = False
    else:
        Update = True
except:
    Update = True

try:
    if ConfigData['system']['fake_thumbnails'] == 'True':
        CreateFakeThumbnails = True
    elif ConfigData['system']['fake_thumbnails'] == 'False':
        CreateFakeThumbnails = False
    else:
        CreateFakeThumbnails = False
except:
    CreateFakeThumbnails = False

try:
    if ConfigData['system']['wordpress_modification_for_s3_upload_plugin'] == 'True':
        WPHack = True
    elif ConfigData['system']['wordpress_modification_for_s3_upload_plugin'] == 'False':
        WPHack = False
    else:
        WPHack = False
except:
    WPHack = False

if type(ConfigData['slack']['task_log']) == str :
    SlackTaskLog = ConfigData['slack']['task_log']
else:
    SlackTaskLog = ""


# Google
GCEAccessKey = 'key/'+ConfigData['gce']['gce_access_key_file']
GCEBucket = ConfigData['gce']['bucket']
GCEPath = ConfigData['gce']['path'].split(',')
GCEPath = [x.strip() for x in GCEPath]
GCEFiles = ConfigData['gce']['files'].split(',')
GCEFiles = [x.strip() for x in GCEFiles]

# AWS
if DevLevel == 'Stage':
    S3TargetBucket = ConfigData['s3']['stage_bucket']
    S3ArchiveTargetBucket = ConfigData['s3']['stage_archive']
    S3ArchiveTargetDir = ConfigData['s3']['stage_archive_dir']
    S3TargetPath   = ConfigData['s3']['stage_path']
    S3HashLocation = ConfigData['s3']['stage_secret']

elif DevLevel == 'Prod':
    S3TargetBucket = ConfigData['s3']['prod_bucket']
    S3ArchiveTargetBucket = ConfigData['s3']['prod_archive']
    S3ArchiveTargetDir = ConfigData['s3']['prod_archive_dir']
    S3TargetPath   = ConfigData['s3']['prod_path']
    S3HashLocation = ConfigData['s3']['prod_secret']
else:
    S3TargetBucket = ''
    S3TargetPath   = ''
    S3HashLocation = ''

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def create_path_to_file(filename_w_path):
    dirs = []
    for directory in filename_w_path.split('/')[:-1]:
        dirs.append(directory)
        try:
            os.mkdir('/'.join(dirs)+'/')
        except FileExistsError:
            pass
        except FileNotFoundError:
            pass

def S3Confirm(
        Connector,
        CTargetBucket,
        CFileName,
        CTargetPath,
        ExpectedHash
):
    MemFile = Connector.S3GetFileObject(
        CTargetBucket,
        CFileName,
        CTargetPath
    )

    Hash = hashlib.md5(MemFile).hexdigest()
    if Hash == ExpectedHash:
        return True, Hash
    return False, Hash



def S3PutAndConfirm(Connector,
                    CTargetBucket,
                    CFileName,
                    CTargetPath,
                    UpdateData,
                    ExpectedHash='',
                    Entry='',
                    SkipHashCheck = False
                    ):
    if not Update:
        if Verbosity >= 10: print('Updating Disabled in Config')
        return False

    Connector.S3PutFileObject(
        CTargetBucket,
        CFileName,
        CTargetPath,
        ConvertToStandardBinaryStream(UpdateData),
        Overwrite=True
    )
    Match, NewHash = S3Confirm(
        Connector,
        CTargetBucket,
        CFileName,
        CTargetPath,
        ExpectedHash
    )
    if not SkipHashCheck:
        if not Match:
            if Verbosity >= 10: print('Update failed!!!')

            raise Exception
        else:
            if Verbosity >= 10: print(f"{NewHash} : {Entry} Done and confirmed")
    else:
        if Verbosity >= 10: print(f"{NewHash} : {Entry} Done and hash check skipped")


def S3UnZipAndPut(Connector,
                    CTargetBucket,
                    CFileNames,
                    CTargetPath,
                    ):
    ArchiveExtensions = ['.zip']
    for PotentialArchive in CFileNames:
        if os.path.splitext(PotentialArchive)[1] in ArchiveExtensions:
            Archive = ZipFileHandle(GCECurrentFiles[PotentialArchive]['data'])
        else:
            continue
        for FileName in Archive.ArchiveFileList():
            if WPHack:
                CTargetPath = ""
                FileNameOrig = FileName
                PrimaryOrigDir = "/".join(FileName.split('/')[:-1]) + "/"
                FileName = FileName.split('/')[-1]
            S3PutAndConfirm(
                Connector,
                CTargetBucket,
                FileName,
                CTargetPath,
                Archive.FileObject.read(FileName),
                ExpectedHash='',
                Entry=f'{FileName} extracted from {PotentialArchive}',
                SkipHashCheck=True
            )
            if CreateFakeThumbnails:
                for ExistingFileName in FilesInS3Bucket:
                    if WPHack:
                        ExistingFileNameOrig = ExistingFileName
                        OrigDir = "/".join(ExistingFileName.split('/')[:-1])+"/"
                        ExistingFileName = ExistingFileName.split('/')[-1]

                    File = os.path.splitext(ExistingFileName)[0]
                    FileExt = os.path.splitext(ExistingFileName)[1]
                    try:
                        Res = File.split('-')[-1].split('x')
                        PrimaryFilename = '-'.join(File.split('-')[:-1]) + FileExt
                        if len(Res) == 2 and int(Res[0]) and int(Res[1]):
                            if PrimaryFilename == FileName:
                                print(f'Current Thumbnail Filename: {ExistingFileName}')
                                S3PutAndConfirm(
                                    Connector,
                                    CTargetBucket,
                                    ExistingFileName,
                                    CTargetPath,
                                    Archive.FileObject.read(FileName),
                                    ExpectedHash='',
                                    Entry=f'{ExistingFileName} thumbnail overwritten from {PotentialArchive}',
                                    SkipHashCheck=True
                                )
                    except:
                        continue

if __name__ == '__main__':
    S3 = S3Connector(Config=CurrentConfig)
    if Verbosity >= 10: print(DevLevel)
    if Verbosity >= 10: print(f"Version: {ConfigData['system']['version']}")
    sys.stdout.flush()
    if Verbosity >= 10: print('------------------')
    SlackURL = ConfigData['slack']['url']

    if CreateFakeThumbnails:
        FilesInS3Bucket = [
            x for x in S3.S3GetFilesIn(
                S3TargetBucket,
                S3TargetPath
            )]

    Payload = dict()
    Payload["text"] = f"Update from: {DevLevel}"
    Payload["attachments"] = []
    try:
        if Verbosity >= 10: print(f'Starting update at: {time.asctime()} in timezone: {time.strftime("%Z")}')
        GC = storage.Client.from_service_account_json(GCEAccessKey)
        GCB = GC.bucket(GCEBucket)

        blobs = []
        for Path in GCEPath:
            blobs.extend(GCB.list_blobs(prefix=Path))

        GCECurrentFiles = OrderedDict()
        for blob in blobs:
            if any([fnmatch.fnmatch(blob.name, x) for x in GCEFiles]):
                GCEMemFile = BytesIO()
                GCB.get_blob(blob.name).download_to_file(GCEMemFile)
                GCEMemFile.seek(0)
                GCECurrentFiles[blob.name] = OrderedDict()
                GCECurrentFiles[blob.name]['hash'] = hashlib.md5(bytes(GCEMemFile.read())).hexdigest()
                GCEMemFile.seek(0)
                GCECurrentFiles[blob.name]['data'] = GCEMemFile.read()
                GCECurrentFiles[blob.name]['created_time'] = blob.time_created
                GCECurrentFiles[blob.name]['file_size'] = blob.size
                if Verbosity >= 10: print(f"GCE | Bucket: {GCB.name} Hash: {GCECurrentFiles[blob.name]['hash']} File: {blob.name}")

        S3CurrentFiles = OrderedDict()
        for FileName, Data in GCECurrentFiles.items():
            S3FileName = FileName.replace('\\', '/')
            if StripPrefix:
                S3FileName = S3FileName.split('/')[-1]
            if Flatten:
                S3FileName = S3FileName.replace('/','_')

            S3ArchiveFileName = f"{S3FileName.split('.')[:-1][0] if '.' in S3FileName else S3FileName}{'_'}{GCECurrentFiles[FileName]['created_time'].strftime('%Y-%m-%d-%H-%M-%S-%Z')}{'.'+S3FileName.split('.')[-1] if '.' in S3FileName else ''}"

            if not S3.S3CheckObject(
                    S3TargetBucket,
                    S3FileName,
                    S3TargetPath
            ):
                S3PutAndConfirm(
                    S3,
                    S3TargetBucket,
                    S3FileName,
                    S3TargetPath,
                    GCECurrentFiles[FileName]['data'],
                    GCECurrentFiles[FileName]['hash'],
                    "New File"
                )
                if UnZip:
                    S3UnZipAndPut(S3,
                                  S3TargetBucket,
                                  GCECurrentFiles.keys(),
                                  S3TargetPath,
                                  )
                if Archive:
                    S3PutAndConfirm(
                        S3,
                        S3ArchiveTargetBucket,
                        S3ArchiveFileName,
                        S3ArchiveTargetDir,
                        GCECurrentFiles[FileName]['data'],
                        GCECurrentFiles[FileName]['hash'],
                        "New File (Archive)"
                    )
                CAttachment = dict()
                CAttachment["color"] = "good"
                CAttachment["title"] = f"New File Found: {S3FileName}"
                CAttachment["text"] = f"File size: {sizeof_fmt(GCECurrentFiles[FileName]['file_size'])}"
                CAttachment["text"] += f"\nFile hash: {GCECurrentFiles[FileName]['hash']}"
                CAttachment[
                    "title_link"] = SlackTaskLog
                CAttachment["ts"] = datetime.timestamp(GCECurrentFiles[FileName]['created_time'])
                Payload["attachments"].append(CAttachment)

                continue

            S3MemFile = S3.S3GetFileObject(
                S3TargetBucket,
                S3FileName,
                S3TargetPath
            )
            S3CurrentFiles[FileName] = OrderedDict()
            S3CurrentFiles[FileName]['hash'] = hashlib.md5(S3MemFile).hexdigest()
            S3CurrentFiles[FileName]['data'] = S3MemFile

            if Verbosity >= 10: print(f"S3  | Bucket: {S3TargetBucket} Hash: {S3CurrentFiles[FileName]['hash']} Path: {S3TargetPath} File: {FileName}")

            if Verbosity >= 10: print(f"Hash match: {GCECurrentFiles[FileName]['hash'] == S3CurrentFiles[FileName]['hash']}")
            if GCECurrentFiles[FileName]['hash'] != S3CurrentFiles[FileName]['hash']:
                if Verbosity >= 10: print(f"Archiving: {S3FileName} Hash: {S3CurrentFiles[FileName]['hash']} -> {S3ArchiveFileName} in {S3ArchiveTargetBucket}")

                if Verbosity >= 10: print(f"Updating... {S3FileName} from {S3CurrentFiles[FileName]['hash']} -> ")

                S3PutAndConfirm(
                    S3,
                    S3TargetBucket,
                    S3FileName,
                    S3TargetPath,
                    GCECurrentFiles[FileName]['data'],
                    GCECurrentFiles[FileName]['hash'],
                    "Primary"
                )
                if UnZip:
                    S3UnZipAndPut(S3,
                                  S3TargetBucket,
                                  GCECurrentFiles.keys(),
                                  S3TargetBucket,
                                  )

                if Archive:
                    S3PutAndConfirm(
                        S3,
                        S3ArchiveTargetBucket,
                        S3ArchiveFileName,
                        S3ArchiveTargetDir,
                        GCECurrentFiles[FileName]['data'],
                        GCECurrentFiles[FileName]['hash'],
                        "Archive"
                    )
                CAttachment = dict()
                CAttachment["color"] = "good"
                CAttachment["title"] = f"File updated: {S3FileName}"
                CAttachment["text"] = f"File size: {sizeof_fmt(GCECurrentFiles[FileName]['file_size'])}"
                CAttachment["text"] += f"\nFile hash: {GCECurrentFiles[FileName]['hash']}"
                CAttachment[
                    "title_link"] = SlackTaskLog
                CAttachment["ts"] = datetime.timestamp(GCECurrentFiles[FileName]['created_time'])
                Payload["attachments"].append(CAttachment)

        DangerEntries = []
        WarningEntries = []
        GoodEntries = []
        OtherEntries = []
        for Entry in Payload['attachments']:
            if Entry['color'] == 'good':
                GoodEntries.append(Entry)
            elif Entry['color'] == 'warning':
                WarningEntries.append(Entry)
            elif Entry['color'] == 'danger':
                DangerEntries.append(Entry)
            else:
                OtherEntries.append(Entry)

        Payload["attachments"] = []
        Payload["attachments"].extend(DangerEntries)
        Payload["attachments"].extend(WarningEntries)
        Payload["attachments"].extend(GoodEntries)
        Payload["attachments"].extend(OtherEntries)
        if DevLevel == 'Prod' and len(Payload["attachments"]) > 0:
            response = requests.post(
                SlackURL,
                data=dumps(Payload),
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code != 200:
                if Verbosity >= 10: print("Error posting the message to slack, response wasn't 200")
            else:
                if Verbosity >= 10: print("Slack message, sent.")
        if Verbosity >= 10: print("Done")
        sys.stdout.flush()

    except Exception as e:
        CAttachment = dict()
        CAttachment["color"] = "danger"
        CAttachment["title"] = "Something Failed, Check Task Configuration!"
        CAttachment["title_link"] = "https://us-east-2.console.aws.amazon.com/ecs/home?region=us-east-2#/clusters/PWY-Google-to-S3/scheduledTasks"
        CAttachment["text"] = "Post in this channel when you have resolved the issue.\n"
        CAttachment["text"] += f" Exception: {e}"
        CAttachment["pretext"] = "<!channel>"
        CAttachment["ts"] = time.time()

        EmergencyPayload = [CAttachment]
        EmergencyPayload.extend(Payload["attachments"])
        Payload["attachments"] = EmergencyPayload

        response = requests.post(
            SlackURL,
            data=dumps(Payload),
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code != 200:
            if Verbosity >= 10: print("Error posting the message to slack, response wasn't 200")
        else:
            if Verbosity >= 10: print("Slack message, sent.")


        if Verbosity >= 10: print("Done")
        sys.stdout.flush()


