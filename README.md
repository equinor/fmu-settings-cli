# fmu-settings-cli

[![ci](https://github.com/equinor/fmu-settings-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/equinor/fmu-settings-cli/actions/workflows/ci.yml)

**fmu-settings-cli** is the CLI package for fmu-settings.

## Usage

To launch the application simply run

```bash
fmu-settings
```

To start only the API, run

```bash
fmu-settings api
```

It is also possible to specify the port and if the API should be reloaded, as
in during development.

```bash
fmu-settings api --port 8001 --reload
```

You can similarly start the GUI server:

```bash
fmu-settings gui
```

## Developing

Clone and install into a virtual environment.

```sh
git clone git@github.com:equinor/fmu-settings-cli.git
cd fmu-settings-cli
# Create or source virtual/Komodo env
pip install -U pip
pip install -e ".[dev]"
# Make a feature branch for your changes
git checkout -b some-feature-branch
```

Run the tests with

```sh
pytest -n auto tests
```

Ensure your changes will pass the various linters before making a pull
request. It is expected that all code will be typed and validated with
mypy.

```sh
ruff check
ruff format --check
mypy src tests
```

See the [contributing document](CONTRIBUTING.md) for more.
