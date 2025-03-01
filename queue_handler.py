#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import tempfile
import pickle
import threading
from typing import Any, Optional

class SharedQueue:
    """Thread-safe queue using file system for IPC."""
    
    def __init__(self, name: str = 'anj_dev_queue'):
        """Initialize queue."""
        self.name = name
        self.queue_file = os.path.join(tempfile.gettempdir(), f"{name}.queue")
        self.lock = threading.Lock()
        self._initialize()
        
    def _initialize(self):
        """Create queue file if it doesn't exist."""
        if not os.path.exists(self.queue_file):
            with open(self.queue_file, 'wb') as f:
                pickle.dump([], f)
                
    def put(self, item: Any):
        """Add item to queue."""
        with self.lock:
            try:
                with open(self.queue_file, 'rb') as f:
                    items = pickle.load(f)
            except:
                items = []
                
            items.append(item)
            
            with open(self.queue_file, 'wb') as f:
                pickle.dump(items, f)
                
    def get(self) -> Optional[Any]:
        """Get next item from queue."""
        with self.lock:
            try:
                with open(self.queue_file, 'rb') as f:
                    items = pickle.load(f)
                    
                if not items:
                    return None
                    
                item = items.pop(0)
                
                with open(self.queue_file, 'wb') as f:
                    pickle.dump(items, f)
                    
                return item
            except:
                return None
                
    def clear(self):
        """Clear the queue."""
        with self.lock:
            with open(self.queue_file, 'wb') as f:
                pickle.dump([], f)
                
    def __del__(self):
        """Clean up queue file."""
        try:
            if os.path.exists(self.queue_file):
                os.remove(self.queue_file)
        except:
            pass

# Global queue instance
log_queue = SharedQueue('anj_dev_logs')
