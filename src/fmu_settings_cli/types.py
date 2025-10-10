"""Additional types for typing."""

from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    # https://github.com/python/typeshed/issues/7539
    import argparse

    SubparserType: TypeAlias = argparse._SubParsersAction[argparse.ArgumentParser]
else:
    SubparserType: TypeAlias = Any
