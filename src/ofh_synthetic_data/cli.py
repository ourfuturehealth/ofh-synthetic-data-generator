"""Command line interface for OFH synthetic data tooling."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from ofh_synthetic_data.config import AppConfig, load_config
from ofh_synthetic_data.export.decoded import write_decoded_outputs
from ofh_synthetic_data.generate.registry_generator import (
    generate_tables_from_processed_registries,
    write_generated_tables,
)
from ofh_synthetic_data.ingest.registries import build_registries
from ofh_synthetic_data.ingest.source_files import discover_inputs, missing_inputs
from ofh_synthetic_data.validate.outputs import validate_synthetic_outputs

DEFAULT_CONFIG = Path("configs/default.yaml")


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser and attach subcommand handlers."""
    parser = argparse.ArgumentParser(prog="ofh-synthetic-data")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to a YAML config file.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect-inputs", help="Check expected source files.")
    inspect_parser.set_defaults(handler=inspect_inputs)

    registry_parser = subparsers.add_parser(
        "build-registry",
        help="Build processed field, coding and logic registries from raw documentation.",
    )
    registry_parser.set_defaults(handler=build_registry)

    generate_parser = subparsers.add_parser("generate", help="Generate a synthetic CSV dataset.")
    generate_parser.add_argument("--rows", type=int, help="Override number of rows to generate.")
    generate_parser.add_argument("--seed", type=int, help="Override deterministic random seed.")
    generate_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for generated synthetic tables.",
    )
    generate_parser.add_argument(
        "--output",
        type=Path,
        help="Deprecated. If provided, its parent directory is used as the output directory.",
    )
    generate_parser.set_defaults(handler=generate)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate generated synthetic tables against processed registries.",
    )
    validate_parser.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing generated synthetic tables.",
    )
    validate_parser.set_defaults(handler=validate)

    export_qa_parser = subparsers.add_parser(
        "export-qa",
        help="Write manual QA copies of synthetic outputs with coded values decoded.",
    )
    export_qa_parser.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing generated synthetic tables.",
    )
    export_qa_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for decoded QA outputs.",
    )
    export_qa_parser.set_defaults(handler=export_qa)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the selected CLI subcommand."""
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    return args.handler(args, config)


def inspect_inputs(_args: argparse.Namespace, config: AppConfig) -> int:
    """Report whether the expected raw source files are present."""
    statuses = discover_inputs(config.paths.raw_data_dir, config.source_files)
    missing = missing_inputs(statuses)

    for status in statuses:
        marker = "ok" if status.exists else "missing"
        print(f"{marker:7} {status.role:21} {status.path}")

    return 1 if missing else 0


def build_registry(_args: argparse.Namespace, config: AppConfig) -> int:
    """Build processed registries from configured source artefacts."""
    result = build_registries(config)

    print(f"Wrote field registry to {result.field_registry}")
    print(f"Wrote coding registry to {result.coding_registry}")
    print(f"Wrote logic registry to {result.logic_registry}")
    print(f"Wrote entity registry to {result.entity_registry}")
    print(f"Wrote coverage summary to {result.coverage_summary}")
    print(f"Wrote source manifest to {result.source_manifest}")
    print(
        "Built registries: "
        f"{result.counts['fields']} fields, "
        f"{result.counts['codings']} coding rows, "
        f"{result.counts['logic_rows']} logic rows, "
        f"{result.counts['entities']} entities",
    )
    return 0


def generate(args: argparse.Namespace, config: AppConfig) -> int:
    """Generate participant and questionnaire CSV outputs."""
    generation_config = config.generation

    if args.rows is not None:
        generation_config = replace(generation_config, rows=args.rows)
    if args.seed is not None:
        generation_config = replace(generation_config, seed=args.seed)

    output_dir = (
        args.output_dir
        or _legacy_output_dir(args.output)
        or config.paths.synthetic_data_dir
    )
    tables = generate_tables_from_processed_registries(
        replace(config, generation=generation_config),
    )
    paths = write_generated_tables(tables, output_dir, generation_config)

    print(f"Wrote {len(tables.participants)} participant rows to {paths.participant}")
    print(f"Wrote {len(tables.questionnaires)} questionnaire rows to {paths.questionnaire}")
    print(f"Wrote manifest to {paths.manifest}")
    return 0


def validate(args: argparse.Namespace, config: AppConfig) -> int:
    """Validate generated outputs against processed registries."""
    input_dir = args.input_dir or config.paths.synthetic_data_dir
    result = validate_synthetic_outputs(config, input_dir=input_dir)

    if result.passed:
        print(f"Validation passed: {result.checks_run} checks run")
        return 0

    print(f"Validation failed: {len(result.errors)} error(s), {result.checks_run} checks run")
    for issue in result.errors:
        print(f"- {issue.check}: {issue.message}")
    return 1


def export_qa(args: argparse.Namespace, config: AppConfig) -> int:
    """Write decoded CSV copies for manual QA."""
    paths = write_decoded_outputs(
        config=config,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
    )

    print(f"Wrote decoded participant QA output to {paths.participant}")
    print(f"Wrote decoded questionnaire QA output to {paths.questionnaire}")
    print(f"Wrote decoded QA manifest to {paths.manifest}")
    return 0


def _legacy_output_dir(output: Path | None) -> Path | None:
    if output is None:
        return None
    if output.suffix:
        return output.parent
    return output


if __name__ == "__main__":
    raise SystemExit(main())
