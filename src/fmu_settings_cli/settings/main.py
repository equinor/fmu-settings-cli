"""The 'settings' command."""

import contextlib
import signal
import time
import urllib.request
import webbrowser
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from pathlib import Path

from fmu_settings_cli.prints import error, info, success

from ._utils import (
    create_authorized_url,
)
from .api_server import start_api_server

API_HEALTH_WAIT_TIMEOUT_SECONDS = 5


def init_worker() -> None:  # pragma: no cover
    """Initializer to ignore signal interrupts on workers."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)


def start_app(
    token: str,
    port: int,
    host: str,
    log_level: str,
    frontend_directory: Path,
) -> None:
    """Start the API and GUI in one application server.

    Args:
        token: Authentication token used to create the browser session.
        port: The port the application will bind to.
        host: The host the application will bind to.
        log_level: The log level to give to Uvicorn.
        frontend_directory: The directory that contains the built GUI.
    """
    with ProcessPoolExecutor(max_workers=1, initializer=init_worker) as executor:
        try:
            server_future = executor.submit(
                start_api_server,
                token,
                host=host,
                port=port,
                frontend_host=host,
                frontend_port=port,
                reload=False,
                log_level=log_level,
                frontend_directory=frontend_directory,
            )

            is_start_up = True
            health_url = f"http://{host}:{port}/health"
            health_deadline = time.monotonic() + API_HEALTH_WAIT_TIMEOUT_SECONDS
            while True:
                try:
                    # Check once a half second if the application server has
                    # completed. This will typically mean it crashed or otherwise
                    # failed.
                    server_future.result(timeout=0.5)
                    error(
                        "Application server unexpectedly exited. Please report this "
                        "as a bug",
                    )
                    break
                except TimeoutError:
                    # This is the valid case, where the server future did not complete
                    # within the 0.5 second timeout. While starting up, keep probing the
                    # health endpoint and open the GUI only after it returns HTTP 200.
                    if is_start_up:
                        try:
                            with urllib.request.urlopen(
                                health_url, timeout=0.5
                            ) as response:
                                is_app_ready = response.status == 200
                        except OSError:
                            is_app_ready = False

                        if is_app_ready:
                            success("FMU Settings is running. Press CTRL+C to quit")
                            webbrowser.open(create_authorized_url(token, host, port))
                            is_start_up = False
                        elif time.monotonic() >= health_deadline:
                            error(
                                "Application did not become ready within "
                                f"{API_HEALTH_WAIT_TIMEOUT_SECONDS} seconds. "
                                "Shutting down FMU Settings.",
                                reason="Health check failed.",
                            )
                            break
                    continue
                except SystemExit as e:
                    # Uvicorn raises SystemExit for fatal errors such as a port that is
                    # already in use. Its detailed error is only available in its log.
                    error(
                        f"Application server exited with exit code {e}. Usually this "
                        f"means that another application is already using port {port}.",
                    )
                    break
                except Exception as e:
                    # This is the exception raised by start_api_server.
                    error(f"Application server failed with: {e}")
                    break

        except KeyboardInterrupt:
            info("Shutting down FMU Settings ...")
        finally:
            server_future.cancel()

            # Uses the internal pid->process mapping. The executor API does not offer a
            # way to retrieve this information, oddly. There is a small possibility this
            # breaks in a future version of Python, although it is unlikely as it would
            # disrupt a great deal of CPython code.
            for process in executor._processes.values():
                with contextlib.suppress(Exception):
                    process.terminate()

            executor.shutdown(wait=False, cancel_futures=True)
