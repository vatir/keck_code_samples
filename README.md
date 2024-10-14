I’ve included two selections. One to illustrate the type of small decisions made within a project, including the thinking behind ensuring a reasonable level of performance. While the second is an example of a small project that accomplished a production goal. 

### First Example: Shortest Graph Path Example
[Maximum Probability Path.ipynb](https://pages.github.com/)

#### Background Requirements:

Given a collection of entities and a probability of transferring between them, what’s the path with the maximum probability between a specific starting location and an ending location. The system is making calls to an outside system, in this case represented by a proxy function, to accomplish a high-cost operation. 

#### Project Selection Rationale:

I find the importance of problems such as these happen at the higher levels of abstraction. If the entire problem is contained in this type of framing, one can usually jump to trusted libraries for finding an efficient solution. Though, all too often at higher levels of abstraction it’s both trickier to handle the calls from within a library and easier to forget you need the improved complexity of using a more efficient algorithm. 

### Second Example: GCE -> S3 Sync System
[GCE_to_S3_Update_System](https://pages.github.com/)

#### Project Selection Rationale:

Attached is a straightforward project that served well in production for several years and due to the clear delineation of responsibilities for the task all code was written by me. Several subsystems like logging and alerting are also covered and don’t require details explanations of backend systems.

#### Background Requirements:

The core processes were in AWS, but several ingestion targets were in Google Compute Engine (GCE) and outputted files to a Google Cloud Storage (GCS) at unknown times. Additionally, the marketing team wanted some of those results automatically transferred into a WordPress site. 

This task had several downstream tasks, including RDS ingestion and display in customer facing applications that should be prepared for, but the downstream tasks were on independent timescales due to business requirements.

Failures should be alerted, and logs maintained.

#### Project Description:

Given a GCS source and S3 target, bring the S3 target up to date and archive any updated files. Files may be large; zip files may need to be processed, and internal files handled. All files handled in memory.

At this moment I don’t recall the exact rationale for why no local storage was to be used. If I recall it was costly or problematic at the time. It appears that is no longer the case, and this would be approached differently today.

Failure events generate API calls to Slack notifications to reach relevant groups. 
General logging was sent to CloudWatch though Fargate’s stdout logging system allowing it to be aggregated with the runtime metrics. 

#### NDA Note:

It was done for a previous employer but does not contain anything proprietary or significant to that business or its affiliates. There are more ML related and modern projects, but I consider my NDAs and confidentiality to cover those, and I wish to respect those even after the closure of the business.
