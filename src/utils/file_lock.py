import os
import time
import errno
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Try to import Windows locking mechanism
try:
    import msvcrt
    def _lock_file(file):
        # Lock first 1 byte
        msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock_file(file):
        msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
        
    PLATFORM = "windows"
except ImportError:
    # Try Unix locking mechanism
    try:
        import fcntl
        def _lock_file(file):
            fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        def _unlock_file(file):
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)
            
        PLATFORM = "unix"
    except ImportError:
        # Fallback for systems without either (should be rare for standard Python)
        PLATFORM = "unknown"
        def _lock_file(file):
            pass
        def _unlock_file(file):
            pass
        logger.warning("File locking not supported on this platform.")

class FileLockException(Exception):
    pass

@contextmanager
def file_lock(lock_file_path, timeout=10, delay=0.1):
    """
    Cross-platform file locking context manager.
    Creates a separate .lock file to manage concurrency.
    
    Args:
        lock_file_path: Path to the file to lock (a .lock suffix will be appended if not present)
        timeout: Maximum time to wait for lock in seconds
        delay: Check interval in seconds
    """
    if not str(lock_file_path).endswith('.lock'):
        lock_path = str(lock_file_path) + '.lock'
    else:
        lock_path = str(lock_file_path)
        
    lock_fd = None
    start_time = time.time()
    
    try:
        # Loop until lock is acquired or timeout
        while True:
            try:
                # Open the lock file
                # Use 'w' to create if not exists, but we don't truncate or write content really
                # We just need a file descriptor to lock
                lock_fd = open(lock_path, 'w')
                
                # Try to acquire exclusive, non-blocking lock
                _lock_file(lock_fd)
                
                # If we got here, we have the lock
                yield lock_fd
                break
                
            except (IOError, OSError) as e:
                # Close the fd if we failed to lock it
                if lock_fd:
                    try:
                        lock_fd.close()
                    except:
                        pass
                    lock_fd = None
                
                # Check for timeout
                if (time.time() - start_time) >= timeout:
                    raise FileLockException(f"Timeout waiting for lock: {lock_path}")
                
                # Wait before retrying
                time.sleep(delay)
                
    finally:
        # Release lock and close file
        if lock_fd:
            try:
                _unlock_file(lock_fd)
            except:
                pass
            try:
                lock_fd.close()
            except:
                pass
            # Optional: Delete lock file? 
            # Deleting lock file can be race-condition prone on some systems if others are waiting on it.
            # Safe to leave it.
