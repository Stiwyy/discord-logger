import tkinter as tk

from .theme import (
    ACCENT,
    ACCENT_ACTIVE,
    ACCENT_HOVER,
    BG,
    BG_CARD,
    BG_HOVER,
    BG_INPUT,
    BG_SELECTED,
    BORDER,
    TEXT,
    TEXT_FAINT,
    TEXT_MUTED,
    font,
)


def round_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    r = radius
    points = (
        x1 + r,
        y1,
        x2 - r,
        y1,
        x2,
        y1,
        x2,
        y1 + r,
        x2,
        y2 - r,
        x2,
        y2,
        x2 - r,
        y2,
        x1 + r,
        y2,
        x1,
        y2,
        x1,
        y2 - r,
        x1,
        y1 + r,
        x1,
        y1,
    )
    return canvas.create_polygon(points, smooth=True, **kwargs)


def center_window(window, width: int, height: int) -> None:
    window.update_idletasks()
    x = (window.winfo_screenwidth() - width) // 2
    y = max(0, (window.winfo_screenheight() - height) // 3)
    window.geometry(f"{width}x{height}+{x}+{y}")


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        master,
        text: str,
        command=None,
        width: int = 180,
        height: int = 40,
        canvas_bg: str = BG,
        fill: str = ACCENT,
        hover_fill: str = ACCENT_HOVER,
        active_fill: str = ACCENT_ACTIVE,
        fg: str = "#ffffff",
        text_font=None,
        state: str = "normal",
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            bg=canvas_bg,
            highlightthickness=0,
            bd=0,
        )
        self._command = command
        self._text = text
        self._fills = {
            "normal": fill,
            "hover": hover_fill,
            "active": active_fill,
            "disabled": BG_SELECTED,
        }
        self._fg = fg
        self._font = text_font or font(11, "bold")
        self._state = state
        self._current = "normal"
        self.bind("<Enter>", lambda _e: self._set("hover"))
        self.bind("<Leave>", lambda _e: self._set("normal"))
        self.bind("<Button-1>", self._click)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w, h = int(self.cget("width")), int(self.cget("height"))
        if self._state == "disabled":
            fill, fg = self._fills["disabled"], TEXT_FAINT
        else:
            fill, fg = self._fills[self._current], self._fg
        round_rect(self, 1, 1, w - 1, h - 1, min(10, h // 2 - 1), fill=fill)
        self.create_text(w / 2, h / 2, text=self._text, fill=fg, font=self._font)

    def _set(self, which: str) -> None:
        if self._state == "disabled":
            return
        self._current = which
        self._draw()

    def _click(self, _event) -> None:
        if self._state == "disabled":
            return
        if self._command:
            self._command()

    def set_state(self, state: str) -> None:
        self._state = state
        self._draw()

    def set_text(self, text: str) -> None:
        self._text = text
        self._draw()


class ModernEntry(tk.Frame):
    def __init__(
        self,
        master,
        width: int = 360,
        height: int = 44,
        placeholder: str = "",
        secret: bool = False,
        canvas_bg: str = BG_CARD,
    ):
        super().__init__(master, bg=canvas_bg)
        self._placeholder = placeholder
        self._secret = secret
        self._hidden = secret
        self._showing_placeholder = False

        self._canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=canvas_bg,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.pack()
        round_rect(
            self._canvas,
            1,
            1,
            width - 1,
            height - 1,
            10,
            fill=BG_INPUT,
            outline=BORDER,
        )

        entry_width = width - 28 - (64 if secret else 0)
        self._entry = tk.Entry(
            self._canvas,
            relief="flat",
            bd=0,
            bg=BG_INPUT,
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground=ACCENT,
            font=font(11),
        )
        self._entry.place(x=14, y=height / 2, anchor="w", width=entry_width)
        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)

        if secret:
            self._toggle = tk.Label(
                self._canvas,
                text="SHOW",
                bg=BG_INPUT,
                fg=ACCENT,
                font=font(9, "bold"),
                cursor="hand2",
            )
            self._toggle.place(x=width - 14, y=height / 2, anchor="e")
            self._toggle.bind("<Button-1>", self._toggle_secret)
            self._toggle.bind("<Enter>", lambda _e: self._toggle.configure(fg=TEXT))
            self._toggle.bind("<Leave>", lambda _e: self._toggle.configure(fg=ACCENT))

        self._set_placeholder()

    def _set_placeholder(self) -> None:
        if self._placeholder:
            self._showing_placeholder = True
            self._entry.configure(fg=TEXT_FAINT, show="")
            self._entry.delete(0, "end")
            self._entry.insert(0, self._placeholder)

    def _clear_placeholder(self) -> None:
        if self._showing_placeholder:
            self._showing_placeholder = False
            self._entry.delete(0, "end")
            self._entry.configure(
                fg=TEXT, show="•" if (self._secret and self._hidden) else ""
            )

    def _on_focus_in(self, _event) -> None:
        self._clear_placeholder()

    def _on_focus_out(self, _event) -> None:
        if not self._entry.get():
            self._set_placeholder()

    def _toggle_secret(self, _event) -> None:
        self._hidden = not self._hidden
        self._toggle.configure(text="HIDE" if not self._hidden else "SHOW")
        if not self._showing_placeholder:
            self._entry.configure(show="" if not self._hidden else "•")

    def get(self) -> str:
        if self._showing_placeholder:
            return ""
        return self._entry.get().strip()

    def bind_return(self, callback) -> None:
        self._entry.bind("<Return>", lambda _e: callback())

    def focus(self) -> None:
        self._entry.focus_set()


class ScrollableFrame(tk.Frame):
    def __init__(self, master, bg: str = BG_CARD, **kwargs):
        super().__init__(master, bg=bg, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_inner_configure(self, _event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)

    def _bind_wheel(self, _event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.canvas.bind_all("<Button-4>", self._on_wheel_up)
        self.canvas.bind_all("<Button-5>", self._on_wheel_down)

    def _unbind_wheel(self, _event) -> None:
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_wheel(self, event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_wheel_up(self, _event) -> None:
        self.canvas.yview_scroll(-1, "units")

    def _on_wheel_down(self, _event) -> None:
        self.canvas.yview_scroll(1, "units")

    def clear(self) -> None:
        for child in self.inner.winfo_children():
            child.destroy()


class ListItem(tk.Frame):
    def __init__(
        self,
        master,
        title: str,
        subtitle: str = None,
        on_select=None,
        bg: str = BG_CARD,
    ):
        super().__init__(master, bg=bg, cursor="hand2")
        self._on_select = on_select
        self._bg_default = bg
        self._selected = False
        self._hover = False

        self._bar = tk.Frame(self, width=3, bg=bg)
        self._bar.pack(side="left", fill="y")

        text_col = tk.Frame(self, bg=bg)
        text_col.pack(side="left", fill="both", expand=True, padx=(10, 8), pady=5)
        self._text_col = text_col

        self._title = tk.Label(
            text_col,
            text=title,
            bg=bg,
            fg=TEXT,
            font=font(11),
            anchor="w",
            justify="left",
        )
        self._title.pack(fill="x")

        self._subtitle_label = None
        if subtitle:
            self._subtitle_label = tk.Label(
                text_col,
                text=subtitle,
                bg=bg,
                fg=TEXT_MUTED,
                font=font(9),
                anchor="w",
            )
            self._subtitle_label.pack(fill="x")

        widgets = [self, self._bar, text_col, self._title, self._subtitle_label]
        for widget in widgets:
            if widget is None:
                continue
            widget.bind("<Button-1>", self._clicked)
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)

    def _clicked(self, _event) -> None:
        if self._on_select:
            self._on_select(self)

    def _enter(self, _event) -> None:
        self._hover = True
        if not self._selected:
            self._recolor(BG_HOVER)

    def _leave(self, _event) -> None:
        self._hover = False
        if not self._selected:
            self._recolor(self._bg_default)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        if selected:
            self._recolor(BG_SELECTED)
            self._bar.configure(bg=ACCENT)
        else:
            self._recolor(self._bg_default)
            self._bar.configure(bg=self._bg_default)

    def _recolor(self, color: str) -> None:
        for widget in (
            self,
            self._bar,
            self._text_col,
            self._title,
            self._subtitle_label,
        ):
            if widget is not None:
                widget.configure(bg=color)
