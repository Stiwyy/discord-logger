import tkinter as tk

from .theme import (
    ACCENT,
    BG,
    DANGER,
    TEXT,
    TEXT_FAINT,
    TEXT_MUTED,
    font,
)
from .widgets import ModernEntry, RoundedButton, center_window, round_rect


class TokenDialog(tk.Toplevel):
    def __init__(self, master, error: str = None):
        super().__init__(master)
        self.title("Discord Logger")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.result = None

        container = tk.Frame(self, bg=BG, padx=48, pady=36)
        container.pack(fill="both", expand=True)

        logo_size = 56
        logo = tk.Canvas(
            container,
            width=logo_size,
            height=logo_size,
            bg=BG,
            highlightthickness=0,
        )
        round_rect(logo, 0, 0, logo_size, logo_size, 16, fill=ACCENT)
        logo.create_text(
            logo_size / 2,
            logo_size / 2,
            text="DL",
            fill="#ffffff",
            font=font(20, "bold"),
        )
        logo.pack()

        tk.Label(
            container,
            text="Discord Logger",
            bg=BG,
            fg=TEXT,
            font=font(18, "bold"),
        ).pack(pady=(16, 4))
        tk.Label(
            container,
            text="Paste your token below to get started",
            bg=BG,
            fg=TEXT_MUTED,
            font=font(11),
        ).pack()

        tk.Label(
            container,
            text="TOKEN",
            bg=BG,
            fg=TEXT_MUTED,
            font=font(9, "bold"),
        ).pack(anchor="w", pady=(28, 6))

        self._entry = ModernEntry(
            container,
            width=440,
            height=46,
            placeholder="Enter your Discord token",
            secret=True,
            canvas_bg=BG,
        )
        self._entry.pack()
        self._entry.bind_return(self._submit)

        self._status = tk.Label(
            container,
            text=error or "",
            bg=BG,
            fg=DANGER,
            font=font(10),
            wraplength=440,
            justify="left",
        )
        if error:
            self._status.pack(fill="x", pady=(10, 0))

        RoundedButton(
            container,
            text="Continue",
            command=self._submit,
            width=440,
            height=44,
            canvas_bg=BG,
        ).pack(pady=(24, 0))

        tk.Label(
            container,
            text="Your token is saved locally in .env and only ever sent to discord.com.",
            bg=BG,
            fg=TEXT_FAINT,
            font=font(9),
            wraplength=440,
        ).pack(pady=(18, 0))

        self.bind("<Escape>", lambda _e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        center_window(self, 560, 460)
        self._entry.focus()

    def _submit(self) -> None:
        token = self._entry.get()
        if not token:
            self._show_error("Please enter a token.")
            return
        self.result = token
        self.destroy()

    def _show_error(self, message: str) -> None:
        self._status.configure(text=message)
        if not self._status.winfo_ismapped():
            self._status.pack(fill="x", pady=(10, 0))

    def _cancel(self) -> None:
        self.result = None
        self.destroy()

    def show(self):
        # The application root is intentionally withdrawn; making this dialog
        # transient to it can keep the dialog hidden under Wayland compositors.
        self.grab_set()
        self.wait_window()
        return self.result
