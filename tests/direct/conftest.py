"""Compatibility shim for genlayer-test 0.29.2 on Windows."""

import os

import pytest


@pytest.fixture(autouse=True)
def windows_direct_loader_tempfile_lifetime(monkeypatch):
    """Keep real Direct Mode message injection, but restore fd 0 after import.

    The pinned loader replaces fd 0 with a temporary calldata file and unlinks
    it immediately. POSIX allows unlinking an open file; Windows does not. On
    Windows, defer that one unlink until `_load_module` has decoded the message,
    then restore the original stdin before deleting the temp file.
    """
    if os.name != "nt":
        yield
        return

    from gltest.direct import loader

    original_inject = loader._inject_message_to_fd0
    original_load = loader._load_module
    pending_paths = []
    current_vm = [None]

    def inject_with_deferred_unlink(vm):
        current_vm[0] = vm
        original_unlink = os.unlink

        def defer_locked_temp_file(path, *args, **kwargs):
            try:
                original_unlink(path, *args, **kwargs)
            except PermissionError:
                pending_paths.append(path)

        with monkeypatch.context() as patch:
            patch.setattr(os, "unlink", defer_locked_temp_file)
            original_inject(vm)

    def load_then_restore_stdin(path):
        try:
            return original_load(path)
        finally:
            vm = current_vm[0]
            if vm is not None:
                stdin_fd = getattr(vm, "_original_stdin_fd", None)
                if stdin_fd is not None:
                    os.dup2(stdin_fd, 0)
                    os.close(stdin_fd)
                    vm._original_stdin_fd = None
            while pending_paths:
                temp_path = pending_paths.pop()
                try:
                    os.unlink(temp_path)
                except FileNotFoundError:
                    pass

    monkeypatch.setattr(loader, "_inject_message_to_fd0", inject_with_deferred_unlink)
    monkeypatch.setattr(loader, "_load_module", load_then_restore_stdin)
    yield
