#!/usr/bin/env python
from pathlib import Path
import shutil


BASE_PATH = Path("{{cookiecutter.library_name}}")
AUTH_METHOD = "{{ cookiecutter.auth_method }}"


if __name__ == "__main__":
    # Handle license selection
    license_choice = "{{ cookiecutter.license }}"
    if license_choice == "Apache-2.0":
        Path("LICENSE-Apache-2.0").rename("LICENSE")
        Path("LICENSE-MIT").unlink()
    elif license_choice == "MIT":
        Path("LICENSE-MIT").rename("LICENSE")
        Path("LICENSE-Apache-2.0").unlink()
    elif license_choice == "None":
        Path("LICENSE-Apache-2.0").unlink()
        Path("LICENSE-MIT").unlink()

    if "{{ cookiecutter.ide | default('VSCode') }}" != "VSCode":
        shutil.rmtree(".vscode", ignore_errors=True)

    # OAuth-only module: remove auth.py when not using OAuth2
    if AUTH_METHOD != "OAuth2":
        (BASE_PATH / "auth.py").unlink(missing_ok=True)

    agent_instructions = "{{ cookiecutter.include_agent_instructions }}"
    if agent_instructions == "CLAUDE.md":
        Path("AGENTS.md").rename("CLAUDE.md")
    elif agent_instructions == "None":
        Path("AGENTS.md").unlink(missing_ok=True)
