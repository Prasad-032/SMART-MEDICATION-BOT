import json
import os
import hashlib
import threading
import time
from datetime import datetime

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.animation import Animation
from kivy.uix.widget import Widget

Window.size = (400, 720)
Window.clearcolor = (0.96, 0.96, 0.98, 1)

# Register MaterialIcons font for icon buttons
_ICONS_FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MaterialIcons.ttf")
if os.path.exists(_ICONS_FONT):
    LabelBase.register("Icons", _ICONS_FONT)

# MaterialIcons codepoints (used with font_name="Icons")
ICO_PILL     = "\ue549"   # medication
ICO_ADD      = "\ue145"   # add
ICO_LOGOUT   = "\ue9ba"   # logout
ICO_HISTORY  = "\ue889"   # history
ICO_DELETE   = "\ue872"   # delete
ICO_BACK     = "\ue5c4"   # arrow_back
ICO_ALARM    = "\ue855"   # alarm
ICO_CHECK    = "\ue876"   # check
ICO_PERSON   = "\ue7fd"   # person
ICO_LOCK     = "\ue897"   # lock

# ── Palette ──────────────────────────────────────────────────────────────────
C_BG        = (0.96, 0.96, 0.98, 1)
C_SURFACE   = (1,    1,    1,    1)
C_PRIMARY   = (0.27, 0.45, 0.98, 1)   # indigo-blue
C_PRIMARY2  = (0.48, 0.30, 0.95, 1)   # purple (gradient end)
C_ACCENT    = (0.13, 0.80, 0.68, 1)   # teal
C_DANGER    = (0.95, 0.27, 0.37, 1)
C_WARN      = (1.00, 0.65, 0.10, 1)
C_SUCCESS   = (0.13, 0.80, 0.50, 1)
C_TEXT      = (0.12, 0.12, 0.18, 1)
C_SUBTEXT   = (0.50, 0.50, 0.60, 1)
C_WHITE     = (1,    1,    1,    1)

LOG_FILE   = "confirmation_logs.json"
USERS_FILE = "users.json"

state = {
    "user": None, "medicines": [],
    "confirmed_today": set(), "last_reset": datetime.now().date(),
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def init_file(f, d):
    if not os.path.exists(f) or os.path.getsize(f) == 0:
        with open(f, "w") as fp: json.dump(d, fp)

def load_json(f):
    init_file(f, [])
    try:
        with open(f) as fp: return json.load(fp)
    except: return []

def save_json(f, d):
    with open(f, "w") as fp: json.dump(d, fp, indent=2)

def med_file(u): return f"medicines_{u}.json"
def load_meds(u): return load_json(med_file(u))
def save_meds(u, m): save_json(med_file(u), m)
def get_seconds(v, u): return int(v) * {"Seconds":1,"Minutes":60,"Hours":3600}.get(u,60)

def time_left_str(end_str):
    try:
        now = datetime.now()
        e = datetime.strptime(end_str, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
        mins = int((e - now).total_seconds() // 60)
        if mins > 60: return f"{mins//60}h {mins%60}m left"
        if mins > 0:  return f"{mins}m left"
        return "Time Over"
    except: return ""

# ── Drawing helpers ───────────────────────────────────────────────────────────
def draw_rounded_bg(widget, color, radius=dp(16)):
    widget.canvas.before.clear()
    with widget.canvas.before:
        Color(*color)
        widget._bg = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
    widget.bind(pos=lambda w,v: setattr(w._bg,'pos',v),
                size=lambda w,v: setattr(w._bg,'size',v))

def draw_rect_bg(widget, color):
    widget.canvas.before.clear()
    with widget.canvas.before:
        Color(*color)
        widget._bg = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda w,v: setattr(w._bg,'pos',v),
                size=lambda w,v: setattr(w._bg,'size',v))

# ── Reusable widgets ──────────────────────────────────────────────────────────
def flat_btn(text, bg=C_PRIMARY, fg=C_WHITE, h=dp(50), radius=dp(14), fs=dp(15), **kw):
    b = Button(text=text, background_normal="", background_color=bg,
               color=fg, size_hint_y=None, height=h, font_size=fs,
               bold=True, **kw)
    draw_rounded_bg(b, bg, radius)
    b.bind(background_color=lambda w,v: draw_rounded_bg(w, v, radius))
    return b

def styled_input(hint, password=False):
    ti = TextInput(hint_text=hint, password=password, multiline=False,
                   size_hint_y=None, height=dp(50), font_size=dp(14),
                   padding=[dp(16), dp(14)], foreground_color=C_TEXT,
                   hint_text_color=C_SUBTEXT, cursor_color=C_PRIMARY,
                   background_color=(0.93, 0.93, 0.97, 1),
                   background_normal="", background_active="")
    return ti

def section_label(text):
    return Label(text=text, font_size=dp(12), color=C_SUBTEXT, bold=True,
                 size_hint_y=None, height=dp(24), halign="left",
                 text_size=(dp(340), None))

def pill_label(text, bg, fg=C_WHITE):
    lbl = Label(text=text, font_size=dp(11), color=fg, bold=True,
                size_hint=(None, None), size=(dp(90), dp(24)))
    draw_rounded_bg(lbl, bg, dp(12))
    return lbl

# ── Auth Screen ───────────────────────────────────────────────────────────────
class AuthScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = FloatLayout()

        # Gradient header panel
        header = Widget(size_hint=(1, None), height=dp(260),
                        pos_hint={"top": 1})
        with header.canvas:
            Color(*C_PRIMARY)
            header._r1 = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda w,v: setattr(w._r1,'pos',v),
                    size=lambda w,v: setattr(w._r1,'size',v))
        root.add_widget(header)

        # Logo + tagline
        logo = Label(text=ICO_PILL, font_name="Icons", font_size=dp(56),
                     size_hint=(None, None), size=(dp(80), dp(80)),
                     pos_hint={"center_x": 0.5, "top": 0.97})
        title = Label(text="MedReminder", font_size=dp(28), bold=True,
                      color=C_WHITE, size_hint=(None, None),
                      size=(dp(300), dp(40)),
                      pos_hint={"center_x": 0.5, "top": 0.85})
        sub = Label(text="Never miss a dose again", font_size=dp(13),
                    color=(0.85, 0.85, 1, 1), size_hint=(None, None),
                    size=(dp(300), dp(28)),
                    pos_hint={"center_x": 0.5, "top": 0.76})
        root.add_widget(logo)
        root.add_widget(title)
        root.add_widget(sub)

        # Card
        card = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(14),
                         size_hint=(0.9, None), height=dp(400),
                         pos_hint={"center_x": 0.5, "y": 0.02})
        draw_rounded_bg(card, C_SURFACE, dp(20))

        # Tab row
        tab_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(0))
        draw_rounded_bg(tab_row, (0.91, 0.91, 0.95, 1), dp(12))
        self._tab_login = Button(text="Login", background_normal="",
                                  background_color=(0,0,0,0), color=C_SUBTEXT,
                                  font_size=dp(14), bold=True)
        self._tab_reg   = Button(text="Register", background_normal="",
                                  background_color=(0,0,0,0), color=C_SUBTEXT,
                                  font_size=dp(14), bold=True)
        self._tab_login.bind(on_press=lambda x: self._switch("login"))
        self._tab_reg.bind(on_press=lambda x: self._switch("register"))
        tab_row.add_widget(self._tab_login)
        tab_row.add_widget(self._tab_reg)
        card.add_widget(tab_row)

        self.user_in = styled_input("Username")
        self.pass_in = styled_input("Password", password=True)
        card.add_widget(self.user_in)
        card.add_widget(self.pass_in)

        self.action_btn = flat_btn("Login")
        self.action_btn.bind(on_press=self._do_action)
        card.add_widget(self.action_btn)

        self.msg = Label(text="", font_size=dp(13), color=C_DANGER,
                         size_hint_y=None, height=dp(28))
        card.add_widget(self.msg)
        root.add_widget(card)
        self.add_widget(root)
        self._mode = "login"
        self._switch("login")

    def _switch(self, mode):
        self._mode = mode
        self.action_btn.text = "Login" if mode == "login" else "Create Account"
        self.msg.text = ""
        if mode == "login":
            draw_rounded_bg(self._tab_login, C_PRIMARY, dp(12))
            self._tab_login.color = C_WHITE
            draw_rounded_bg(self._tab_reg, (0,0,0,0), dp(12))
            self._tab_reg.color = C_SUBTEXT
        else:
            draw_rounded_bg(self._tab_reg, C_PRIMARY, dp(12))
            self._tab_reg.color = C_WHITE
            draw_rounded_bg(self._tab_login, (0,0,0,0), dp(12))
            self._tab_login.color = C_SUBTEXT

    def _do_action(self, *_):
        u = self.user_in.text.strip()
        p = self.pass_in.text.strip()
        if not u or not p:
            self.msg.text = "⚠  Please fill in both fields."
            return
        if self._mode == "login":
            users = load_json(USERS_FILE)
            for usr in users:
                if usr["username"] == u and usr["password"] == hash_password(p):
                    state["user"] = usr
                    state["medicines"] = load_meds(u)
                    state["confirmed_today"] = set()
                    self.user_in.text = self.pass_in.text = self.msg.text = ""
                    self.manager.transition = SlideTransition(direction="left")
                    self.manager.current = "home"
                    return
            self.msg.text = "✗  Invalid username or password."
        else:
            users = load_json(USERS_FILE)
            if any(x["username"] == u for x in users):
                self.msg.text = "✗  Username already taken."
                return
            users.append({"username": u, "password": hash_password(p)})
            save_json(USERS_FILE, users)
            self.msg.text = "✓  Account created! Please login."
            self._switch("login")

# ── Home Screen ───────────────────────────────────────────────────────────────
class HomeScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        self._selected = set()
        root = FloatLayout()
        draw_rect_bg(root, C_BG)

        # ── Top bar ──
        bar = BoxLayout(size_hint=(1, None), height=dp(70),
                        padding=[dp(20), dp(10)], spacing=dp(8),
                        pos_hint={"top": 1})
        with bar.canvas.before:
            Color(*C_PRIMARY)
            bar._bg = RoundedRectangle(pos=bar.pos, size=bar.size,
                                       radius=[0, 0, dp(20), dp(20)])
        bar.bind(pos=lambda w,v: setattr(w._bg,'pos',v),
                 size=lambda w,v: setattr(w._bg,'size',v))

        uname = state["user"]["username"] if state["user"] else ""
        bar.add_widget(Label(text=f"Hello, [b]{uname}[/b]", markup=True,
                             font_size=dp(16), color=C_WHITE, halign="left",
                             text_size=(dp(200), None)))
        logs_btn = Button(text=ICO_HISTORY, font_name="Icons",
                          background_normal="", background_color=(0,0,0,0),
                          color=C_WHITE, font_size=dp(24),
                          size_hint=(None, 1), width=dp(44))
        logs_btn.bind(on_press=lambda x: self._go("logs"))
        logout_btn = Button(text=ICO_LOGOUT, font_name="Icons",
                            background_normal="", background_color=(0,0,0,0),
                            color=C_WHITE, font_size=dp(24),
                            size_hint=(None, 1), width=dp(44))
        logout_btn.bind(on_press=self._logout)
        bar.add_widget(logs_btn)
        bar.add_widget(logout_btn)
        root.add_widget(bar)

        # ── Stats strip ──
        total = len(state["medicines"])
        done  = sum(1 for m in state["medicines"] if m.get("confirmed"))
        stats = BoxLayout(size_hint=(1, None), height=dp(72),
                          padding=[dp(16), dp(8)], spacing=dp(10),
                          pos_hint={"top": 0.865})
        for label, val, color in [
            ("Total", str(total), C_PRIMARY),
            ("Done", str(done), C_SUCCESS),
            ("Pending", str(total - done), C_WARN),
        ]:
            tile = BoxLayout(orientation="vertical", padding=dp(6))
            draw_rounded_bg(tile, C_SURFACE, dp(12))
            tile.add_widget(Label(text=str(val), font_size=dp(20), bold=True,
                                  color=color, size_hint_y=None, height=dp(28)))
            tile.add_widget(Label(text=label, font_size=dp(11), color=C_SUBTEXT,
                                  size_hint_y=None, height=dp(18)))
            stats.add_widget(tile)
        root.add_widget(stats)

        # ── Scrollable med list ──
        scroll = ScrollView(size_hint=(1, None),
                            pos_hint={"x": 0, "y": 0.12},
                            size=(Window.width, Window.height * 0.62))
        self._grid = GridLayout(cols=1, spacing=dp(10),
                                padding=[dp(14), dp(8), dp(14), dp(80)],
                                size_hint_y=None)
        self._grid.bind(minimum_height=self._grid.setter("height"))
        scroll.add_widget(self._grid)
        root.add_widget(scroll)

        # ── Bottom action bar ──
        bot = BoxLayout(size_hint=(1, None), height=dp(64),
                        padding=[dp(12), dp(8)], spacing=dp(8),
                        pos_hint={"x": 0, "y": 0})
        draw_rect_bg(bot, C_SURFACE)
        del_btn = flat_btn("Delete Selected", C_DANGER, h=dp(46), fs=dp(13))
        del_btn.bind(on_press=self._delete_selected)
        del_acc = flat_btn("Delete Account", (0.85, 0.85, 0.88, 1),
                           fg=C_DANGER, h=dp(46), fs=dp(12))
        del_acc.bind(on_press=self._delete_account)
        bot.add_widget(del_btn)
        bot.add_widget(del_acc)
        root.add_widget(bot)

        # FAB
        fab = Button(text=ICO_ADD, font_name="Icons", font_size=dp(28), bold=True,
                     background_normal="", background_color=C_PRIMARY,
                     color=C_WHITE, size_hint=(None, None),
                     size=(dp(60), dp(60)),
                     pos_hint={"right": 0.95, "y": 0.14})
        draw_rounded_bg(fab, C_PRIMARY, dp(30))
        fab.bind(on_press=lambda x: self._go("add"))
        root.add_widget(fab)

        self.add_widget(root)
        self._refresh()

    def _go(self, s):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = s

    def _refresh(self):
        self._grid.clear_widgets()
        if not state["medicines"]:
            empty = BoxLayout(orientation="vertical", size_hint_y=None,
                              height=dp(160), padding=dp(20))
            draw_rounded_bg(empty, C_SURFACE, dp(16))
            empty.add_widget(Label(text=ICO_PILL, font_name="Icons", font_size=dp(40),
                                   size_hint_y=None, height=dp(60), color=C_SUBTEXT))
            empty.add_widget(Label(
                text="No medicines yet\nTap  +  to add your first reminder",
                font_size=dp(14), color=C_SUBTEXT, halign="center",
                text_size=(dp(300), None)))
            self._grid.add_widget(empty)
            return
        for med in state["medicines"]:
            self._grid.add_widget(self._make_card(med))

    def _make_card(self, med):
        confirmed = med.get("confirmed", False)
        tl = time_left_str(med["end"])
        is_over = tl == "Time Over"

        card = BoxLayout(orientation="vertical", size_hint_y=None,
                         height=dp(110), padding=[dp(14), dp(10)], spacing=dp(6))

        # Card background + left accent bar
        with card.canvas.before:
            Color(*C_SURFACE)
            card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(14)])
            accent_color = C_SUCCESS if confirmed else (C_WARN if is_over else C_PRIMARY)
            Color(*accent_color)
            card._bar = RoundedRectangle(pos=card.pos, size=(dp(5), card.height),
                                          radius=[dp(4)])
        def _upd(w, *_):
            w._bg.pos  = w.pos;  w._bg.size  = w.size
            w._bar.pos = w.pos;  w._bar.size = (dp(5), w.height)
        card.bind(pos=_upd, size=_upd)

        # Row 1: name + status pill
        row1 = BoxLayout(size_hint_y=None, height=dp(32))
        name_lbl = Label(text=med["name"], font_size=dp(16), bold=True,
                         color=C_TEXT, halign="left",
                         text_size=(dp(200), None))
        status_text = "Done" if confirmed else ("Over" if is_over else "Pending")
        status_color = C_SUCCESS if confirmed else (C_DANGER if is_over else C_WARN)
        status_pill = pill_label(status_text, status_color)
        row1.add_widget(name_lbl)
        row1.add_widget(status_pill)
        card.add_widget(row1)

        # Row 2: details
        detail = Label(
            text=f"{med['meal']} meal  |  {med['start']} - {med['end']}  |  every {med['freq_value']} {med['freq_unit']}",
            font_size=dp(11), color=C_SUBTEXT, halign="left",
            text_size=(dp(340), None), size_hint_y=None, height=dp(22))
        card.add_widget(detail)

        # Row 3: time left + select toggle
        row3 = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        tl_color = C_DANGER if is_over else (C_SUCCESS if confirmed else C_PRIMARY)
        row3.add_widget(Label(text=tl, font_size=dp(12), bold=True,
                              color=tl_color, halign="left",
                              text_size=(dp(180), None)))

        name = med["name"]
        is_sel = name in self._selected
        sel = Button(text="✓ Selected" if is_sel else "Select",
                     background_normal="", font_size=dp(12),
                     background_color=C_PRIMARY if is_sel else (0.88,0.88,0.92,1),
                     color=C_WHITE if is_sel else C_SUBTEXT,
                     size_hint=(None, 1), width=dp(100))
        draw_rounded_bg(sel, C_PRIMARY if is_sel else (0.88,0.88,0.92,1), dp(10))

        def toggle(btn, n=name):
            if n in self._selected:
                self._selected.discard(n)
                btn.text = "Select"
                draw_rounded_bg(btn, (0.88,0.88,0.92,1), dp(10))
                btn.color = C_SUBTEXT
            else:
                self._selected.add(n)
                btn.text = "✓ Selected"
                draw_rounded_bg(btn, C_PRIMARY, dp(10))
                btn.color = C_WHITE
        sel.bind(on_press=toggle)
        row3.add_widget(sel)
        card.add_widget(row3)
        return card

    def _delete_selected(self, *_):
        if not self._selected:
            self._alert("Nothing selected", "Tap 'Select' on a medicine card first.")
            return
        self._confirm(f"Delete {len(self._selected)} medicine(s)?",
                      "This cannot be undone.", self._do_delete)

    def _do_delete(self, popup, *_):
        state["medicines"] = [m for m in state["medicines"]
                               if m["name"] not in self._selected]
        save_meds(state["user"]["username"], state["medicines"])
        self._selected.clear()
        popup.dismiss()
        self.on_enter()

    def _logout(self, *_):
        state.update(user=None, medicines=[], confirmed_today=set())
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "auth"

    def _delete_account(self, *_):
        self._confirm("Delete Account?",
                      "All your data will be permanently removed.",
                      self._do_delete_account)

    def _do_delete_account(self, popup, *_):
        u = state["user"]["username"]
        save_json(USERS_FILE, [x for x in load_json(USERS_FILE) if x["username"] != u])
        mf = med_file(u)
        if os.path.exists(mf): os.remove(mf)
        save_json(LOG_FILE, [l for l in load_json(LOG_FILE) if l.get("username") != u])
        state.update(user=None, medicines=[])
        popup.dismiss()
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "auth"

    def _alert(self, title, msg):
        c = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        draw_rounded_bg(c, C_SURFACE, dp(16))
        c.add_widget(Label(text=msg, font_size=dp(14), color=C_TEXT,
                           halign="center", text_size=(dp(260), None)))
        ok = flat_btn("OK", h=dp(44))
        p = Popup(title=title, content=c, size_hint=(0.82, 0.32),
                  separator_color=C_PRIMARY, title_color=C_TEXT,
                  title_size=dp(15))
        ok.bind(on_press=p.dismiss)
        c.add_widget(ok)
        p.open()

    def _confirm(self, title, msg, cb):
        c = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        draw_rounded_bg(c, C_SURFACE, dp(16))
        c.add_widget(Label(text=msg, font_size=dp(13), color=C_SUBTEXT,
                           halign="center", text_size=(dp(260), None)))
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        p = Popup(title=title, content=c, size_hint=(0.82, 0.36),
                  separator_color=C_DANGER, title_color=C_TEXT, title_size=dp(15))
        yes = flat_btn("Yes, Delete", C_DANGER, h=dp(44))
        no  = flat_btn("Cancel", (0.88,0.88,0.92,1), fg=C_TEXT, h=dp(44))
        yes.bind(on_press=lambda x: cb(p, x))
        no.bind(on_press=p.dismiss)
        row.add_widget(yes); row.add_widget(no)
        c.add_widget(row)
        p.open()

    def refresh_from_reminder(self):
        Clock.schedule_once(lambda dt: self.on_enter(), 0)

# ── Add Medicine Screen ───────────────────────────────────────────────────────
# ── Time Picker Widget ────────────────────────────────────────────────────────
class TimePicker(BoxLayout):
    """A +/- hour/minute picker with AM/PM toggle. Returns 24h HH:MM string."""

    def __init__(self, label_text="", **kw):
        super().__init__(orientation="vertical",
                         size_hint_y=None, height=dp(110),
                         spacing=dp(6), **kw)
        self._hour = 8    # 1-12
        self._minute = 0  # 0-55 step 5
        self._ampm = "AM"

        # Section label
        self.add_widget(section_label(label_text))

        # Main picker card
        card = BoxLayout(orientation="horizontal", size_hint_y=None,
                         height=dp(80), spacing=dp(6), padding=[dp(8), dp(6)])
        draw_rounded_bg(card, C_SURFACE, dp(14))

        card.add_widget(self._unit_col("hour"))
        card.add_widget(self._colon())
        card.add_widget(self._unit_col("minute"))
        card.add_widget(self._ampm_btn())
        self.add_widget(card)

    def _step_btn(self, text, callback):
        btn = Button(text=text, font_size=dp(18), bold=True,
                     background_normal="", background_color=(0,0,0,0),
                     color=C_PRIMARY, size_hint_y=None, height=dp(26))
        btn.bind(on_press=callback)
        return btn

    def _unit_col(self, unit):
        col = BoxLayout(orientation="vertical", spacing=dp(2),
                        size_hint_x=None, width=dp(72))

        up = self._step_btn("+", lambda x, u=unit: self._change(u, 1))
        if unit == "hour":
            self._hour_lbl = Label(text=self._fmt_hour(), font_size=dp(22),
                                   bold=True, color=C_TEXT,
                                   size_hint_y=None, height=dp(30))
            display = self._hour_lbl
        else:
            self._min_lbl = Label(text=self._fmt_min(), font_size=dp(22),
                                  bold=True, color=C_TEXT,
                                  size_hint_y=None, height=dp(30))
            display = self._min_lbl

        sub_lbl = Label(text="HH" if unit == "hour" else "MM",
                        font_size=dp(9), color=C_SUBTEXT,
                        size_hint_y=None, height=dp(14))
        down = self._step_btn("-", lambda x, u=unit: self._change(u, -1))

        col.add_widget(up)
        col.add_widget(display)
        col.add_widget(sub_lbl)
        col.add_widget(down)
        return col

    def _colon(self):
        return Label(text=":", font_size=dp(24), bold=True, color=C_SUBTEXT,
                     size_hint_x=None, width=dp(16))

    def _ampm_btn(self):
        col = BoxLayout(orientation="vertical", spacing=dp(4),
                        size_hint_x=None, width=dp(60), padding=[dp(4), dp(8)])
        self._am_btn = Button(text="AM", font_size=dp(13), bold=True,
                              background_normal="", color=C_WHITE,
                              background_color=C_PRIMARY,
                              size_hint_y=None, height=dp(30))
        self._pm_btn = Button(text="PM", font_size=dp(13), bold=True,
                              background_normal="", color=C_SUBTEXT,
                              background_color=(0.88, 0.88, 0.92, 1),
                              size_hint_y=None, height=dp(30))
        draw_rounded_bg(self._am_btn, C_PRIMARY, dp(8))
        draw_rounded_bg(self._pm_btn, (0.88, 0.88, 0.92, 1), dp(8))
        self._am_btn.bind(on_press=lambda x: self._set_ampm("AM"))
        self._pm_btn.bind(on_press=lambda x: self._set_ampm("PM"))
        col.add_widget(self._am_btn)
        col.add_widget(self._pm_btn)
        return col

    def _change(self, unit, direction):
        if unit == "hour":
            self._hour = (self._hour - 1 + direction) % 12 + 1
            self._hour_lbl.text = self._fmt_hour()
        else:
            self._minute = (self._minute + direction * 5) % 60
            self._min_lbl.text = self._fmt_min()

    def _set_ampm(self, val):
        self._ampm = val
        if val == "AM":
            draw_rounded_bg(self._am_btn, C_PRIMARY, dp(8))
            self._am_btn.color = C_WHITE
            draw_rounded_bg(self._pm_btn, (0.88, 0.88, 0.92, 1), dp(8))
            self._pm_btn.color = C_SUBTEXT
        else:
            draw_rounded_bg(self._pm_btn, C_PRIMARY, dp(8))
            self._pm_btn.color = C_WHITE
            draw_rounded_bg(self._am_btn, (0.88, 0.88, 0.92, 1), dp(8))
            self._am_btn.color = C_SUBTEXT

    def _fmt_hour(self): return f"{self._hour:02d}"
    def _fmt_min(self):  return f"{self._minute:02d}"

    def get_24h(self):
        """Returns HH:MM in 24-hour format."""
        h = self._hour % 12
        if self._ampm == "PM":
            h += 12
        return f"{h:02d}:{self._minute:02d}"


# ── Add Medicine Screen ───────────────────────────────────────────────────────
class AddScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        draw_rect_bg(root, C_BG)

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(64),
                        padding=[dp(16), dp(10)], spacing=dp(10))
        with hdr.canvas.before:
            Color(*C_PRIMARY)
            hdr._bg = RoundedRectangle(pos=hdr.pos, size=hdr.size,
                                       radius=[0, 0, dp(20), dp(20)])
        hdr.bind(pos=lambda w,v: setattr(w._bg,'pos',v),
                 size=lambda w,v: setattr(w._bg,'size',v))
        back = Button(text=ICO_BACK, font_name="Icons",
                      background_normal="", background_color=(0,0,0,0),
                      color=C_WHITE, font_size=dp(24),
                      size_hint=(None, 1), width=dp(44))
        back.bind(on_press=self._back)
        hdr.add_widget(back)
        hdr.add_widget(Label(text="Add Medicine", font_size=dp(18), bold=True,
                             color=C_WHITE))
        root.add_widget(hdr)

        # Scrollable form
        scroll = ScrollView()
        form = GridLayout(cols=1, spacing=dp(10),
                          padding=[dp(20), dp(16), dp(20), dp(20)],
                          size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        def field(label, widget):
            form.add_widget(section_label(label))
            form.add_widget(widget)

        self.name_in = styled_input("e.g. Paracetamol 500mg")
        self.meal_sp = self._spinner(["After Meal", "Before Meal"])
        self.freq_in = styled_input("e.g. 30")
        self.unit_sp = self._spinner(["Minutes", "Seconds", "Hours"])

        # Time pickers
        self.start_picker = TimePicker()
        self.end_picker   = TimePicker()
        # default end to 9 AM
        self.end_picker._hour = 9

        field("MEDICINE NAME", self.name_in)
        field("MEAL TIMING", self.meal_sp)

        form.add_widget(self.start_picker)
        form.add_widget(Label(size_hint_y=None, height=dp(2)))  # spacer
        form.add_widget(self.end_picker)

        field("REMIND EVERY", self.freq_in)
        field("UNIT", self.unit_sp)

        # Rebuild pickers with labels now that we know the text
        form.remove_widget(self.start_picker)
        form.remove_widget(self.end_picker)
        self.start_picker = TimePicker(label_text="START TIME")
        self.end_picker   = TimePicker(label_text="END TIME")
        self.end_picker._hour = 9

        # Re-insert in correct order
        # Clear and rebuild form cleanly
        form.clear_widgets()
        form.add_widget(section_label("MEDICINE NAME")); form.add_widget(self.name_in)
        form.add_widget(section_label("MEAL TIMING"));   form.add_widget(self.meal_sp)
        form.add_widget(self.start_picker)
        form.add_widget(self.end_picker)
        form.add_widget(section_label("REMIND EVERY"));  form.add_widget(self.freq_in)
        form.add_widget(section_label("UNIT"));          form.add_widget(self.unit_sp)

        self.msg = Label(text="", font_size=dp(13), color=C_DANGER,
                         size_hint_y=None, height=dp(30), halign="center",
                         text_size=(dp(340), None))
        form.add_widget(self.msg)

        save_btn = flat_btn("Save Reminder", C_PRIMARY, h=dp(52), fs=dp(16))
        save_btn.bind(on_press=self._save)
        form.add_widget(save_btn)
        scroll.add_widget(form)
        root.add_widget(scroll)
        self.add_widget(root)

    def _spinner(self, values):
        sp = Spinner(text=values[0], values=values,
                     background_normal="", background_color=(0.93,0.93,0.97,1),
                     color=C_TEXT, font_size=dp(14),
                     size_hint_y=None, height=dp(50))
        return sp

    def _save(self, *_):
        name  = self.name_in.text.strip()
        meal  = self.meal_sp.text.split()[0]
        start = self.start_picker.get_24h()
        end   = self.end_picker.get_24h()
        freq  = self.freq_in.text.strip()
        unit  = self.unit_sp.text

        if not name:
            self.msg.text = "Medicine name is required."; return
        try:
            fval = int(freq)
            assert fval > 0
        except:
            self.msg.text = "Frequency must be a positive number."; return
        if any(m["name"] == name for m in state["medicines"]):
            self.msg.text = "Medicine already exists."; return

        state["medicines"].append({
            "name": name, "meal": meal, "start": start, "end": end,
            "confirmed": False, "last_notified_time": None,
            "freq_value": fval, "freq_unit": unit
        })
        save_meds(state["user"]["username"], state["medicines"])
        self.name_in.text = self.freq_in.text = self.msg.text = ""
        self._back()

    def _back(self, *_):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "home"
        self.manager.get_screen("home").on_enter()

# ── Logs Screen ───────────────────────────────────────────────────────────────
class LogsScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        root = BoxLayout(orientation="vertical")
        draw_rect_bg(root, C_BG)

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(64),
                        padding=[dp(16), dp(10)], spacing=dp(10))
        with hdr.canvas.before:
            Color(*C_PRIMARY)
            hdr._bg = RoundedRectangle(pos=hdr.pos, size=hdr.size,
                                       radius=[0, 0, dp(20), dp(20)])
        hdr.bind(pos=lambda w,v: setattr(w._bg,'pos',v),
                 size=lambda w,v: setattr(w._bg,'size',v))
        back = Button(text=ICO_BACK, font_name="Icons",
                      background_normal="", background_color=(0,0,0,0),
                      color=C_WHITE, font_size=dp(24),
                      size_hint=(None, 1), width=dp(44))
        back.bind(on_press=lambda x: self._back())
        hdr.add_widget(back)
        hdr.add_widget(Label(text="History", font_size=dp(18), bold=True,
                             color=C_WHITE))
        root.add_widget(hdr)

        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=dp(8),
                          padding=[dp(14), dp(12), dp(14), dp(20)],
                          size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))

        uname = state["user"]["username"] if state["user"] else ""
        logs = [l for l in load_json(LOG_FILE) if l.get("username") == uname]

        if not logs:
            empty = BoxLayout(orientation="vertical", size_hint_y=None,
                              height=dp(140), padding=dp(20))
            draw_rounded_bg(empty, C_SURFACE, dp(16))
            empty.add_widget(Label(text=ICO_HISTORY, font_name="Icons", font_size=dp(36),
                                   color=C_SUBTEXT, size_hint_y=None, height=dp(50)))
            empty.add_widget(Label(text="No history yet",
                                   font_size=dp(14), color=C_SUBTEXT,
                                   halign="center", text_size=(dp(300), None)))
            grid.add_widget(empty)
        else:
            for log in reversed(logs):
                row = BoxLayout(size_hint_y=None, height=dp(64),
                                padding=[dp(14), dp(8)], spacing=dp(12))
                draw_rounded_bg(row, C_SURFACE, dp(12))

                dot = Widget(size_hint=(None, None), size=(dp(10), dp(10)))
                with dot.canvas:
                    Color(*C_SUCCESS)
                    dot._c = RoundedRectangle(pos=dot.pos, size=dot.size, radius=[dp(5)])
                dot.bind(pos=lambda w,v: setattr(w._c,'pos',v))

                info = BoxLayout(orientation="vertical")
                info.add_widget(Label(
                    text=f"[b]{log.get('medicine','?')}[/b]",
                    markup=True, font_size=dp(14), color=C_TEXT,
                    halign="left", text_size=(dp(220), None),
                    size_hint_y=None, height=dp(24)))
                info.add_widget(Label(
                    text=f"🕐 {log.get('confirmed_at','')}",
                    font_size=dp(11), color=C_SUBTEXT,
                    halign="left", text_size=(dp(220), None),
                    size_hint_y=None, height=dp(20)))

                badge = pill_label("taken", C_SUCCESS)
                row.add_widget(dot)
                row.add_widget(info)
                row.add_widget(badge)
                grid.add_widget(row)

        scroll.add_widget(grid)
        root.add_widget(scroll)
        self.add_widget(root)

    def _back(self):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "home"
        self.manager.get_screen("home").on_enter()


# ── Reminder Popup ────────────────────────────────────────────────────────────
def show_confirm_popup(idx):
    if idx >= len(state["medicines"]): return
    med = state["medicines"][idx]

    def confirm(*_):
        state["medicines"][idx]["confirmed"] = True
        state["confirmed_today"].add(med["name"])
        data = load_json(LOG_FILE)
        data.append({"username": state["user"]["username"],
                     "medicine": med["name"],
                     "confirmed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                     "confirmed_by": "app", "status": "taken"})
        save_json(LOG_FILE, data)
        save_meds(state["user"]["username"], state["medicines"])
        popup.dismiss()
        app = App.get_running_app()
        if app.sm.current == "home":
            app.sm.get_screen("home").refresh_from_reminder()

    c = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))
    draw_rounded_bg(c, C_SURFACE, dp(16))

    c.add_widget(Label(text=ICO_ALARM, font_name="Icons", font_size=dp(40),
                       color=C_PRIMARY, size_hint_y=None, height=dp(50)))
    c.add_widget(Label(
        text=f"Time to take\n[b][color=3a72fa]{med['name']}[/color][/b]\n{med['meal']} meal",
        markup=True, font_size=dp(15), color=C_TEXT,
        halign="center", text_size=(dp(260), None),
        size_hint_y=None, height=dp(70)))

    btns = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
    taken = flat_btn("I've Taken It", C_SUCCESS, h=dp(46))
    skip  = flat_btn("Skip", (0.88,0.88,0.92,1), fg=C_SUBTEXT, h=dp(46))
    popup = Popup(title="Medication Reminder", content=c,
                  size_hint=(0.88, 0.52), auto_dismiss=False,
                  separator_color=C_PRIMARY, title_color=C_TEXT,
                  title_size=dp(15))
    taken.bind(on_press=confirm)
    skip.bind(on_press=popup.dismiss)
    btns.add_widget(taken); btns.add_widget(skip)
    c.add_widget(btns)
    popup.open()


# ── Reminder thread ───────────────────────────────────────────────────────────
def reminder_loop():
    while True:
        time.sleep(1)
        if not state["user"]: continue
        now = datetime.now()
        today = now.date()
        ct = now.strftime("%H:%M")
        if today != state["last_reset"]:
            state["last_reset"] = today
            state["confirmed_today"].clear()
            for m in state["medicines"]:
                m["confirmed"] = False; m["last_notified_time"] = None
        for i, med in enumerate(state["medicines"]):
            if med["confirmed"] or med["name"] in state["confirmed_today"]: continue
            if med["start"] <= ct <= med["end"]:
                secs = get_seconds(med["freq_value"], med["freq_unit"])
                last = med.get("last_notified_time")
                if last is None or (now - last).total_seconds() >= secs:
                    med["last_notified_time"] = now
                    Clock.schedule_once(lambda dt, idx=i: show_confirm_popup(idx), 0)


# ── App entry ─────────────────────────────────────────────────────────────────
class MedReminderApp(App):
    title = "MedReminder"
    def build(self):
        init_file(USERS_FILE, [])
        init_file(LOG_FILE, [])
        self.sm = ScreenManager(transition=FadeTransition(duration=0.2))
        self.sm.add_widget(AuthScreen(name="auth"))
        self.sm.add_widget(HomeScreen(name="home"))
        self.sm.add_widget(AddScreen(name="add"))
        self.sm.add_widget(LogsScreen(name="logs"))
        threading.Thread(target=reminder_loop, daemon=True).start()
        return self.sm

if __name__ == "__main__":
    MedReminderApp().run()
