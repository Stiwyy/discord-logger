import asyncio
import threading
from queue import Queue, Empty
from concurrent.futures import Future
from typing import Any, Callable, Optional


class AsyncRunner:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, name="discord-async", daemon=True
        )
        self._thread.start()
        self._callbacks: Queue = Queue()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def run_bg(
        self,
        coro: Any,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        widget: Optional[Any] = None,
    ) -> Future:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        def _dispatch(f: Future) -> None:
            try:
                result = f.result()
            except Exception as exc:
                if on_error is not None:
                    on_error(exc)
            else:
                if on_success is not None:
                    on_success(result)

        def _done(f: Future) -> None:
            if widget is None:
                _dispatch(f)
            else:
                # Future callbacks run on the asyncio worker thread. Never call
                # Tk methods there; let a main-thread timer drain completions.
                self._callbacks.put((f, on_success, on_error))

        if widget is not None:
            def _drain():
                try:
                    while True:
                        f, success, error = self._callbacks.get_nowait()
                        try:
                            result = f.result()
                        except Exception as exc:
                            if error is not None:
                                error(exc)
                        else:
                            if success is not None:
                                success(result)
                except Empty:
                    pass
                if not future.done():
                    try:
                        widget.after(25, _drain)
                    except Exception:
                        pass
            widget.after(25, _drain)

        future.add_done_callback(_done)
        return future

    def close(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=2)
