#!/usr/bin/env python3
"""
Atomic file operations for the training plan pipeline.

Ensures files are written completely or not at all, preventing partial state.
"""

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


@contextmanager
def atomic_write(target_path: Path, mode: str = 'w'):
    """
    Context manager for atomic file writes.

    Writes to a temp file first, then atomically moves to target.
    If an exception occurs, the temp file is cleaned up and target is unchanged.

    Usage:
        with atomic_write(Path('output.yaml')) as f:
            yaml.dump(data, f)

    Args:
        target_path: Final destination path
        mode: File mode ('w' for text, 'wb' for binary)
    """
    target_path = Path(target_path)
    target_dir = target_path.parent

    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    # Create temp file in same directory (for atomic rename to work)
    fd, temp_path = tempfile.mkstemp(
        dir=target_dir,
        prefix=f'.{target_path.name}.',
        suffix='.tmp'
    )

    try:
        with os.fdopen(fd, mode) as f:
            yield f

        # Atomic rename (on POSIX systems)
        os.replace(temp_path, target_path)

    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def atomic_copy(src: Path, dst: Path) -> bool:
    """
    Atomically copy a file.

    Copies to temp location first, then renames.

    Args:
        src: Source file path
        dst: Destination file path

    Returns:
        True if successful, False otherwise
    """
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in destination directory
    fd, temp_path = tempfile.mkstemp(
        dir=dst.parent,
        prefix=f'.{dst.name}.',
        suffix='.tmp'
    )
    os.close(fd)

    try:
        shutil.copy2(src, temp_path)
        os.replace(temp_path, dst)
        return True

    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        return False


def atomic_write_dir(target_dir: Path):
    """
    Context manager for atomically writing multiple files to a directory.

    Creates files in a temp directory first, then replaces target directory.
    If an exception occurs, the temp directory is cleaned up.

    Usage:
        with atomic_write_dir(Path('workouts')) as temp_dir:
            for workout in workouts:
                (temp_dir / workout.name).write_text(workout.content)

    Args:
        target_dir: Final destination directory
    """
    return AtomicDirWriter(target_dir)


class AtomicDirWriter:
    """Context manager for atomic directory writes."""

    def __init__(self, target_dir: Path):
        self.target_dir = Path(target_dir)
        self.temp_dir: Optional[Path] = None
        self.backup_dir: Optional[Path] = None

    def __enter__(self) -> Path:
        """Create temp directory and return its path."""
        self.temp_dir = Path(tempfile.mkdtemp(
            dir=self.target_dir.parent,
            prefix=f'.{self.target_dir.name}.',
            suffix='.tmp'
        ))
        return self.temp_dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        """On success, replace target with temp. On failure, clean up."""
        if exc_type is not None:
            # Exception occurred - clean up temp dir
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            return False

        try:
            # Move existing target to backup
            if self.target_dir.exists():
                self.backup_dir = Path(tempfile.mkdtemp(
                    dir=self.target_dir.parent,
                    prefix=f'.{self.target_dir.name}.',
                    suffix='.bak'
                ))
                shutil.rmtree(self.backup_dir)
                shutil.move(str(self.target_dir), str(self.backup_dir))

            # Move temp to target
            shutil.move(str(self.temp_dir), str(self.target_dir))

            # Remove backup on success
            if self.backup_dir and self.backup_dir.exists():
                shutil.rmtree(self.backup_dir, ignore_errors=True)

        except Exception:
            # Restore from backup if it exists
            if self.backup_dir and self.backup_dir.exists():
                try:
                    if self.target_dir.exists():
                        shutil.rmtree(self.target_dir)
                    shutil.move(str(self.backup_dir), str(self.target_dir))
                except Exception:
                    pass

            # Clean up temp
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)

            raise

        return False


def safe_write_yaml(path: Path, data: dict):
    """Safely write YAML data atomically."""
    import yaml

    with atomic_write(path) as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def safe_write_json(path: Path, data: dict, indent: int = 2):
    """Safely write JSON data atomically."""
    import json

    with atomic_write(path) as f:
        json.dump(data, f, indent=indent)


if __name__ == '__main__':
    # Test atomic operations
    import tempfile as tf

    test_dir = Path(tf.mkdtemp())
    print(f"Testing in: {test_dir}")

    # Test atomic_write
    test_file = test_dir / 'test.txt'
    with atomic_write(test_file) as f:
        f.write("Hello, world!")
    assert test_file.read_text() == "Hello, world!"
    print("✓ atomic_write works")

    # Test atomic_copy
    copy_file = test_dir / 'copy.txt'
    assert atomic_copy(test_file, copy_file)
    assert copy_file.read_text() == "Hello, world!"
    print("✓ atomic_copy works")

    # Test atomic_write_dir
    output_dir = test_dir / 'output'
    with atomic_write_dir(output_dir) as temp:
        (temp / 'file1.txt').write_text("File 1")
        (temp / 'file2.txt').write_text("File 2")
    assert (output_dir / 'file1.txt').read_text() == "File 1"
    assert (output_dir / 'file2.txt').read_text() == "File 2"
    print("✓ atomic_write_dir works")

    # Clean up
    shutil.rmtree(test_dir)
    print("\nAll tests passed!")
