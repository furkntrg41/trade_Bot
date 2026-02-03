"""
Application - Hot-Reload Configuration Watcher
===============================================
Watch YAML config for changes, reload services WITHOUT restart.

Design Pattern: Observer Pattern
Thread-Safety: Uses threading.Thread + file system watcher

Benefits:
- A/B testing: Toggle providers without downtime
- Emergency disable: Bad provider → edit YAML → auto-reload
- Production-grade: No manual restarts

Complexity:
- Watch overhead: O(1) - async file system events
- Reload: O(n) where n = providers (same as init)
"""
import logging
import time
import threading
from pathlib import Path
from typing import Callable, Optional
import hashlib

logger = logging.getLogger(__name__)


class ConfigWatcher:
    """
    File system watcher for hot-reload (production-grade).
    
    Method:
    1. Calculate MD5 hash of config file
    2. Poll every N seconds
    3. On change: trigger callback
    
    Alternative (advanced): Use watchdog library for inotify/FSEvents
    
    Complexity:
    - Poll overhead: O(1) hash calculation
    - Memory: O(1) just hash storage
    - CPU: Minimal (poll interval = 5s default)
    """
    
    def __init__(
        self,
        config_path: str,
        callback: Callable,
        poll_interval: float = 5.0
    ):
        """
        Args:
            config_path: Path to YAML config
            callback: Function to call on change (reload logic)
            poll_interval: Seconds between checks (5s default)
        """
        self.config_path = Path(config_path)
        self.callback = callback
        self.poll_interval = poll_interval
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_hash: Optional[str] = None
        
        if not self.config_path.exists():
            logger.error(f"Config file not found: {config_path}")
    
    def _calculate_hash(self) -> str:
        """
        Calculate MD5 hash of config file.
        
        Time: O(n) where n = file size (typically < 10KB → < 1ms)
        
        Returns:
            MD5 hex digest
        """
        try:
            with open(self.config_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.error(f"Hash calculation failed: {e}")
            return ""
    
    def _watch_loop(self):
        """
        Background thread loop (Observer Pattern).
        
        Runs until stop() called.
        """
        logger.info(f"🔍 Config watcher started: {self.config_path}")
        
        # Initial hash
        self._last_hash = self._calculate_hash()
        
        while self._running:
            try:
                # Sleep first (avoid busy-wait)
                time.sleep(self.poll_interval)
                
                # Calculate current hash
                current_hash = self._calculate_hash()
                
                # Detect change
                if current_hash != self._last_hash and current_hash:
                    logger.warning(f"🔄 Config changed! Hash: {self._last_hash[:8]} → {current_hash[:8]}")
                    
                    # Trigger callback (reload services)
                    try:
                        self.callback()
                        logger.info("✅ Hot-reload completed")
                    except Exception as e:
                        logger.error(f"❌ Hot-reload failed: {e}")
                    
                    # Update hash
                    self._last_hash = current_hash
            
            except Exception as e:
                logger.error(f"Watcher error: {e}")
                # Continue watching despite errors
        
        logger.info("🛑 Config watcher stopped")
    
    def start(self):
        """
        Start background watcher thread.
        
        Non-blocking: Returns immediately, watch runs in background.
        """
        if self._running:
            logger.warning("Watcher already running")
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,  # Auto-terminate when main thread exits
            name="ConfigWatcher"
        )
        self._thread.start()
        
        logger.info(f"✅ Config watcher thread started (poll: {self.poll_interval}s)")
    
    def stop(self):
        """
        Stop watcher thread gracefully.
        
        Blocks until thread terminates (max 2x poll_interval).
        """
        if not self._running:
            return
        
        logger.info("Stopping config watcher...")
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=self.poll_interval * 2)
        
        logger.info("✅ Config watcher stopped")
    
    def is_running(self) -> bool:
        """Check if watcher is active"""
        return self._running and self._thread is not None and self._thread.is_alive()


# =============================================================================
# ADVANCED: Use watchdog library for OS-level file events (optional)
# =============================================================================
class WatchdogConfigWatcher:
    """
    Advanced watcher using watchdog library (inotify on Linux, FSEvents on macOS).
    
    Benefits over polling:
    - Instant notification (no delay)
    - Lower CPU usage (event-driven, not polling)
    
    Drawbacks:
    - Extra dependency (pip install watchdog)
    - More complex implementation
    
    TODO: Implement if polling proves insufficient
    """
    pass


# =============================================================================
# EXAMPLE USAGE
# =============================================================================
if __name__ == "__main__":
    def on_config_change():
        print("Config changed! Reloading services...")
    
    watcher = ConfigWatcher("../config/providers.yaml", on_config_change, poll_interval=2.0)
    watcher.start()
    
    try:
        print("Watcher running. Edit providers.yaml to test. Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
