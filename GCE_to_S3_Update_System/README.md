# GCE to S3 File Transfer with optional Wordpress thumbnail image generation and posting
- Data Science

Author: Koan Briggs

Status: Inactive (Multiple copies were in production for several years)

Current Setup:
- Runs in: AWS ECS Cluster
    - Fargate Instances
    - As a scheduled task
    - Production/Staging determined by ENV var "DevLevel" in task configuration:
      - DevLevel = Stage
      - DevLevel = Prod
 - Output logs are maintained in Cloudwatch
 
 Setup requirements:
 - primary.ini config file should be created and filled in from template_primary.ini
 - GCE private key should be added to key directory
 - wordpress_modification_for_s3_upload_plugin (config variable): s3 upload plugin likes having all of its files in the root of the directory. 
    - Required for a downstream task that uploads thumbnail images to wordpress for the marketing team.
 - Beware: Turning off the Wordpress modification, thumbnail detection on and directories structures DO NOT mix well. If creating or modifying directory structures in the system always check carefully that the system works. Make cause infinite directory recursion errors or files created in directories closer to root than expected. This is especially true if the archives start containing folders.  

Project Layout:
  - Dockerfile:
      Container build description
  - update_pwy.py:
      Primary worker
  - base.py, data.py, funcs.py:
      Helper functions with doctests, that were part of a PyCharm deployment pipeline across multiple projects.

Run lifecycle:
- Runs on container initiation
  - md5 hashes are generated
  - matching S3 files are checked for existence (S3 files have all '/'s replaced with '_'s)
    - If files do not exist, then they are copied from GCE to target and archived
  - md5 hashes are compared between GCE file and S3 file if they match nothing is done
    - In the case of a hash difference the GCE file is copied over the S3 file and the current GCE file is archived with a timestamp to the archive target in the configuration file
  - Archive and primary files are then retrieved from S3 and the hashes are confirmed.
    - Note: Failure at this point is outputted, but there is no current notification system of the failure.
    [backlog] Logs should be parsed for failures by a separate system or this should be added at a future point. 
- Container terminates when copy is complete
 
Notes:
 - path configuration variable should not contain a leading slash, leave blank for root. Technically this is the GCE prefix not a directory.
 - all files are handled in memory, no disk writes required. Instance memory should be provisioned with the size of total file copy in mind.