# fmu-settings-cli

[![ci](https://github.com/equinor/fmu-settings-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/equinor/fmu-settings-cli/actions/workflows/ci.yml)

**fmu-settings-cli** is the CLI package for fmu-settings.

## Usage

To launch the application simply run

```bash
fmu settings
```

To start only the API, run

```bash
fmu settings api
```

It is also possible to specify the port and if the API should be reloaded, as
in during development.

## Starting the API only

```bash
fmu settings api --port 8001
```

By default the API will set CORS rules restricting requests to a default host
and port (`localhost:8000`). In development with a GUI it's likely your
frontend port will be something different. You can specify this like so:

```bash
fmu settings api --gui-port 5173
```

This will update the CORS rules in the API to accept requests from
`localhost:5173`.

The API authorizes all requests with a randomly generated token. When starting
the API for use in development this token can be printed by setting the
`FMU_SETTINGS_PRINT_TOKEN` environment variable or providing the `--print-token`
flag.

```bash
fmu settings api --gui-port 5173 --print-token
# or
export FMU_SETTINGS_PRINT_TOKEN=true
# or
FMU_SETTINGS_PRINT_TOKEN=true fmu-settings api --gui-port 5173
```

It's also possible to print the full URL a user would be directed to with a
similar URL flag and environment variable.

```bash
fmu settings api --gui-port 5173 --print-url
# or
export FMU_SETTINGS_PRINT_URL=true
# or
FMU_SETTINGS_PRINT_URL=true fmu-settings api --gui-port 5173
```

Note that these additional flags are intended for development so they _only_ work
with `fmu settings api` subcommand.

## Starting the GUI only

You can similarly start the GUI server:

```bash
fmu settings gui
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
