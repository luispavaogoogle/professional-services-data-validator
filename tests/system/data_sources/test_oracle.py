# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from unittest import mock

from data_validation import cli_tools, data_validation, consts, __main__ as main
from tests.system.data_sources.common_functions import (
    binary_key_assertions,
    find_tables_assertions,
    id_type_test_assertions,
    null_not_null_assertions,
    row_validation_many_columns_test,
    run_test_from_cli_args,
)
from tests.system.data_sources.test_bigquery import BQ_CONN
from tests.system.data_sources.test_postgres import CONN as PG_CONN
from tests.system.data_sources.common_functions import generate_partitions_test


ORACLE_HOST = os.getenv("ORACLE_HOST", "localhost")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")
ORACLE_DATABASE = os.getenv("ORACLE_DATABASE", "XEPDB1")

CONN = {
    "source_type": "Oracle",
    "host": ORACLE_HOST,
    "user": "SYSTEM",
    "password": ORACLE_PASSWORD,
    "port": 1521,
    "database": ORACLE_DATABASE,
}


ORACLE_CONFIG = {
    # Specific Connection Config
    consts.CONFIG_SOURCE_CONN: CONN,
    consts.CONFIG_TARGET_CONN: CONN,
    # Validation Type
    consts.CONFIG_TYPE: "Column",
    # Configuration Required Depending on Validator Type
    consts.CONFIG_SCHEMA_NAME: "pso_data_validator",
    consts.CONFIG_TABLE_NAME: "items_price",
    consts.CONFIG_AGGREGATES: [
        {
            consts.CONFIG_TYPE: "count",
            consts.CONFIG_SOURCE_COLUMN: "price",
            consts.CONFIG_TARGET_COLUMN: "price",
            consts.CONFIG_FIELD_ALIAS: "count",
        },
    ],
    consts.CONFIG_FORMAT: "table",
    consts.CONFIG_FILTER_STATUS: None,
}

ORA2PG_COLUMNS = [
    "id",
    "col_num_4",
    "col_num_9",
    "col_num_18",
    "col_num_38",
    "col_num",
    "col_num_10_2",
    "col_num_float",
    "col_float32",
    "col_float64",
    "col_varchar_30",
    "col_char_2",
    "col_nvarchar_30",
    "col_nchar_2",
    "col_date",
    "col_ts",
    "col_tstz",
    "col_interval_ds",
    "col_raw",
    "col_long_raw",
    "col_blob",
    "col_clob",
    "col_nclob",
]


def test_count_validator():
    validator = data_validation.DataValidation(ORACLE_CONFIG, verbose=True)
    df = validator.execute()
    assert int(df["source_agg_value"][0]) > 0
    assert df["source_agg_value"][0] == df["target_agg_value"][0]


def mock_get_connection_config(*args):
    if args[1] in ("ora-conn", "mock-conn"):
        return CONN
    elif args[1] == "bq-conn":
        return BQ_CONN
    elif args[1] == "pg-conn":
        return PG_CONN


# Expected result from partitioning table on 3 keys
EXPECTED_PARTITION_FILTER = [
    [
        " quarter_id <> 1111 AND ( course_id < 'ALG001' OR course_id = 'ALG001' AND ( quarter_id < 2 OR quarter_id = 2 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'ALG001' OR course_id = 'ALG001' AND ( quarter_id > 2 OR quarter_id = 2 AND student_id >= 1234 ) ) AND ( course_id < 'ALG001' OR course_id = 'ALG001' AND ( quarter_id < 3 OR quarter_id = 3 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'ALG001' OR course_id = 'ALG001' AND ( quarter_id > 3 OR quarter_id = 3 AND student_id >= 1234 ) ) AND ( course_id < 'GEO001' OR course_id = 'GEO001' AND ( quarter_id < 1 OR quarter_id = 1 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'GEO001' OR course_id = 'GEO001' AND ( quarter_id > 1 OR quarter_id = 1 AND student_id >= 1234 ) ) AND ( course_id < 'GEO001' OR course_id = 'GEO001' AND ( quarter_id < 2 OR quarter_id = 2 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'GEO001' OR course_id = 'GEO001' AND ( quarter_id > 2 OR quarter_id = 2 AND student_id >= 1234 ) ) AND ( course_id < 'GEO001' OR course_id = 'GEO001' AND ( quarter_id < 3 OR quarter_id = 3 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'GEO001' OR course_id = 'GEO001' AND ( quarter_id > 3 OR quarter_id = 3 AND student_id >= 1234 ) ) AND ( course_id < 'TRI001' OR course_id = 'TRI001' AND ( quarter_id < 1 OR quarter_id = 1 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'TRI001' OR course_id = 'TRI001' AND ( quarter_id > 1 OR quarter_id = 1 AND student_id >= 1234 ) ) AND ( course_id < 'TRI001' OR course_id = 'TRI001' AND ( quarter_id < 2 OR quarter_id = 2 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'TRI001' OR course_id = 'TRI001' AND ( quarter_id > 2 OR quarter_id = 2 AND student_id >= 1234 ) ) AND ( course_id < 'TRI001' OR course_id = 'TRI001' AND ( quarter_id < 3 OR quarter_id = 3 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'TRI001' OR course_id = 'TRI001' AND ( quarter_id > 3 OR quarter_id = 3 AND student_id >= 1234 ) )",
    ],
    [
        " quarter_id <> 1111 AND ( course_id < 'ALG001' OR course_id = 'ALG001' AND ( quarter_id < 2 OR quarter_id = 2 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'ALG001' OR course_id = 'ALG001' AND ( quarter_id > 2 OR quarter_id = 2 AND student_id >= 1234 ) ) AND ( course_id < 'ALG001' OR course_id = 'ALG001' AND ( quarter_id < 3 OR quarter_id = 3 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'ALG001' OR course_id = 'ALG001' AND ( quarter_id > 3 OR quarter_id = 3 AND student_id >= 1234 ) ) AND ( course_id < 'GEO001' OR course_id = 'GEO001' AND ( quarter_id < 1 OR quarter_id = 1 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'GEO001' OR course_id = 'GEO001' AND ( quarter_id > 1 OR quarter_id = 1 AND student_id >= 1234 ) ) AND ( course_id < 'GEO001' OR course_id = 'GEO001' AND ( quarter_id < 2 OR quarter_id = 2 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'GEO001' OR course_id = 'GEO001' AND ( quarter_id > 2 OR quarter_id = 2 AND student_id >= 1234 ) ) AND ( course_id < 'GEO001' OR course_id = 'GEO001' AND ( quarter_id < 3 OR quarter_id = 3 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'GEO001' OR course_id = 'GEO001' AND ( quarter_id > 3 OR quarter_id = 3 AND student_id >= 1234 ) ) AND ( course_id < 'TRI001' OR course_id = 'TRI001' AND ( quarter_id < 1 OR quarter_id = 1 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'TRI001' OR course_id = 'TRI001' AND ( quarter_id > 1 OR quarter_id = 1 AND student_id >= 1234 ) ) AND ( course_id < 'TRI001' OR course_id = 'TRI001' AND ( quarter_id < 2 OR quarter_id = 2 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'TRI001' OR course_id = 'TRI001' AND ( quarter_id > 2 OR quarter_id = 2 AND student_id >= 1234 ) ) AND ( course_id < 'TRI001' OR course_id = 'TRI001' AND ( quarter_id < 3 OR quarter_id = 3 AND student_id < 1234 ) )",
        " quarter_id <> 1111 AND ( course_id > 'TRI001' OR course_id = 'TRI001' AND ( quarter_id > 3 OR quarter_id = 3 AND student_id >= 1234 ) )",
    ],
]


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_oracle_generate_table_partitions():
    """Test generate table partitions on Oracle"""
    generate_partitions_test(EXPECTED_PARTITION_FILTER)


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_schema_validation_core_types():
    """Oracle to Oracle dvt_core_types schema validation"""
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "schema",
            "-sc=mock-conn",
            "-tc=mock-conn",
            "-tbls=pso_data_validator.dvt_core_types",
            "--filter-status=fail",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_schema_validation_core_types_to_bigquery():
    """Oracle to BigQuery dvt_core_types schema validation"""
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "schema",
            "-sc=ora-conn",
            "-tc=bq-conn",
            "-tbls=pso_data_validator.dvt_core_types",
            "--filter-status=fail",
            "--exclusion-columns=id",
            (
                # Integer Oracle NUMBERS go to BigQuery INT64.
                "--allow-list=decimal(2,0):int64,decimal(4,0):int64,decimal(9,0):int64,decimal(18,0):int64,"
                # BigQuery does not have a float32 type.
                "float32:float64"
            ),
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_schema_validation_not_null_vs_nullable():
    """Compares a source table with a BigQuery target and ensure we match/fail on not null/nullable correctly."""
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "schema",
            "-sc=ora-conn",
            "-tc=bq-conn",
            "-tbls=pso_data_validator.dvt_null_not_null=pso_data_validator.dvt_null_not_null",
        ]
    )
    df = run_test_from_cli_args(args)
    null_not_null_assertions(df)


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_schema_validation_oracle_to_postgres():
    """Oracle to PostgreSQL schema validation"""

    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "schema",
            "-sc=ora-conn",
            "-tc=pg-conn",
            "-tbls=pso_data_validator.dvt_ora2pg_types",
            "--filter-status=fail",
            "--exclusion-columns=id",
            "--allow-list-file=samples/allow_list/oracle_to_postgres.yaml",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_column_validation_core_types():
    """Oracle to Oracle dvt_core_types column validation"""
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "column",
            "-sc=mock-conn",
            "-tc=mock-conn",
            "-tbls=pso_data_validator.dvt_core_types",
            "--filters=id>0 AND col_int8>0",
            "--filter-status=fail",
            "--grouped-columns=col_varchar_30",
            "--sum=col_int8,col_int16,col_int32,col_int64,col_dec_20,col_dec_38,col_dec_10_2,col_float32,col_float64,col_varchar_30,col_char_2,col_string,col_date,col_datetime,col_tstz",
            "--min=col_int8,col_int16,col_int32,col_int64,col_dec_20,col_dec_38,col_dec_10_2,col_float32,col_float64,col_varchar_30,col_char_2,col_string,col_date,col_datetime,col_tstz",
            "--max=col_int8,col_int16,col_int32,col_int64,col_dec_20,col_dec_38,col_dec_10_2,col_float32,col_float64,col_varchar_30,col_char_2,col_string,col_date,col_datetime,col_tstz",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_column_validation_core_types_to_bigquery():
    parser = cli_tools.configure_arg_parser()
    # We've excluded col_float32 because BigQuery does not have an exact same type and float32/64 are lossy and cannot be compared.
    args = parser.parse_args(
        [
            "validate",
            "column",
            "-sc=ora-conn",
            "-tc=bq-conn",
            "-tbls=pso_data_validator.dvt_core_types",
            "--filter-status=fail",
            "--sum=col_int8,col_int16,col_int32,col_int64,col_dec_20,col_dec_38,col_dec_10_2,col_float64,col_varchar_30,col_char_2,col_string,col_date,col_datetime,col_tstz",
            "--min=col_int8,col_int16,col_int32,col_int64,col_dec_20,col_dec_38,col_dec_10_2,col_float64,col_varchar_30,col_char_2,col_string,col_date,col_datetime,col_tstz",
            "--max=col_int8,col_int16,col_int32,col_int64,col_dec_20,col_dec_38,col_dec_10_2,col_float64,col_varchar_30,col_char_2,col_string,col_date,col_datetime,col_tstz",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_column_validation_oracle_to_postgres():
    parser = cli_tools.configure_arg_parser()
    count_cols = ",".join([_ for _ in ORA2PG_COLUMNS if _ not in ("col_long_raw")])
    # TODO Change sum_cols and min_cols to include col_char_2,col_nchar_2 when issue-842 is complete.
    # TODO Change sum_cols to include col_num_18 when issue-1007 is complete.
    sum_cols = ",".join(
        [
            _
            for _ in ORA2PG_COLUMNS
            if _ not in ("col_char_2", "col_nchar_2", "col_num_18", "col_long_raw")
        ]
    )
    min_cols = ",".join(
        [
            _
            for _ in ORA2PG_COLUMNS
            if _ not in ("col_char_2", "col_nchar_2", "col_long_raw")
        ]
    )
    args = parser.parse_args(
        [
            "validate",
            "column",
            "-sc=ora-conn",
            "-tc=pg-conn",
            "-tbls=pso_data_validator.dvt_ora2pg_types",
            "--filter-status=fail",
            f"--count={count_cols}",
            f"--sum={sum_cols}",
            f"--min={min_cols}",
            f"--max={min_cols}",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_row_validation_core_types():
    """Oracle to Oracle dvt_core_types row validation"""
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "row",
            "-sc=mock-conn",
            "-tc=mock-conn",
            "-tbls=pso_data_validator.dvt_core_types",
            "--filters=id>0 AND col_int8>0",
            "--primary-keys=id",
            "--filter-status=fail",
            "--hash=*",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_row_validation_core_types_to_bigquery():
    """Oracle to BigQuery dvt_core_types row validation"""
    # Excluded col_float32,col_float64 due to the lossy nature of BINARY_FLOAT/DOUBLE.
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "row",
            "-sc=ora-conn",
            "-tc=bq-conn",
            "-tbls=pso_data_validator.dvt_core_types",
            "--primary-keys=id",
            "--filter-status=fail",
            "--hash=col_int8,col_int16,col_int32,col_int64,col_dec_20,col_dec_38,col_dec_10_2,col_varchar_30,col_char_2,col_string,col_date,col_datetime,col_tstz",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_row_validation_oracle_to_postgres():
    # TODO Change hash_cols below to include col_tstz when issue-706 is complete.
    # TODO col_raw/col_long_raw are blocked by issue-773 (is it even reasonable to expect binary columns to work here?)
    # TODO Change hash_cols below to include col_nvarchar_30,col_nchar_2 when issue-772 is complete.
    # TODO Change hash_cols below to include col_interval_ds when issue-1214 is complete.
    # Excluded col_float32,col_float64 due to the lossy nature of BINARY_FLOAT/DOUBLE.
    # Excluded CLOB/NCLOB/BLOB columns because lob values cannot be concatenated
    hash_cols = ",".join(
        [
            _
            for _ in ORA2PG_COLUMNS
            if _
            not in (
                "col_blob",
                "col_clob",
                "col_nclob",
                "col_raw",
                "col_long_raw",
                "col_float32",
                "col_float64",
                "col_tstz",
                "col_nvarchar_30",
                "col_nchar_2",
                "col_interval_ds",
            )
        ]
    )
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "row",
            "-sc=ora-conn",
            "-tc=pg-conn",
            "-tbls=pso_data_validator.dvt_ora2pg_types",
            "--primary-keys=id",
            "--filter-status=fail",
            f"--hash={hash_cols}",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_row_validation_large_decimals_to_bigquery():
    """Oracle to BigQuery dvt_large_decimals row validation.
    See https://github.com/GoogleCloudPlatform/professional-services-data-validator/issues/956
    This is testing large decimals for the primary key join column plus the hash columns.
    """
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "row",
            "-sc=ora-conn",
            "-tc=bq-conn",
            "-tbls=pso_data_validator.dvt_large_decimals",
            "--primary-keys=id",
            "--filter-status=fail",
            "--hash=id,col_data,col_dec_18,col_dec_38,col_dec_38_9,col_dec_38_30",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_row_validation_binary_pk_to_bigquery():
    """Oracle to BigQuery dvt_binary row validation.
    This is testing binary primary key join columns.
    Includes random row filter test.
    """
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "row",
            "-sc=ora-conn",
            "-tc=bq-conn",
            "-tbls=pso_data_validator.dvt_binary",
            "--primary-keys=binary_id",
            "--hash=int_id,other_data",
            "--use-random-row",
            "--random-row-batch-size=5",
        ]
    )
    df = run_test_from_cli_args(args)
    binary_key_assertions(df)


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_row_validation_string_pk_to_bigquery():
    """Oracle to BigQuery dvt_string_id row validation.
    This is testing string primary key join columns.
    Includes random row filter test.
    """
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "row",
            "-sc=ora-conn",
            "-tc=bq-conn",
            "-tbls=pso_data_validator.dvt_string_id",
            "--primary-keys=id",
            "--hash=id,other_data",
            "--use-random-row",
            "--random-row-batch-size=5",
        ]
    )
    df = run_test_from_cli_args(args)
    id_type_test_assertions(df)


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_row_validation_char_pk_to_bigquery():
    """Oracle to BigQuery dvt_char_id row validation.
    This is testing CHAR primary key join columns.
    Includes random row filter test.
    """
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "row",
            "-sc=ora-conn",
            "-tc=bq-conn",
            "-tbls=pso_data_validator.dvt_char_id",
            "--primary-keys=id",
            "--hash=id,other_data",
            "--use-random-row",
            "--random-row-batch-size=5",
        ]
    )
    df = run_test_from_cli_args(args)
    id_type_test_assertions(df)


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_row_validation_pangrams_to_bigquery():
    """Oracle to BigQuery dvt_pangrams row validation.
    This is testing comparisons across a wider set of characters than standard test data.
    """
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "row",
            "-sc=ora-conn",
            "-tc=bq-conn",
            "-tbls=pso_data_validator.dvt_pangrams",
            "--primary-keys=id",
            "--hash=*",
        ]
    )
    df = run_test_from_cli_args(args)
    id_type_test_assertions(df)


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_custom_query_column_validation_core_types_to_bigquery():
    """Oracle to BigQuery dvt_core_types custom-query column validation"""
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "custom-query",
            "column",
            "-sc=ora-conn",
            "-tc=bq-conn",
            "--source-query=select * from pso_data_validator.dvt_core_types",
            "--target-query=select * from pso_data_validator.dvt_core_types",
            "--filter-status=fail",
            "--count=*",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_custom_query_row_validation_core_types_to_bigquery():
    """Oracle to BigQuery dvt_core_types custom-query row comparison-fields validation"""
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "custom-query",
            "row",
            "-sc=ora-conn",
            "-tc=bq-conn",
            "--source-query=select id,col_int64,COL_VARCHAR_30,col_date from pso_data_validator.dvt_core_types",
            "--target-query=select id,col_int64,col_varchar_30,COL_DATE from pso_data_validator.dvt_core_types",
            "--primary-keys=id",
            "--filter-status=fail",
            "--comparison-fields=col_int64,col_varchar_30,col_date",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_custom_query_row_hash_validation_core_types_to_bigquery():
    """Oracle to BigQuery dvt_core_types custom-query row hash validation"""
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "validate",
            "custom-query",
            "row",
            "-sc=ora-conn",
            "-tc=bq-conn",
            "--source-query=select id,col_int64,COL_VARCHAR_30,col_date from pso_data_validator.dvt_core_types",
            "--target-query=select id,col_int64,col_varchar_30,COL_DATE from pso_data_validator.dvt_core_types",
            "--primary-keys=id",
            "--filter-status=fail",
            "--hash=col_int64,col_varchar_30,col_date",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be empty
    assert len(df) == 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_custom_query_invalid_long_decimal():
    """Oracle to BigQuery of comparisons of decimals that exceed precision of 18 (int64 & float64).
    We used to have an issue where we would see false success because long numbers would lose precision
    and look the same even if they differed slightly.
    See: https://github.com/GoogleCloudPlatform/professional-services-data-validator/issues/900
    This is the regression test.
    """
    parser = cli_tools.configure_arg_parser()
    # Notice the two numeric values balow have a different final digit, we expect a failure status.
    args = parser.parse_args(
        [
            "validate",
            "custom-query",
            "column",
            "-sc=mock-conn",
            "-tc=bq-conn",
            "--source-query=select to_number(1234567890123456789012345) as dec_25 from dual",
            "--target-query=select cast('1234567890123456789012340' as numeric) as dec_25",
            "--filter-status=fail",
            "--min=dec_25",
            "--max=dec_25",
            "--sum=dec_25",
        ]
    )
    df = run_test_from_cli_args(args)
    # With filter on failures the data frame should be populated
    assert len(df) > 0


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_find_tables():
    """Oracle to BigQuery test of find-tables command."""
    parser = cli_tools.configure_arg_parser()
    args = parser.parse_args(
        [
            "find-tables",
            "-sc=mock-conn",
            "-tc=bq-conn",
            "--allowed-schemas=pso_data_validator",
        ]
    )
    output = main.find_tables_using_string_matching(args)
    find_tables_assertions(output)


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_row_validation_many_columns():
    """Oracle dvt_many_cols row validation.
    This is testing many columns logic for --hash, there's a Teradata test for --concat.
    """
    row_validation_many_columns_test(expected_config_managers=4)


@mock.patch(
    "data_validation.state_manager.StateManager.get_connection_config",
    new=mock_get_connection_config,
)
def test_custom_query_row_validation_many_columns():
    """Oracle dvt_many_cols custom-query row validation.
    This is testing many columns logic for --hash, there's a Teradata test for --concat.
    """
    row_validation_many_columns_test(
        validation_type="custom-query", expected_config_managers=4
    )
