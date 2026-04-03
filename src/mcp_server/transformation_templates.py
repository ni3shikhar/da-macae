"""
Transformation Templates for ADF Mapping Data Flows, Synapse Data Flows,
and Fabric Dataflow Gen2 with Power Query M transformations.

Provides:
  - Column-level transformation mapping model
  - ADF Mapping Data Flow JSON templates with transformation activities
  - Synapse Data Flow definitions
  - Fabric Dataflow Gen2 Power Query M scripts with transformations
  - Pre-built transformation expression libraries for common ETL/ELT patterns
"""

from __future__ import annotations

from typing import Any

# ══════════════════════════════════════════════════════════════════════
# TRANSFORMATION EXPRESSION LIBRARIES
# ══════════════════════════════════════════════════════════════════════
# Pre-built expressions for common transformations across ADF Data Flow
# Expression Language (DFEL), PySpark, and Power Query M.

# ── ADF Data Flow Expression Language (DFEL) ─────────────────────────
ADF_EXPRESSIONS: dict[str, dict[str, str]] = {
    # String transformations
    "upper": {
        "expression": "upper({column})",
        "description": "Convert to uppercase",
    },
    "lower": {
        "expression": "lower({column})",
        "description": "Convert to lowercase",
    },
    "trim": {
        "expression": "trim({column})",
        "description": "Trim whitespace from both ends",
    },
    "ltrim": {
        "expression": "ltrim({column})",
        "description": "Trim whitespace from left",
    },
    "rtrim": {
        "expression": "rtrim({column})",
        "description": "Trim whitespace from right",
    },
    "concat": {
        "expression": "concat({column1}, {separator}, {column2})",
        "description": "Concatenate two columns with separator",
    },
    "substring": {
        "expression": "substring({column}, {start}, {length})",
        "description": "Extract substring",
    },
    "replace": {
        "expression": "replace({column}, {old_value}, {new_value})",
        "description": "Replace string pattern",
    },
    "regex_replace": {
        "expression": "regexReplace({column}, `{pattern}`, '{replacement}')",
        "description": "Regex-based string replacement",
    },
    "left_pad": {
        "expression": "lpad({column}, {length}, '{pad_char}')",
        "description": "Left-pad to specified length",
    },
    "right_pad": {
        "expression": "rpad({column}, {length}, '{pad_char}')",
        "description": "Right-pad to specified length",
    },
    "soundex": {
        "expression": "soundex({column})",
        "description": "Compute Soundex phonetic code",
    },
    # Type conversions
    "to_string": {
        "expression": "toString({column})",
        "description": "Cast to string",
    },
    "to_integer": {
        "expression": "toInteger({column})",
        "description": "Cast to integer",
    },
    "to_long": {
        "expression": "toLong({column})",
        "description": "Cast to long",
    },
    "to_float": {
        "expression": "toFloat({column})",
        "description": "Cast to float",
    },
    "to_double": {
        "expression": "toDouble({column})",
        "description": "Cast to double",
    },
    "to_decimal": {
        "expression": "toDecimal({column}, {precision}, {scale})",
        "description": "Cast to decimal with precision/scale",
    },
    "to_date": {
        "expression": "toDate({column}, '{format}')",
        "description": "Parse string to date (e.g. 'yyyy-MM-dd')",
    },
    "to_timestamp": {
        "expression": "toTimestamp({column}, '{format}')",
        "description": "Parse string to timestamp",
    },
    "to_boolean": {
        "expression": "toBoolean({column})",
        "description": "Cast to boolean",
    },
    # Date/time transformations
    "current_date": {
        "expression": "currentDate()",
        "description": "Current date (UTC)",
    },
    "current_timestamp": {
        "expression": "currentTimestamp()",
        "description": "Current timestamp (UTC)",
    },
    "year": {
        "expression": "year({column})",
        "description": "Extract year from date/timestamp",
    },
    "month": {
        "expression": "month({column})",
        "description": "Extract month from date/timestamp",
    },
    "day_of_month": {
        "expression": "dayOfMonth({column})",
        "description": "Extract day of month",
    },
    "date_diff": {
        "expression": "daysBetween({start_column}, {end_column})",
        "description": "Days between two dates",
    },
    "add_days": {
        "expression": "addDays({column}, {days})",
        "description": "Add days to a date",
    },
    "format_date": {
        "expression": "toString({column}, '{format}')",
        "description": "Format date as string (e.g. 'yyyy-MM-dd')",
    },
    # Null handling
    "coalesce": {
        "expression": "coalesce({column}, {default_value})",
        "description": "Replace NULL with default value",
    },
    "iif_null": {
        "expression": "iifNull({column}, {replacement})",
        "description": "If null then replacement, else original value",
    },
    "is_null": {
        "expression": "isNull({column})",
        "description": "Check if value is NULL (returns boolean)",
    },
    # Conditional
    "iif": {
        "expression": "iif({condition}, {true_value}, {false_value})",
        "description": "If-then-else conditional expression",
    },
    "case_when": {
        "expression": "case({column} == {value1}, {result1}, {column} == {value2}, {result2}, {default_result})",
        "description": "Multi-branch case/when expression",
    },
    # Hash / crypto
    "md5": {
        "expression": "md5({column})",
        "description": "MD5 hash of column value",
    },
    "sha2_256": {
        "expression": "sha2({column}, 256)",
        "description": "SHA-256 hash",
    },
    # Aggregations (for aggregate transforms)
    "sum": {
        "expression": "sum({column})",
        "description": "Sum aggregation",
    },
    "avg": {
        "expression": "avg({column})",
        "description": "Average aggregation",
    },
    "min": {
        "expression": "min({column})",
        "description": "Minimum value",
    },
    "max": {
        "expression": "max({column})",
        "description": "Maximum value",
    },
    "count": {
        "expression": "count({column})",
        "description": "Count non-null values",
    },
    "count_distinct": {
        "expression": "countDistinct({column})",
        "description": "Count distinct values",
    },
    # Lookup / surrogate key
    "surrogate_key": {
        "expression": "1",  # Used in Surrogate Key transform, not an expression
        "description": "Auto-incrementing surrogate key (use with SurrogateKey transform)",
    },
}

# ── Power Query M Expression Library ─────────────────────────────────
POWER_QUERY_M_EXPRESSIONS: dict[str, dict[str, str]] = {
    "upper": {
        "expression": 'Text.Upper([{column}])',
        "description": "Convert to uppercase",
    },
    "lower": {
        "expression": 'Text.Lower([{column}])',
        "description": "Convert to lowercase",
    },
    "trim": {
        "expression": 'Text.Trim([{column}])',
        "description": "Trim whitespace",
    },
    "concat": {
        "expression": '[{column1}] & "{separator}" & [{column2}]',
        "description": "Concatenate columns",
    },
    "substring": {
        "expression": 'Text.Range([{column}], {start}, {length})',
        "description": "Extract substring (0-based start)",
    },
    "replace": {
        "expression": 'Text.Replace([{column}], "{old_value}", "{new_value}")',
        "description": "Replace string",
    },
    "to_number": {
        "expression": 'Number.FromText([{column}])',
        "description": "Convert text to number",
    },
    "to_text": {
        "expression": 'Text.From([{column}])',
        "description": "Convert to text",
    },
    "to_date": {
        "expression": 'Date.FromText([{column}])',
        "description": "Parse text to date",
    },
    "to_datetime": {
        "expression": 'DateTime.FromText([{column}])',
        "description": "Parse text to datetime",
    },
    "coalesce": {
        "expression": 'if [{column}] = null then {default_value} else [{column}]',
        "description": "Replace null with default",
    },
    "iif": {
        "expression": 'if {condition} then {true_value} else {false_value}',
        "description": "Conditional expression",
    },
    "year": {
        "expression": 'Date.Year([{column}])',
        "description": "Extract year",
    },
    "month": {
        "expression": 'Date.Month([{column}])',
        "description": "Extract month",
    },
    "day": {
        "expression": 'Date.Day([{column}])',
        "description": "Extract day",
    },
    "round": {
        "expression": 'Number.Round([{column}], {decimals})',
        "description": "Round to N decimal places",
    },
    "left_pad": {
        "expression": 'Text.PadStart(Text.From([{column}]), {length}, "{pad_char}")',
        "description": "Left-pad to length",
    },
    "hash_md5": {
        "expression": 'Binary.ToText(Binary.FromText(Text.From([{column}]), BinaryEncoding.Base64), BinaryEncoding.Hex)',
        "description": "Basic hash (for deduplication, not cryptographic)",
    },
}

# ── PySpark Expression Library (for Synapse Spark) ───────────────────
PYSPARK_EXPRESSIONS: dict[str, dict[str, str]] = {
    "upper": {
        "expression": 'F.upper(F.col("{column}"))',
        "description": "Convert to uppercase",
    },
    "lower": {
        "expression": 'F.lower(F.col("{column}"))',
        "description": "Convert to lowercase",
    },
    "trim": {
        "expression": 'F.trim(F.col("{column}"))',
        "description": "Trim whitespace",
    },
    "concat": {
        "expression": 'F.concat(F.col("{column1}"), F.lit("{separator}"), F.col("{column2}"))',
        "description": "Concatenate columns",
    },
    "substring": {
        "expression": 'F.substring(F.col("{column}"), {start}, {length})',
        "description": "Extract substring (1-based start in Spark)",
    },
    "replace": {
        "expression": 'F.regexp_replace(F.col("{column}"), "{old_value}", "{new_value}")',
        "description": "Replace string pattern",
    },
    "to_date": {
        "expression": 'F.to_date(F.col("{column}"), "{format}")',
        "description": "Parse to date (e.g., 'yyyy-MM-dd')",
    },
    "to_timestamp": {
        "expression": 'F.to_timestamp(F.col("{column}"), "{format}")',
        "description": "Parse to timestamp",
    },
    "cast_int": {
        "expression": 'F.col("{column}").cast("int")',
        "description": "Cast to integer",
    },
    "cast_double": {
        "expression": 'F.col("{column}").cast("double")',
        "description": "Cast to double",
    },
    "cast_string": {
        "expression": 'F.col("{column}").cast("string")',
        "description": "Cast to string",
    },
    "coalesce": {
        "expression": 'F.coalesce(F.col("{column}"), F.lit({default_value}))',
        "description": "Replace null with default",
    },
    "iif": {
        "expression": 'F.when({condition}, {true_value}).otherwise({false_value})',
        "description": "Conditional expression",
    },
    "year": {
        "expression": 'F.year(F.col("{column}"))',
        "description": "Extract year",
    },
    "month": {
        "expression": 'F.month(F.col("{column}"))',
        "description": "Extract month",
    },
    "md5": {
        "expression": 'F.md5(F.col("{column}"))',
        "description": "MD5 hash",
    },
    "sha2_256": {
        "expression": 'F.sha2(F.col("{column}"), 256)',
        "description": "SHA-256 hash",
    },
}


# ══════════════════════════════════════════════════════════════════════
# ADF MAPPING DATA FLOW TEMPLATES
# ══════════════════════════════════════════════════════════════════════

# ── Source transform ──────────────────────────────────────────────────
ADF_DATAFLOW_SOURCE: dict[str, Any] = {
    "name": "{{SOURCE_NAME}}",
    "description": "Read from {{SOURCE_TABLE}}",
    "dataset": {
        "referenceName": "{{SOURCE_DATASET}}",
        "type": "DatasetReference",
    },
    "script": 'source(output(\n{{COLUMN_DEFINITIONS}}\n),\nallowSchemaDrift: true,\nvalidateSchema: false) ~> {{SOURCE_NAME}}',
}

# ── Sink transform ────────────────────────────────────────────────────
ADF_DATAFLOW_SINK: dict[str, Any] = {
    "name": "{{SINK_NAME}}",
    "description": "Write to {{TARGET_TABLE}}",
    "dataset": {
        "referenceName": "{{TARGET_DATASET}}",
        "type": "DatasetReference",
    },
    "script": '{{INPUT_STREAM}} sink(allowSchemaDrift: true,\nvalidateSchema: false,\ntruncate: {{TRUNCATE}},\nskipDuplicateMapInputs: true,\nskipDuplicateMapOutputs: true) ~> {{SINK_NAME}}',
}

# ── Derived Column transform ─────────────────────────────────────────
ADF_DATAFLOW_DERIVED_COLUMN: dict[str, Any] = {
    "name": "{{TRANSFORM_NAME}}",
    "description": "Apply column transformations",
    "script": '{{INPUT_STREAM}} derive(\n{{DERIVED_EXPRESSIONS}}\n) ~> {{TRANSFORM_NAME}}',
}

# ── Select / Column Mapping transform ─────────────────────────────────
ADF_DATAFLOW_SELECT: dict[str, Any] = {
    "name": "{{TRANSFORM_NAME}}",
    "description": "Map and rename columns",
    "script": '{{INPUT_STREAM}} select(mapColumn(\n{{COLUMN_MAPPINGS}}\n),\nskipDuplicateMapInputs: true,\nskipDuplicateMapOutputs: true) ~> {{TRANSFORM_NAME}}',
}

# ── Filter transform ─────────────────────────────────────────────────
ADF_DATAFLOW_FILTER: dict[str, Any] = {
    "name": "{{TRANSFORM_NAME}}",
    "description": "Filter rows: {{FILTER_DESCRIPTION}}",
    "script": '{{INPUT_STREAM}} filter(\n{{FILTER_EXPRESSION}}\n) ~> {{TRANSFORM_NAME}}',
}

# ── Aggregate transform ──────────────────────────────────────────────
ADF_DATAFLOW_AGGREGATE: dict[str, Any] = {
    "name": "{{TRANSFORM_NAME}}",
    "description": "Aggregate data",
    "script": '{{INPUT_STREAM}} aggregate(groupBy(\n{{GROUP_COLUMNS}}\n),\n{{AGGREGATE_EXPRESSIONS}}\n) ~> {{TRANSFORM_NAME}}',
}

# ── Lookup / Join transform ───────────────────────────────────────────
ADF_DATAFLOW_LOOKUP: dict[str, Any] = {
    "name": "{{TRANSFORM_NAME}}",
    "description": "Lookup from {{LOOKUP_TABLE}}",
    "script": '{{INPUT_STREAM}}, {{LOOKUP_STREAM}} lookup(\n{{JOIN_CONDITION}},\nmultiple: false,\npickup: \'first\',\nbroadcast: \'auto\') ~> {{TRANSFORM_NAME}}',
}

# ── Conditional Split transform ───────────────────────────────────────
ADF_DATAFLOW_CONDITIONAL_SPLIT: dict[str, Any] = {
    "name": "{{TRANSFORM_NAME}}",
    "description": "Route rows by condition",
    "script": '{{INPUT_STREAM}} split(\n{{SPLIT_CONDITIONS}},\ndisjoint: false) ~> {{TRANSFORM_NAME}}@({{OUTPUT_STREAMS}})',
}

# ── Surrogate Key transform ──────────────────────────────────────────
ADF_DATAFLOW_SURROGATE_KEY: dict[str, Any] = {
    "name": "{{TRANSFORM_NAME}}",
    "description": "Add surrogate key column",
    "script": '{{INPUT_STREAM}} keyGenerate(output({{KEY_COLUMN}} as long),\nstartAt: 1L) ~> {{TRANSFORM_NAME}}',
}

# ── Union transform (append multiple streams) ────────────────────────
ADF_DATAFLOW_UNION: dict[str, Any] = {
    "name": "{{TRANSFORM_NAME}}",
    "description": "Union multiple data streams",
    "script": '{{INPUT_STREAM1}}, {{INPUT_STREAM2}} union(byName: true) ~> {{TRANSFORM_NAME}}',
}

# ── Exists transform (semi-join: keep rows that exist in lookup) ──────
ADF_DATAFLOW_EXISTS: dict[str, Any] = {
    "name": "{{TRANSFORM_NAME}}",
    "description": "Keep rows that exist in {{LOOKUP_STREAM}}",
    "script": '{{INPUT_STREAM}}, {{LOOKUP_STREAM}} exists(\n{{JOIN_CONDITION}},\nnegate: {{NEGATE}},\nbroadcast: \'auto\') ~> {{TRANSFORM_NAME}}',
}

# ── Alter Row transform (upsert/insert/update/delete policy) ─────────
ADF_DATAFLOW_ALTER_ROW: dict[str, Any] = {
    "name": "{{TRANSFORM_NAME}}",
    "description": "Set row modification policy",
    "script": '{{INPUT_STREAM}} alterRow(\n{{ALTER_CONDITIONS}}\n) ~> {{TRANSFORM_NAME}}',
}


# ── Full Mapping Data Flow container template ─────────────────────────

ADF_MAPPING_DATAFLOW_TEMPLATE: dict[str, Any] = {
    "name": "{{DATAFLOW_NAME}}",
    "properties": {
        "type": "MappingDataFlow",
        "typeProperties": {
            "sources": [],       # Populated from source transforms
            "sinks": [],         # Populated from sink transforms
            "transformations": [],  # Populated from transformation chain
            "scriptLines": [],   # Full DFS script lines
        },
    },
}

# ── ADF Mapping Data Flow Pipeline (runs a data flow) ────────────────

ADF_DATAFLOW_PIPELINE_TEMPLATE: dict[str, Any] = {
    "name": "{{PIPELINE_NAME}}",
    "properties": {
        "activities": [
            {
                "name": "Execute_{{DATAFLOW_NAME}}",
                "type": "ExecuteDataFlow",
                "typeProperties": {
                    "dataflow": {
                        "referenceName": "{{DATAFLOW_NAME}}",
                        "type": "DataFlowReference",
                    },
                    "compute": {
                        "coreCount": 8,
                        "computeType": "General",
                    },
                    "traceLevel": "Fine",
                },
                "policy": {
                    "timeout": "1.00:00:00",
                    "retry": 0,
                    "retryIntervalInSeconds": 30,
                },
            }
        ],
    },
}


# ══════════════════════════════════════════════════════════════════════
# SYNAPSE DATA FLOW TEMPLATES (Spark-based with transforms)
# ══════════════════════════════════════════════════════════════════════

SYNAPSE_DATAFLOW_NOTEBOOK_TEMPLATE: dict[str, Any] = {
    "name": "{{NOTEBOOK_NAME}}",
    "properties": {
        "nbformat": 4,
        "nbformat_minor": 2,
        "cells": [
            {
                "cell_type": "code",
                "source": [
                    "# Auto-generated ETL/ELT Notebook by DA-MACAÉ Pipeline Agent\n",
                    "# Includes column-level transformations\n",
                    "from pyspark.sql import SparkSession\n",
                    "from pyspark.sql import functions as F\n",
                    "from pyspark.sql.types import *\n",
                    "\n",
                    "spark = SparkSession.builder.getOrCreate()\n",
                ],
                "metadata": {},
                "outputs": [],
            },
            {
                "cell_type": "code",
                "source": [
                    "# ── Extract: Read from source ──\n",
                    "{{EXTRACT_CODE}}\n",
                ],
                "metadata": {},
                "outputs": [],
            },
            {
                "cell_type": "code",
                "source": [
                    "# ── Transform: Apply column mappings and transformations ──\n",
                    "{{TRANSFORM_CODE}}\n",
                ],
                "metadata": {},
                "outputs": [],
            },
            {
                "cell_type": "code",
                "source": [
                    "# ── Load: Write to target ──\n",
                    "{{LOAD_CODE}}\n",
                ],
                "metadata": {},
                "outputs": [],
            },
        ],
        "metadata": {
            "language_info": {"name": "python"},
            "a]_name": "synapse_pyspark",
        },
    },
}


# ══════════════════════════════════════════════════════════════════════
# FABRIC DATAFLOW GEN2 WITH TRANSFORMATIONS (Power Query M)
# ══════════════════════════════════════════════════════════════════════

FABRIC_DATAFLOW_GEN2_TRANSFORM_TEMPLATE: dict[str, Any] = {
    "name": "{{DATAFLOW_NAME}}",
    "description": "Auto-generated ETL Dataflow by DA-MACAÉ Pipeline Agent",
    "mashup": {
        "document": "{{M_SCRIPT}}",
        "queryGroups": [],
    },
    "destinationSettings": {
        "loadToLakehouse": {
            "lakehouseId": "{{LAKEHOUSE_ID}}",
            "tableName": "{{TARGET_TABLE}}",
            "loadType": "{{LOAD_TYPE}}",
        }
    },
}


# ══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS — Build data flow artifacts from transformation maps
# ══════════════════════════════════════════════════════════════════════


def build_column_mapping(
    source_columns: list[dict[str, str]],
    target_columns: list[dict[str, str]],
    transformations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Build a structured transformation mapping document.

    Each source_column: {"name": "col", "type": "varchar(50)", "nullable": true}
    Each target_column: {"name": "col", "type": "varchar(100)", "nullable": true}
    Each transformation: {
        "source_column": "first_name",
        "target_column": "full_name",
        "expression_type": "concat",
        "params": {"column1": "first_name", "separator": " ", "column2": "last_name"}
    }
    """
    # Auto-pair columns by name if no explicit transformations
    if transformations is None:
        transformations = []

    transformed_targets = {t["target_column"] for t in transformations}

    # Build direct mappings for columns not in transformations
    direct_mappings = []
    for sc in source_columns:
        matching_tc = next(
            (tc for tc in target_columns if tc["name"].lower() == sc["name"].lower()),
            None,
        )
        if matching_tc and matching_tc["name"] not in transformed_targets:
            needs_cast = sc["type"].lower() != matching_tc["type"].lower()
            direct_mappings.append({
                "source_column": sc["name"],
                "source_type": sc["type"],
                "target_column": matching_tc["name"],
                "target_type": matching_tc["type"],
                "transformation": "type_cast" if needs_cast else "direct",
                "expression": None,
            })

    return {
        "direct_mappings": direct_mappings,
        "transformation_mappings": transformations,
        "unmapped_source_columns": [
            sc["name"] for sc in source_columns
            if not any(
                dm["source_column"].lower() == sc["name"].lower()
                for dm in direct_mappings
            )
            and not any(
                t.get("source_column", "").lower() == sc["name"].lower()
                for t in transformations
            )
        ],
        "unmapped_target_columns": [
            tc["name"] for tc in target_columns
            if not any(
                dm["target_column"].lower() == tc["name"].lower()
                for dm in direct_mappings
            )
            and not any(
                t.get("target_column", "").lower() == tc["name"].lower()
                for t in transformations
            )
        ],
    }


def build_adf_dataflow_script(
    source_name: str,
    source_dataset: str,
    sink_name: str,
    sink_dataset: str,
    column_mappings: list[dict[str, Any]],
    derived_columns: list[dict[str, str]] | None = None,
    filter_expression: str | None = None,
    lookup_config: dict[str, Any] | None = None,
    surrogate_key_column: str | None = None,
) -> list[str]:
    """
    Build the script lines for an ADF Mapping Data Flow.

    Returns a list of DFS script lines that define the complete data flow.
    """
    lines: list[str] = []
    current_stream = source_name

    # 1. Source
    lines.append(
        f"source(allowSchemaDrift: true,\n"
        f"    validateSchema: false) ~> {source_name}"
    )

    # 2. Filter (optional)
    if filter_expression:
        filter_name = f"Filter{source_name}"
        lines.append(
            f"{current_stream} filter(\n"
            f"    {filter_expression}\n"
            f") ~> {filter_name}"
        )
        current_stream = filter_name

    # 3. Lookup / Join (optional)
    if lookup_config:
        lookup_name = f"Lookup{lookup_config.get('lookup_table', 'Ref')}"
        lookup_stream = lookup_config.get("lookup_stream", "LookupSource")
        join_cond = lookup_config.get("join_condition", "true()")
        lines.append(
            f"source(allowSchemaDrift: true,\n"
            f"    validateSchema: false) ~> {lookup_stream}"
        )
        lines.append(
            f"{current_stream}, {lookup_stream} lookup(\n"
            f"    {join_cond},\n"
            f"    multiple: false,\n"
            f"    pickup: 'first',\n"
            f"    broadcast: 'auto') ~> {lookup_name}"
        )
        current_stream = lookup_name

    # 4. Surrogate Key (optional)
    if surrogate_key_column:
        sk_name = "AddSurrogateKey"
        lines.append(
            f"{current_stream} keyGenerate(output({surrogate_key_column} as long),\n"
            f"    startAt: 1L) ~> {sk_name}"
        )
        current_stream = sk_name

    # 5. Derived Column (transformations)
    if derived_columns:
        derive_name = "ApplyTransformations"
        expr_lines = ",\n    ".join(
            f"{dc['target_column']} = {dc['expression']}" for dc in derived_columns
        )
        lines.append(
            f"{current_stream} derive(\n"
            f"    {expr_lines}\n"
            f") ~> {derive_name}"
        )
        current_stream = derive_name

    # 6. Select / Column Mapping
    if column_mappings:
        select_name = "MapColumns"
        mapping_lines = ",\n    ".join(
            f"{m['target_column']} = {m.get('source_expression', m['source_column'])}"
            if m.get("source_expression")
            else (
                f"{m['target_column']} = {m['source_column']}"
                if m["source_column"] != m["target_column"]
                else m["target_column"]
            )
            for m in column_mappings
        )
        lines.append(
            f"{current_stream} select(mapColumn(\n"
            f"    {mapping_lines}\n"
            f"),\n"
            f"    skipDuplicateMapInputs: true,\n"
            f"    skipDuplicateMapOutputs: true) ~> {select_name}"
        )
        current_stream = select_name

    # 7. Sink
    lines.append(
        f"{current_stream} sink(allowSchemaDrift: true,\n"
        f"    validateSchema: false,\n"
        f"    truncate: false,\n"
        f"    skipDuplicateMapInputs: true,\n"
        f"    skipDuplicateMapOutputs: true) ~> {sink_name}"
    )

    return lines


def build_adf_mapping_dataflow(
    dataflow_name: str,
    source_dataset: str,
    target_dataset: str,
    source_table: str,
    target_table: str,
    column_mappings: list[dict[str, Any]],
    derived_columns: list[dict[str, str]] | None = None,
    filter_expression: str | None = None,
    lookup_config: dict[str, Any] | None = None,
    surrogate_key_column: str | None = None,
) -> dict[str, Any]:
    """
    Build a complete ADF Mapping Data Flow JSON definition with
    transformation activities.
    """
    source_name = f"Source{source_table.replace('.', '').replace(' ', '')}"
    sink_name = f"Sink{target_table.replace('.', '').replace(' ', '')}"

    script_lines = build_adf_dataflow_script(
        source_name=source_name,
        source_dataset=source_dataset,
        sink_name=sink_name,
        sink_dataset=target_dataset,
        column_mappings=column_mappings,
        derived_columns=derived_columns,
        filter_expression=filter_expression,
        lookup_config=lookup_config,
        surrogate_key_column=surrogate_key_column,
    )

    sources = [{
        "dataset": {"referenceName": source_dataset, "type": "DatasetReference"},
        "name": source_name,
    }]
    sinks = [{
        "dataset": {"referenceName": target_dataset, "type": "DatasetReference"},
        "name": sink_name,
    }]

    # Build transformations list from script analysis
    transformations = []
    for line in script_lines:
        if "~>" in line:
            name = line.split("~>")[-1].strip()
            if name not in (source_name, sink_name) and not name.startswith("source"):
                transformations.append({"name": name})

    # Add lookup source if present
    if lookup_config:
        lookup_stream = lookup_config.get("lookup_stream", "LookupSource")
        lookup_dataset = lookup_config.get("lookup_dataset", "")
        sources.append({
            "dataset": {"referenceName": lookup_dataset, "type": "DatasetReference"},
            "name": lookup_stream,
        })

    return {
        "name": dataflow_name,
        "properties": {
            "type": "MappingDataFlow",
            "typeProperties": {
                "sources": sources,
                "sinks": sinks,
                "transformations": transformations,
                "scriptLines": script_lines,
            },
        },
    }


def build_adf_dataflow_pipeline(
    pipeline_name: str,
    dataflow_name: str,
    compute_core_count: int = 8,
    compute_type: str = "General",
) -> dict[str, Any]:
    """Build an ADF pipeline that executes a mapping data flow."""
    return {
        "name": pipeline_name,
        "properties": {
            "activities": [
                {
                    "name": f"Execute_{dataflow_name}",
                    "type": "ExecuteDataFlow",
                    "typeProperties": {
                        "dataflow": {
                            "referenceName": dataflow_name,
                            "type": "DataFlowReference",
                        },
                        "compute": {
                            "coreCount": compute_core_count,
                            "computeType": compute_type,
                        },
                        "traceLevel": "Fine",
                    },
                    "policy": {
                        "timeout": "1.00:00:00",
                        "retry": 0,
                        "retryIntervalInSeconds": 30,
                    },
                }
            ],
        },
    }


def build_synapse_etl_notebook(
    notebook_name: str,
    source_format: str,
    source_url: str,
    source_table: str,
    target_format: str,
    target_url: str,
    target_table: str,
    column_mappings: list[dict[str, Any]],
    transformations: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Build a Synapse Spark notebook with ETL transformations using PySpark.
    """
    # Build extract code
    extract_lines = [
        f'source_df = spark.read.format("{source_format}") \\\n',
        f'    .option("url", "{source_url}") \\\n',
        f'    .option("dbtable", "{source_table}") \\\n',
        "    .load()\n",
        "\n",
        f'print(f"Source row count: {{source_df.count()}}")\n',
        'source_df.printSchema()\n',
    ]

    # Build transform code
    transform_lines = ["# Apply column mappings and transformations\n", "df = source_df\n", "\n"]

    # Column renames
    renames = [m for m in column_mappings if m["source_column"] != m["target_column"]]
    if renames:
        transform_lines.append("# Column renames\n")
        for m in renames:
            transform_lines.append(
                f'df = df.withColumnRenamed("{m["source_column"]}", "{m["target_column"]}")\n'
            )
        transform_lines.append("\n")

    # Transformations
    if transformations:
        transform_lines.append("# Column transformations\n")
        for t in transformations:
            transform_lines.append(
                f'df = df.withColumn("{t["target_column"]}", {t["expression"]})\n'
            )
        transform_lines.append("\n")

    # Column selection
    target_cols = [m["target_column"] for m in column_mappings]
    if transformations:
        target_cols.extend(t["target_column"] for t in transformations if t["target_column"] not in target_cols)
    if target_cols:
        col_list = ", ".join(f'"{c}"' for c in target_cols)
        transform_lines.append(f"df = df.select({col_list})\n")
        transform_lines.append("\n")

    transform_lines.append(f'print(f"Transformed row count: {{df.count()}}")\n')
    transform_lines.append("df.printSchema()\n")

    # Build load code
    load_lines = [
        f'df.write.format("{target_format}") \\\n',
        f'    .option("url", "{target_url}") \\\n',
        f'    .option("dbtable", "{target_table}") \\\n',
        '    .mode("append") \\\n',
        "    .save()\n",
        "\n",
        f'print("Successfully loaded data to {target_table}")\n',
    ]

    return {
        "name": notebook_name,
        "properties": {
            "nbformat": 4,
            "nbformat_minor": 2,
            "cells": [
                {
                    "cell_type": "code",
                    "source": [
                        "# Auto-generated ETL Notebook by DA-MACAÉ Pipeline Agent\n",
                        "from pyspark.sql import SparkSession\n",
                        "from pyspark.sql import functions as F\n",
                        "from pyspark.sql.types import *\n",
                        "\n",
                        "spark = SparkSession.builder.getOrCreate()\n",
                    ],
                    "metadata": {},
                    "outputs": [],
                },
                {
                    "cell_type": "code",
                    "source": extract_lines,
                    "metadata": {},
                    "outputs": [],
                },
                {
                    "cell_type": "code",
                    "source": transform_lines,
                    "metadata": {},
                    "outputs": [],
                },
                {
                    "cell_type": "code",
                    "source": load_lines,
                    "metadata": {},
                    "outputs": [],
                },
            ],
            "metadata": {
                "language_info": {"name": "python"},
                "a]_name": "synapse_pyspark",
            },
        },
    }


def build_fabric_m_script(
    source_connector: str,
    source_params: str,
    schema_name: str,
    table_name: str,
    query_name: str,
    column_mappings: list[dict[str, Any]],
    transformations: list[dict[str, str]] | None = None,
) -> str:
    """
    Build a Power Query M script with column transformations for
    Fabric Dataflow Gen2.
    """
    # Start the M script
    lines = [
        f'section Section1;\nshared {query_name} = let',
        f'    Source = {source_connector}({source_params}),',
        f'    Data = Source{{[Schema="{schema_name}",Item="{table_name}"]}}[Data],',
    ]

    step_counter = 1

    # Column renames
    renames = [m for m in column_mappings if m["source_column"] != m["target_column"]]
    if renames:
        rename_pairs = ", ".join(
            f'{{"{m["source_column"]}", "{m["target_column"]}"}}'
            for m in renames
        )
        step_name = f"RenameColumns"
        lines.append(
            f'    {step_name} = Table.RenameColumns(Data, {{{rename_pairs}}}),',
        )
        prev_step = step_name
        step_counter += 1
    else:
        prev_step = "Data"

    # Apply transformations
    if transformations:
        for i, t in enumerate(transformations):
            step_name = f"Transform{i + 1}"
            lines.append(
                f'    {step_name} = Table.TransformColumns({prev_step}, '
                f'{{{{"{t["target_column"]}", each {t["expression"]}, type text}}}}),',
            )
            prev_step = step_name

    # Add custom / derived columns
    derived = [t for t in (transformations or []) if t.get("is_derived")]
    for i, d in enumerate(derived):
        step_name = f"AddColumn{i + 1}"
        lines.append(
            f'    {step_name} = Table.AddColumn({prev_step}, '
            f'"{d["target_column"]}", each {d["expression"]}),',
        )
        prev_step = step_name

    # Select final columns
    target_cols = [m["target_column"] for m in column_mappings]
    if transformations:
        for t in transformations:
            if t["target_column"] not in target_cols:
                target_cols.append(t["target_column"])
    if target_cols:
        col_list = ", ".join(f'"{c}"' for c in target_cols)
        step_name = "SelectColumns"
        lines.append(
            f'    {step_name} = Table.SelectColumns({prev_step}, {{{col_list}}}),',
        )
        prev_step = step_name

    # Close the let/in
    # Remove trailing comma from last step
    lines[-1] = lines[-1].rstrip(",")
    lines.append(f'in\n    {prev_step};')

    return "\n".join(lines)


def build_fabric_dataflow_gen2_with_transforms(
    dataflow_name: str,
    source_connector: str,
    source_params: str,
    schema_name: str,
    table_name: str,
    lakehouse_id: str,
    target_table: str,
    column_mappings: list[dict[str, Any]],
    transformations: list[dict[str, str]] | None = None,
    load_type: str = "Append",
) -> dict[str, Any]:
    """Build a Fabric Dataflow Gen2 JSON with Power Query M transformations."""
    query_name = table_name.replace(" ", "_").replace(".", "_")

    m_script = build_fabric_m_script(
        source_connector=source_connector,
        source_params=source_params,
        schema_name=schema_name,
        table_name=table_name,
        query_name=query_name,
        column_mappings=column_mappings,
        transformations=transformations,
    )

    return {
        "name": dataflow_name,
        "description": "Auto-generated ETL Dataflow by DA-MACAÉ Pipeline Agent",
        "mashup": {
            "document": m_script,
            "queryGroups": [],
        },
        "destinationSettings": {
            "loadToLakehouse": {
                "lakehouseId": lakehouse_id,
                "tableName": target_table,
                "loadType": load_type,
            }
        },
    }
