# Copyright 2022 Google LLC
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

# from ibis.backends.postgres.client import PostgreSQLClient
from __future__ import annotations
import third_party.ibis.ibis_postgres.numeric
import ibis.expr.datatypes as dt
import ibis.expr.schema as sch
from ibis import util
from ibis.backends.postgres.client import PostgreSQLClient
import toolz
import parsy

from third_party.ibis.ibis_postgres.parsing import (
    COMMA,
    LBRACKET,
    LPAREN,
    PRECISION,
    RBRACKET,
    RPAREN,
    SCALE,
    spaceless,
    spaceless_string,
)

_BRACKETS = "[]"


def _parse_numeric(
    text: str, default_decimal_parameters: tuple[int | None, int | None] = (None, None)
):
    @parsy.generate
    def decimal():
        yield spaceless_string("decimal", "numeric")
        prec_scale = (
            yield LPAREN.then(
                parsy.seq(PRECISION.skip(COMMA), SCALE).combine(
                    lambda prec, scale: (prec, scale)
                )
            )
            .skip(RPAREN)
            .optional()
        ) or default_decimal_parameters
        return dt.Decimal(*prec_scale)

    @parsy.generate
    def brackets():
        yield spaceless(LBRACKET)
        yield spaceless(RBRACKET)

    @parsy.generate
    def pg_array():
        value_type = yield decimal
        n = len((yield brackets.at_least(1)))
        return toolz.nth(n, toolz.iterate(dt.Array, value_type))

    ty = pg_array | decimal
    return ty.parse(text)


def _get_type(typestr: str) -> dt.DataType:
    is_array = typestr.endswith(_BRACKETS)
    if (typ := _type_mapping.get(typestr.replace(_BRACKETS, ""))) is not None:
        return dt.Array(typ) if is_array else typ
    return _parse_numeric(typestr)

def _get_type(self,typestr: str) -> dt.DataType:
    try:
        return _type_mapping[typestr]
    except KeyError:
        return 

def _get_schema_using_query(self, query: str) -> sch.Schema:
    raw_name = util.guid()
    name = self.con.dialect.identifier_preparer.quote_identifier(raw_name)
    type_info_sql = f"""\
SELECT
attname,
format_type(atttypid, atttypmod) AS type
FROM pg_attribute
WHERE attrelid = {raw_name!r}::regclass
AND attnum > 0
AND NOT attisdropped
ORDER BY attnum
"""
    with self.con.connect() as con:
        con.execute(f"CREATE TEMPORARY VIEW {name} AS {query}")
        try:
            type_info = con.execute(type_info_sql).fetchall()
        finally:
            con.execute(f"DROP VIEW {name}")
    tuples = [(col, self._get_type(typestr)) for col, typestr in type_info]
    return sch.Schema.from_tuples(tuples)

_type_mapping = {
    # "boolean": dt.bool,
    "boolean": dt.boolean,
    "boolean[]": dt.Array(dt.boolean),
    "bytea": dt.binary,
    "bytea[]": dt.Array(dt.binary),
    "character(1)": dt.string,
    "character(1)[]": dt.Array(dt.string),
    "bigint": dt.int64,
    "bigint[]": dt.Array(dt.int64),
    "smallint": dt.int16,
    "smallint[]": dt.Array(dt.int16),
    "integer": dt.int32,
    "integer[]": dt.Array(dt.int32),
    "text": dt.string,
    "text[]": dt.Array(dt.string),
    "json": dt.json,
    "json[]": dt.Array(dt.json),
    "point": dt.point,
    "point[]": dt.Array(dt.point),
    "polygon": dt.polygon,
    "polygon[]": dt.Array(dt.polygon),
    "line": dt.linestring,
    "line[]": dt.Array(dt.linestring),
    "real": dt.float32,
    "real[]": dt.Array(dt.float32),
    "double precision": dt.float64,
    "double precision[]": dt.Array(dt.float64),
    "macaddr8": dt.macaddr,
    "macaddr8[]": dt.Array(dt.macaddr),
    "macaddr": dt.macaddr,
    "macaddr[]": dt.Array(dt.macaddr),
    "inet": dt.inet,
    "inet[]": dt.Array(dt.inet),
    "character": dt.string,
    "character[]": dt.Array(dt.string),
    "character varying": dt.string,
    "character varying[]": dt.Array(dt.string),
    "date": dt.date,
    "date[]": dt.Array(dt.date),
    "time without time zone": dt.time,
    "time without time zone[]": dt.Array(dt.time),
    "timestamp without time zone": dt.timestamp,
    "timestamp without time zone[]": dt.Array(dt.timestamp),
    "timestamp with time zone": dt.Timestamp("UTC"),
    "timestamp with time zone[]": dt.Array(dt.Timestamp("UTC")),
    "interval": dt.interval,
    "interval[]": dt.Array(dt.interval),
    # NB: this isn"t correct, but we try not to fail
    "time with time zone": "time",
    "numeric": dt.Decimal,
    "numeric[]": dt.Array(dt.Decimal),
    "uuid": dt.uuid,
    "uuid[]": dt.Array(dt.uuid),
    "jsonb": dt.jsonb,
    "jsonb[]": dt.Array(dt.jsonb),
    "geometry": dt.geometry,
    "geometry[]": dt.Array(dt.geometry),
    "geography": dt.geography,
    "geography[]": dt.Array(dt.geography),
}

PostgreSQLClient._get_schema_using_query = _get_schema_using_query
PostgreSQLClient._get_type = _get_type