import re
import tkinter as tk
from datetime import datetime, timezone
from queue import SimpleQueue, Empty
import aiohttp

from discord_logger import config
from discord_logger.logger_core import MessageLogger

from .theme import (
    BG,
    BG_CARD,
    BG_ELEVATED,
    DANGER,
    SUCCESS,
    SUCCESS_DIM,
    TEXT,
    TEXT_FAINT,
    TEXT_MUTED,
    AUTHOR,
    font,
    mono,
)
from .widgets import RoundedButton, center_window, round_rect


class LogWindow(tk.Toplevel):
    def __init__(self, master, runner, client, target: dict):
        super().__init__(master)
        self.title(f"Discord Logger — {target['server']} / {target['channel']}")
        self.configure(bg=BG)
        self.minsize(720, 520)

        self.runner = runner
        self.client = client
        self.target = target

        self.logger = None
        self.queue = SimpleQueue()
        self._webhook_session = None
        self._webhook_started = False
        self._closing = False
        self._count = 0
        self._started_at = None

        self._build_ui()
        self._wire_events()
        center_window(self, 920, 600)

        self.after(50, self._start)
        self.after(80, self._pump)

    def show(self):
        self.wait_window(self)
        return True

    def _build_ui(self):
        header = tk.Frame(self, bg=BG_CARD)
        header.pack(fill="x", side="top")

        title = tk.Label(
            header,
            text=f"{self.target['server']}  ·  #{self.target['channel']}",
            bg=BG_CARD,
            fg=TEXT,
            font=font(13, "bold"),
            anchor="w",
        )
        title.pack(side="left", padx=16, pady=12)

        self.status = tk.Label(
            header,
            text="starting…",
            bg=BG_CARD,
            fg=TEXT_MUTED,
            font=font(10),
            anchor="e",
        )
        self.status.pack(side="right", padx=16)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(12, 0))

        self.text = tk.Text(
            body,
            bg=BG_ELEVATED,
            fg=TEXT,
            insertbackground=TEXT,
            font=mono(10),
            wrap="word",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=10,
            state="disabled",
        )
        self.text.pack(side="left", fill="both", expand=True)

        scroll = tk.Scrollbar(body, command=self.text.yview)
        scroll.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=scroll.set)

        self.text.tag_configure("author", foreground=AUTHOR, font=mono(10))
        self.text.tag_configure("time", foreground=TEXT_FAINT, font=mono(9))
        self.text.tag_configure("content", foreground=TEXT, font=mono(10))
        self.text.tag_configure("system", foreground=TEXT_MUTED, font=mono(9))
        self.text.tag_configure("error", foreground=DANGER, font=mono(10))
        self.text.tag_configure("ok", foreground=SUCCESS, font=mono(10))

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=16, pady=12)

        self.count_lbl = tk.Label(
            footer, text="0 messages", bg=BG, fg=TEXT_MUTED, font=font(10)
        )
        self.count_lbl.pack(side="left")

        self.stop_btn = RoundedButton(
            footer,
            text="Stop",
            command=self._on_stop,
            canvas_bg=BG,
            fill=DANGER,
            hover_fill=DANGER,
            active_fill=DANGER,
            fg=TEXT,
        )
        self.stop_btn.pack(side="right")

    def _wire_events(self):
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _start(self):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            webhook_url = (
                self.target.get("webhook")
                or getattr(config, "WEBHOOK_URL", None)
                or getattr(config, "load_webhook", lambda: None)()
            )
            self._started_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.logger = MessageLogger(
                client=self.client,
                target=self.target,
                on_message=self._on_logger_message,
                on_status=self._on_logger_status,
            )
            self.runner.run_bg(self._run_async(webhook_url))
        except Exception as exc:
            self.queue.put(("log", ("error", f"failed to start logger: {exc}")))

    async def _run_async(self, webhook_url):
        self._webhook_session = aiohttp.ClientSession()
        try:
            if webhook_url:
                ok = await self._send_webhook(
                    f"🟢 **Logger started** — `{self.target['server']} / "
                    f"#{self.target['channel']}`"
                )
                self._webhook_started = ok
                self.queue.put(
                    (
                        "log",
                        (
                            "ok" if ok else "error",
                            "webhook start message sent"
                            if ok
                            else "webhook start message failed",
                        ),
                    )
                )
            else:
                self.queue.put(("log", ("system", "no webhook configured")))

            try:
                await self.logger.run()
            except Exception as exc:
                self.queue.put(("log", ("error", f"logger error: {exc}")))
            finally:
                await self._shutdown_async()
        finally:
            if self._webhook_session is not None:
                try:
                    await self._webhook_session.close()
                except Exception:
                    pass
                self._webhook_session = None

    async def _shutdown_async(self):
        if self._closing:
            return
        self._closing = True
        if self._webhook_started:
            await self._send_webhook(
                f"🔴 **Logger stopped** — `{self.target['server']} / "
                f"#{self.target['channel']}`"
            )
        self.queue.put(("stopped", None))

    async def _send_webhook(self, content):
        if self._webhook_session is None:
            return False
        url = (
            self.target.get("webhook")
            or getattr(config, "WEBHOOK_URL", None)
            or getattr(config, "load_webhook", lambda: None)()
        )
        if not url:
            return False
        try:
            async with self._webhook_session.post(url, json={"content": content}) as r:
                return 200 <= r.status < 300
        except Exception as exc:
            self.queue.put(("log", ("error", f"webhook error: {exc}")))
            return False

    def _on_logger_message(self, message):
        self.queue.put(("msg", message))
        if self._webhook_started and self._is_after_start(message):
            try:
                self.runner.run_bg(self._forward_to_webhook(message))
            except Exception:
                pass

    def _on_logger_status(self, total):
        self.queue.put(("status", str(total)))

    def _is_after_start(self, message):
        if self._started_at is None:
            return True
        date = (message.get("date") or "").strip()
        time = (message.get("time") or "").strip()
        if not date or not time:
            return True
        try:
            msg_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return True
        return msg_dt >= self._started_at

    async def _forward_to_webhook(self, message):
        try:
            author = message.get("author") or "unknown"
            content = message.get("content") or "(empty)"
            date = message.get("date") or ""
            time = message.get("time") or ""
            stamp = f"{date} {time}".strip()
            body = (
                f"**[{self.target['server']} / #{self.target['channel']}] {author}**\n"
                f"`{stamp}`\n{content}"
            )
            for r in message.get("replies") or []:
                if r.get("deleted"):
                    body += f"\n↪ forwarded from msg ID: {r.get('ref_id')} [DELETED]"
                else:
                    body += (
                        f"\n↪ forwarded from {r.get('author', 'unknown')}: "
                        f"{r.get('content', '')}"
                    )
            await self._send_webhook(body)
        except Exception as exc:
            self.queue.put(("log", ("error", f"forward error: {exc}")))

    def _pump(self):
        try:
            drained = 0
            while True:
                kind, payload = self.queue.get_nowait()
                drained += 1
                if kind == "msg":
                    self._render_message(payload)
                elif kind == "log":
                    tag, text = payload
                    self._render_log(tag, text)
                elif kind == "status":
                    self.status.configure(text=f"{payload} messages")
                elif kind == "stopped":
                    self._render_stopped()
                if drained > 500:
                    break
        except Empty:
            pass
        except tk.TclError:
            return
        try:
            if self.winfo_exists():
                self.after(80, self._pump)
        except tk.TclError:
            pass

    def _render_message(self, message):
        author = message.get("author") or "unknown"
        content = message.get("content") or "(empty)"
        date = message.get("date") or ""
        time = message.get("time") or ""
        stamp = f"{date} {time}".strip()

        self._count += 1
        self.count_lbl.configure(text=f"{self._count} messages")

        self.text.configure(state="normal")
        if stamp:
            self.text.insert("end", f"{stamp} ", "time")
        self.text.insert("end", f"{author}: ", "author")
        self.text.insert("end", f"{content}\n", "content")

        for r in message.get("replies") or []:
            if r.get("deleted"):
                self.text.insert(
                    "end", f"    ↪ msg {r.get('ref_id')} [DELETED]\n", "system"
                )
            else:
                self.text.insert(
                    "end",
                    f"    ↪ {r.get('author', 'unknown')}: {r.get('content', '')}\n",
                    "system",
                )

        self.text.configure(state="disabled")
        self.text.see("end")

    def _render_log(self, tag, text):
        self.text.configure(state="normal")
        self.text.insert("end", f"{text}\n", tag)
        self.text.configure(state="disabled")
        self.text.see("end")

    def _render_stopped(self):
        try:
            self.status.configure(text="stopped")
            self.stop_btn.configure(state="disabled")
        except tk.TclError:
            pass

    def _on_stop(self):
        if self.logger is not None:
            try:
                self.logger.stop()
            except Exception:
                pass

    def _on_close(self):
        if self.logger is not None:
            try:
                self.logger.stop()
            except Exception:
                pass
        try:
            self.destroy()
        except tk.TclError:
            pass
