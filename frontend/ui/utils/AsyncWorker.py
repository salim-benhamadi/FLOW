from PySide6.QtCore import Signal, QThread
import asyncio

import logging
from PySide6.QtCore import QThread, Signal

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AsyncWorker(QThread):
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int, str, str)

    def __init__(self, run_task, **kwargs):
        super().__init__()
        self.run_task = run_task
        self.kwargs = kwargs
        self._is_running = False
        self._loop = None
        self._task = None

    def run(self):
        try:
            self._is_running = True
            
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            result = self._loop.run_until_complete(self._safe_run_task())
            
            self.finished.emit(result)

        except Exception as e:
            logger.error("Error in worker: %s", str(e), exc_info=True)
            self.error.emit(str(e))
        finally:
            self._cleanup()

    async def _safe_run_task(self):
        try:
            self._task = asyncio.create_task(self.run_task(**self.kwargs))
            return await self._task
        except asyncio.CancelledError:
            raise Exception("Operation cancelled")
        except Exception as e:
            logger.error(f"Task execution error: {str(e)}")
            raise
        finally:
            pass

    def _cleanup(self):
        try:
            if self._loop and not self._loop.is_closed():
                pending_tasks = list(asyncio.all_tasks(self._loop))
                
                if pending_tasks:
                    for task in pending_tasks:
                        if not task.done():
                            task.cancel()
                    
                    try:
                        self._loop.run_until_complete(
                            asyncio.wait_for(
                                asyncio.gather(*pending_tasks, return_exceptions=True),
                                timeout=2.0
                            )
                        )
                    except (asyncio.TimeoutError, Exception) as e:
                        logger.debug(f"Task cleanup timeout or error: {e}")
                
                if not self._loop.is_closed():
                    self._loop.close()
        except Exception as e:
            logger.error("Error during cleanup: %s", str(e))
        finally:
            self._loop = None
            self._task = None
            self._is_running = False

    def stop(self):
        if self._is_running and self._loop and not self._loop.is_closed():
            try:
                self._loop.call_soon_threadsafe(self._cancel_task)
            except Exception as e:
                logger.error("Error cancelling task: %s", str(e))
        self.wait()
    
    def _cancel_task(self):
        if self._task and not self._task.done():
            self._task.cancel()