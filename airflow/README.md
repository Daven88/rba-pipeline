# Retired: Airflow orchestration (Module 6)

The pipeline was originally orchestrated by a 4-task Airflow DAG running in Docker with
LocalExecutor. It was replaced by a Cloud Run Job triggered by Cloud Scheduler in commit
`bee0606` - managed Airflow on GCP costs roughly $300/month for a permanently-on
cluster, against a pipeline that runs eight times a year.

These files are kept as a record of that implementation. **Nothing here runs.** The DAG
itself was removed once the modules it imported were deleted; see the git history for
`airflow/dags/rba-pipeline-dag.py`.

The container's dependency list used to live here as `requirements-airflow.txt`, which
was misleading long after Airflow was gone. It is now `requirements-pipeline.txt` in the
repository root.

The reasoning behind the migration is in the main README under Architecture Decisions.
