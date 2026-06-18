from pathlib import Path

from ofh_synthetic_data.config import AppConfig, load_config


def test_default_config_values() -> None:
    config = AppConfig()

    assert config.paths.raw_data_dir == Path("data/raw")
    assert config.paths.synthetic_data_dir == Path("outputs/synthetic")
    assert config.paths.qa_dir == Path("outputs/qa")
    assert config.generation.rows == 200


def test_load_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
paths:
  raw_data_dir: custom-raw
  processed_data_dir: custom-processed
generation:
  rows: 10
  seed: 123
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.paths.raw_data_dir == Path("custom-raw")
    assert config.paths.processed_data_dir == Path("custom-processed")
    assert config.generation.rows == 10
    assert config.generation.seed == 123


def test_load_config_accepts_legacy_reports_dir_as_qa_dir(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
paths:
  reports_dir: old-reports
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.paths.qa_dir == Path("old-reports")
