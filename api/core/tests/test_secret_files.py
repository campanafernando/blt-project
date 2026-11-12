import os
import stat

from config import secret_files


def test_reads_the_file_and_strips_the_newline(tmp_path, monkeypatch):
    (tmp_path / "blt_password").write_text("from-file\n")
    monkeypatch.setenv("SECRETS_DIR", str(tmp_path))
    monkeypatch.setenv("BLT_PASSWORD", "from-env")
    assert secret_files.read_secret("blt_password") == "from-file"


def test_falls_back_to_the_environment_then_the_default(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRETS_DIR", str(tmp_path))
    monkeypatch.setattr(secret_files, "PROJECT_ROOT", tmp_path / "nowhere")
    monkeypatch.setenv("OPENCODE_API_KEY", "from-env")
    assert secret_files.read_secret("opencode_api_key") == "from-env"
    monkeypatch.delenv("OPENCODE_API_KEY")
    assert secret_files.read_secret("opencode_api_key") == ""
    assert secret_files.read_secret("opencode_api_key", "fallback") == "fallback"


def test_project_secrets_dir_is_used_outside_docker(tmp_path, monkeypatch):
    project = tmp_path / "project"
    (project / "secrets").mkdir(parents=True)
    (project / "secrets" / "postgres_password").write_text("local")
    monkeypatch.setenv("SECRETS_DIR", str(tmp_path / "missing"))
    monkeypatch.setattr(secret_files, "PROJECT_ROOT", project)
    assert secret_files.read_secret("postgres_password") == "local"


def test_secret_files_are_not_world_writable():
    # Guards the generated files if any exist locally (they are git-ignored).
    directory = secret_files.PROJECT_ROOT / "secrets"
    if directory.is_dir():
        assert not stat.S_IMODE(os.stat(directory).st_mode) & 0o077
