create table sources(
    id serial primary key,
    type varchar,
    filename varchar,
    submitted_by varchar,
    submitted_date date,
    number_of_records int,
    processed_at timestamp with time zone null
);

create table source_errors(
    id serial primary key,
    source_id int,
    errors json null
)

create table csv_errors(
    id serial primary key,
    source_id int,
    record_id int,
    errors json null
)

create table area_csv(
    id serial primary key,
    source_id int null,
    processed_at int null,
    IsDeleted varchar,
    Operation varchar null,
    LicenseNumber varchar null,
    LicenseeId varchar,
    ExternalIdentifier varchar,
    CreatedBy varchar,
    UpdatedBy varchar,
    CreatedDate varchar,
    UpdatedDate varchar,
    Area varchar null,
    Name varchar,
    AreaId varchar,
    IsQuarantine varchar
);

create table areas(
    ExternalIdentifier varchar primary key,
    LicenseeId integer,
    CreatedBy varchar,
    UpdatedBy varchar,
    CreatedDate date,
    UpdatedDate date,
    Name varchar,
    AreaId integer,
    IsQuarantine boolean
);

create table strain_csv(
    id serial primary key,
    source_id int null,
    processed_at int null,
    IsDeleted varchar,
    Operation varchar null,
    LicenseNumber varchar null,
    LicenseeId varchar,
    CreatedBy varchar,
    UpdatedBy varchar,
    CreatedDate varchar,
    UpdatedDate varchar,
    StrainId varchar,
    AssociateId varchar,
    StrainType varchar,
    Name varchar
);

create table inventory_csv(
    source_id int null,
    Operation varchar,
    LicenseNumber varchar,
    ExternalIdentifier varchar,
    CreatedBy varchar,
    UpdatedBy varchar null,
    CreatedDate date,
    UpdatedDate date null,
    Strain varchar,
    Area varchar,
    Product varchar,
    InitialQuantity integer,
    QuantityOnHand integer,
    TotalCost integer,
    IsMedical boolean
)

