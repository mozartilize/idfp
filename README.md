idfp
---

0. Prerequisite

- Python >= 3.11
- Postgresql >= 13

1. Setup the database

Create the database and run the sqls in the migrations directory.

It also requires 2 different roles, one for normal use and one for only reading the data tables via `/sql` route.

For example, to create the read-only role:

```sql
create user idfp_reader;

\password idfp_reader

REVOKE ALL PRIVILEGES ON database idfp FROM PUBLIC;

grant connect on database idfp to idfp_reader;

-- and so on for other tables
grant select on areas to idfp_reader;
```

2. Setup the application

The application can be installed via git.

```shell
pip install git+https://github.com/mozartilize/idfp
```

Or to exploring the codebase, install in development mode after cloning.

```shell
pip install -e .
```

Configure the application with a toml file, an example is available as `config.example.toml`.

The application exposes a command line interface.

```shell
idfp --help
```

3. Start the web server

```shell
idfp -c config.toml web
```

It runs gunicorn under the hood but only some of the options are available to be configured.

4. Import csv data

```shell
idfp -c config.toml import-csv --help
```

For example, to import areas data with a csv file that has tab delimeter:

```shell
idfp -c config.toml import-csv --delimiter $'\t' Area.csv area
```

It even accepts data from standard input, so we can unzip the file and pipe into it:

```shell
unzip -p Area.zip | idfp -c config.toml import-csv --delimiter $'\t' - area
```

5. Data models/Tables

|sources|
|-------|
|id|
|type|
|filename|
|submitted_date|
|processed_at|
|errors|

where the csv file info stored once it imported. The error could be the file contains invalid/unmatch headers.

|[entity]_csv|
|------------|
|id|
|source_id|
|processed_at|
|...|

where each row in the csv file inserted into. All the fields will be store as `varchar` for further parsing process.

Regarding csv files could be directly processed and imported to database, this table is responsible for reporting bad data and acting as a source in case editing inplace and reimporting the data.

The tables will grow quickly over time, but a simple cron job runs on a monthly or weekly basis to truncate data could solve the problem.

|csv_errors|
|----------|
|id|
|source_id|
|record_id|
|errors|

contains the error if any for each row once processed. The error could be missing required field, or invalid data type.

|[entity]|
|--------|
|...|

stores cleaned data. Each entity is modeled Pydantic type - a library support parsing data with Python origin typing system.
