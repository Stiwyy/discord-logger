import tkinter as tk
from tkinter import simpledialog, messagebox
from urllib.parse import urlparse
from typing import Dict, List, Optional

from discord_logger import config

from .theme import (
    ACCENT,
    BG,
    BG_CARD,
    BG_ELEVATED,
    BG_SELECTED,
    DANGER,
    TEXT,
    TEXT_FAINT,
    TEXT_MUTED,
    font,
)
from .widgets import (
    ListItem,
    ModernEntry,
    RoundedButton,
    ScrollableFrame,
    center_window,
    round_rect,
)

MODES = ("Servers", "Direct Messages")


def _dm_name(channel: Dict) -> str:
    return channel.get("name") or ", ".join(
        r["username"] for r in channel.get("recipients", [])
    )


class PickerWindow(tk.Toplevel):
    def __init__(self, master, runner, client, user: Dict):
        super().__init__(master)
        self.title("Discord Logger — Select a target")
        self.configure(bg=BG)
        self.runner = runner
        self.client = client
        self.user = user
        self.result: Optional[Dict] = None

        self._mode = MODES[0]
        self._load_gen = 0
        self._left_items = []
        self._channel_items = []
        self._selected_guild: Optional[Dict] = None
        self._selected_channel: Optional[Dict] = None

        self._build()
        center_window(self, 920, 600)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._load_left()

    def _build(self) -> None:
        self._build_header()

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=BG_CARD, width=300)
        left.pack(side="left", fill="y", padx=(12, 6), pady=12)
        left.pack_propagate(False)

        seg = tk.Frame(left, bg=BG_CARD)
        seg.pack(fill="x", padx=10, pady=(10, 6))
        self._mode_labels = {}
        for mode in MODES:
            lbl = tk.Label(
                seg,
                text=mode,
                bg=BG_SELECTED if mode == self._mode else BG_CARD,
                fg=TEXT if mode == self._mode else TEXT_MUTED,
                font=font(10, "bold"),
                padx=8,
                pady=6,
                cursor="hand2",
            )
            lbl.pack(side="left", fill="x", expand=True)
            lbl.bind("<Button-1>", lambda _e, m=mode: self._set_mode(m))
            self._mode_labels[mode] = lbl

        self._search = ModernEntry(
            left,
            width=270,
            height=32,
            placeholder="Search",
            canvas_bg=BG_CARD,
        )
        self._search.pack(padx=10, pady=(0, 6))
        self._entry_inner = self._search._entry
        self._entry_inner.bind("<KeyRelease>", self._filter_left)

        self._left_list = ScrollableFrame(left, bg=BG_CARD, height=430)
        self._left_list.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(6, 12), pady=12)

        right_card = tk.Frame(right, bg=BG_CARD)
        right_card.pack(fill="both", expand=True)

        self._right_title = tk.Label(
            right_card,
            text="Select a server to see its channels",
            bg=BG_CARD,
            fg=TEXT_MUTED,
            font=font(11, "bold"),
            anchor="w",
        )
        self._right_title.pack(fill="x", padx=16, pady=(16, 8))

        self._right_list = ScrollableFrame(right_card, bg=BG_CARD)
        self._right_list.pack(fill="both", expand=True, padx=6)

        bottom = tk.Frame(right_card, bg=BG_CARD, padx=16, pady=14)
        bottom.pack(fill="x")
        self._start_btn = RoundedButton(
            bottom,
            text="Start logging",
            command=self._start,
            width=180,
            state="disabled",
            canvas_bg=BG_CARD,
        )
        self._start_btn.pack(side="right")

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=BG_ELEVATED, padx=20, pady=14)
        header.pack(fill="x")

        self._avatar = tk.Canvas(
            header,
            width=40,
            height=40,
            bg=BG_ELEVATED,
            highlightthickness=0,
        )
        round_rect(self._avatar, 0, 0, 40, 40, 20, fill=ACCENT)
        initial = (self.user.get("username") or "?")[:1].upper()
        self._avatar.create_text(
            20,
            20,
            text=initial,
            fill="#ffffff",
            font=font(15, "bold"),
        )
        self._avatar.pack(side="left")

        name_col = tk.Frame(header, bg=BG_ELEVATED)
        name_col.pack(side="left", padx=12)
        tk.Label(
            name_col,
            text=self.user.get("username", "unknown"),
            bg=BG_ELEVATED,
            fg=TEXT,
            font=font(13, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            name_col,
            text="Connected to Discord",
            bg=BG_ELEVATED,
            fg=TEXT_MUTED,
            font=font(9),
            anchor="w",
        ).pack(fill="x")

        RoundedButton(
            header,
            text="Add webhook",
            command=self._add_webhook,
            width=130,
            height=32,
            canvas_bg=BG_ELEVATED,
            fill=BG_CARD,
            hover_fill=BG_SELECTED,
            active_fill=BG_SELECTED,
            text_font=font(10, "bold"),
        ).pack(side="right", padx=(0, 8))

        RoundedButton(
            header,
            text="Switch token",
            command=self._logout,
            width=130,
            height=32,
            canvas_bg=BG_ELEVATED,
            fill=BG_CARD,
            hover_fill=BG_SELECTED,
            active_fill=BG_SELECTED,
            text_font=font(10, "bold"),
        ).pack(side="right")

        avatar_hash = self.user.get("avatar")
        if avatar_hash:
            url = (
                f"https://cdn.discordapp.com/avatars/"
                f"{self.user['id']}/{avatar_hash}.png?size=64"
            )
            self.runner.run_bg(
                self.client.get_bytes(url),
                on_success=self._set_avatar,
                on_error=lambda _e: None,
                widget=self,
            )

    def _add_webhook(self) -> None:
        url = simpledialog.askstring(
            "Uptime webhook", "Discord webhook URL:", parent=self
        )
        if url is None:
            return
        url = url.strip()
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "discord.com"
            or not parsed.path.startswith("/api/webhooks/")
        ):
            messagebox.showerror(
                "Invalid webhook",
                "Enter an https://discord.com/api/webhooks/... URL.",
                parent=self,
            )
            return
        config.save_webhook(url)

    def _set_avatar(self, data: bytes) -> None:
        try:
            self._avatar_img = tk.PhotoImage(data=data)
            self._avatar.create_image(20, 20, image=self._avatar_img)
        except tk.TclError:
            pass

    def _begin_load(self) -> int:
        self._load_gen += 1
        return self._load_gen

    def _show_loading(self, frame: ScrollableFrame, text: str) -> None:
        frame.clear()
        label = tk.Label(
            frame.inner,
            text=text,
            bg=frame.inner.cget("bg"),
            fg=TEXT_MUTED,
            font=font(10),
        )
        label.pack(pady=24)
        gen = self._load_gen
        state = {"dots": 0}

        def tick():
            if gen != self._load_gen:
                return
            try:
                state["dots"] = (state["dots"] + 1) % 4
                label.configure(text=text + "." * state["dots"])
            except tk.TclError:
                return
            self.after(350, tick)

        self.after(350, tick)

    def _load_error(self, gen: int, exc: Exception, where: str) -> None:
        if gen != self._load_gen:
            return
        self._right_title.configure(text=f"Error loading {where}: {exc}", fg=DANGER)

    def _load_left(self) -> None:
        gen = self._begin_load()
        self._selected_guild = None
        self._selected_channel = None
        self._start_btn.set_state("disabled")
        self._right_title.configure(
            text=(
                "Select a server to see its channels"
                if self._mode == "Servers"
                else "Select a conversation"
            ),
            fg=TEXT_MUTED,
        )
        self._right_list.clear()
        self._show_loading(self._left_list, "Connecting")

        if self._mode == "Servers":
            coro = self.client.get_user_guilds()
        else:
            coro = self.client.get_dm_channels()
        self.runner.run_bg(
            coro,
            on_success=lambda data: self._fill_left(gen, data),
            on_error=lambda exc: self._load_error(gen, exc, "conversations"),
            widget=self,
        )

    def _fill_left(self, gen: int, data: List[Dict]) -> None:
        if gen != self._load_gen:
            return
        self._left_list.clear()
        self._left_items = []
        for entry in data:
            if self._mode == "Servers":
                title, subtitle, payload = (
                    entry["name"],
                    None,
                    {"name": entry["name"], "id": entry["id"]},
                )
            else:
                title, subtitle, payload = (
                    _dm_name(entry),
                    None,
                    {"name": _dm_name(entry), "id": entry["id"]},
                )
            item = ListItem(
                self._left_list.inner,
                title=title,
                subtitle=subtitle,
                on_select=(
                    self._on_guild_clicked
                    if self._mode == "Servers"
                    else self._on_dm_clicked
                ),
                bg=BG_CARD,
            )
            item.pack(fill="x", padx=4, pady=2)
            self._left_items.append((item, title.lower(), payload))

    def _filter_left(self, _event=None) -> None:
        query = self._search.get().lower()
        for item, title, _payload in self._left_items:
            if query in title:
                if not item.winfo_ismapped():
                    item.pack(fill="x", padx=4, pady=2)
            elif item.winfo_ismapped():
                item.pack_forget()

    def _set_mode(self, mode: str) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        for name, lbl in self._mode_labels.items():
            active = name == mode
            lbl.configure(
                bg=BG_SELECTED if active else BG_CARD,
                fg=TEXT if active else TEXT_MUTED,
            )
        self._load_left()

    def _on_guild_clicked(self, item: ListItem) -> None:
        for other, _title, _payload in self._left_items:
            other.set_selected(other is item)
        self._selected_guild = next(p for it, _t, p in self._left_items if it is item)
        self._selected_channel = None
        self._start_btn.set_state("disabled")

        gen = self._begin_load()
        self._right_title.configure(
            text=f"Channels in {self._selected_guild['name']}",
            fg=TEXT,
        )
        self._show_loading(self._right_list, "Loading channels")
        self.runner.run_bg(
            self.client.get_guild_channels(self._selected_guild["id"]),
            on_success=lambda data: self._fill_channels(gen, data),
            on_error=lambda exc: self._load_error(gen, exc, "channels"),
            widget=self,
        )

    def _fill_channels(self, gen: int, channels: List[Dict]) -> None:
        if gen != self._load_gen:
            return
        self._right_list.clear()
        self._channel_items = []
        for ch in channels:
            item = ListItem(
                self._right_list.inner,
                title=f"# {ch['name']}",
                on_select=self._on_channel_clicked,
                bg=BG_CARD,
            )
            item.pack(fill="x", padx=4, pady=2)
            self._channel_items.append((item, {"name": ch["name"], "id": ch["id"]}))

    def _on_channel_clicked(self, item: ListItem) -> None:
        for other, _payload in self._channel_items:
            other.set_selected(other is item)
        self._selected_channel = next(p for it, p in self._channel_items if it is item)
        self._start_btn.set_state("normal")

    def _on_dm_clicked(self, item: ListItem) -> None:
        for other, _title, _payload in self._left_items:
            other.set_selected(other is item)
        self._selected_channel = next(p for it, _t, p in self._left_items if it is item)
        self._right_title.configure(
            text=f"Logging direct messages with {self._selected_channel['name']}",
            fg=TEXT,
        )
        self._start_btn.set_state("normal")

    def _start(self) -> None:
        if self._mode == "Servers":
            if not (self._selected_guild and self._selected_channel):
                return
            self.result = {
                "action": "log",
                "kind": "channel",
                "server": self._selected_guild["name"],
                "channel": self._selected_channel["name"],
                "channel_id": self._selected_channel["id"],
            }
        else:
            if not self._selected_channel:
                return
            self.result = {
                "action": "log",
                "kind": "dm",
                "server": "DMs",
                "channel": self._selected_channel["name"],
                "channel_id": self._selected_channel["id"],
            }
        self._begin_load()
        self.destroy()

    def _logout(self) -> None:
        self.result = {"action": "logout"}
        self._begin_load()
        self.destroy()

    def _close(self) -> None:
        self.result = None
        self._begin_load()
        self.destroy()

    def show(self):
        self.wait_window()
        return self.result
