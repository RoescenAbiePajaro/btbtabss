# main.py
import os
import time
import threading
from dotenv import load_dotenv

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.progressbar import ProgressBar
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty

from pymongo import MongoClient

# Import the integrated painter screen
from VirtualPainterMobile import VirtualPainterScreen

# ---------------- Env & DB ----------------
load_dotenv()

def get_db_connection():
    """Return a pymongo db or None if unavailable."""
    try:
        MONGODB_URI = os.getenv("MONGODB_URI")
        if not MONGODB_URI:
            print("MONGODB_URI not set — continuing without DB.")
            return None
        client = MongoClient(
            MONGODB_URI,
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
        )
        client.admin.command("ping")
        print("MongoDB connection successful")
        return client["beyond_the_brush"]
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return None

db = get_db_connection()

# ---------------- Styled Widgets ----------------
class StyledLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = (1, 1, 1, 1)
        self.halign = 'left'
        self.valign = 'middle'

class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.color = (1, 1, 1, 1)
        self.bold = True
        self.size_hint_y = None
        self.height = dp(50)
        with self.canvas.before:
            Color(0.145, 0.458, 0.988, 1)
            self._rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[10])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

class StyledTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_size = '16sp'
        self.size_hint_y = None
        self.height = dp(40)
        self.background_color = (0, 0, 0, 0)
        self.foreground_color = (1, 1, 1, 1)
        self.cursor_color = (1, 1, 1, 1)
        self.hint_text_color = (1, 1, 1, 0.7)
        self.multiline = False
        self.padding = [dp(10), dp(10)]
        with self.canvas.before:
            Color(1, 1, 1, 0.2)
            self._rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[5])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

class StyledCheckBox(CheckBox):
    pass

# ---------------- Loading Screen ----------------
class LoadingScreen(Screen):
    progress_value = NumericProperty(0)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        with self.layout.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(size=Window.size, pos=self.layout.pos)
        try:
            self.logo = Image(source='logo.png', size_hint=(None, None), size=(200, 200),
                             pos_hint={'center_x': 0.5, 'center_y': 0.7})
            self.layout.add_widget(self.logo)
        except Exception:
            self.layout.add_widget(StyledLabel(text="Beyond The Brush", font_size='48sp', bold=True,
                                               pos_hint={'center_x': 0.5, 'center_y': 0.7}))
        self.loading_label = StyledLabel(text="Loading...", font_size='24sp',
                                         pos_hint={'center_x': 0.5, 'center_y': 0.4})
        self.progress_bar = ProgressBar(max=100, value=0, size_hint=(0.6, None), height=30,
                                        pos_hint={'center_x': 0.5, 'center_y': 0.3})
        self.layout.add_widget(self.loading_label)
        self.layout.add_widget(self.progress_bar)
        self.add_widget(self.layout)
        self.bind(progress_value=self._on_progress)

    def _on_progress(self, *_):
        self.progress_bar.value = self.progress_value

    def on_enter(self):
        Clock.schedule_interval(self._tick, 0.02)

    def _tick(self, dt):
        if self.progress_value < 100:
            self.progress_value += 1
        else:
            Clock.unschedule(self._tick)
            Clock.schedule_once(lambda *_: setattr(self.manager, 'current', 'entry'), 0.2)
            return False

    def on_size(self, *_):
        self._bg.size = self.size
        self._bg.pos = self.pos

# ---------------- Entry Screen ----------------
class EntryScreen(Screen):
    role = StringProperty('student')
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        with self.layout.canvas.before:
            Color(0.219, 0.196, 0.196, 1)
            self._bg = Rectangle(size=Window.size, pos=self.layout.pos)

        # Logo
        try:
            self.layout.add_widget(Image(source='logo.png', size_hint=(None, None), size=(150, 150),
                                         pos_hint={'center_x': 0.5, 'center_y': 0.8}))
        except Exception:
            self.layout.add_widget(StyledLabel(text="Beyond The Brush", font_size='36sp', bold=True,
                                               pos_hint={'center_x': 0.5, 'center_y': 0.8}))
        self.layout.add_widget(StyledLabel(text="Beyond The Brush", font_size='36sp', bold=True,
                                           pos_hint={'center_x': 0.5, 'center_y': 0.65}))

        # Role selection
        role_container = AnchorLayout(size_hint=(1, None), height=50, pos_hint={'center_x': 0.5, 'center_y': 0.55})
        role_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), size=(300, 50), spacing=20)
        # Student
        st_box = BoxLayout(orientation='horizontal', size_hint_x=None, width=150)
        st_rb = StyledCheckBox(group='role', active=True)
        st_rb.role_value = 'student'
        st_lbl = StyledLabel(text='Student', font_size='18sp', bold=True)
        st_box.add_widget(st_rb); st_box.add_widget(st_lbl)
        # Educator
        ed_box = BoxLayout(orientation='horizontal', size_hint_x=None, width=150)
        ed_rb = StyledCheckBox(group='role')
        ed_rb.role_value = 'educator'
        ed_lbl = StyledLabel(text='Educator', font_size='18sp', bold=True)
        ed_box.add_widget(ed_rb); ed_box.add_widget(ed_lbl)
        role_layout.add_widget(st_box); role_layout.add_widget(ed_box)
        role_container.add_widget(role_layout)
        self.layout.add_widget(role_container)
        st_rb.bind(active=self._on_role_change); ed_rb.bind(active=self._on_role_change)

        # Form
        form = BoxLayout(orientation='vertical', size_hint=(0.7, 0.22),
                         pos_hint={'center_x': 0.5, 'center_y': 0.4}, spacing=10)
        # Name
        nrow = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        self.name_label = StyledLabel(text="Enter your name:", font_size='16sp', size_hint_x=0.4)
        self.name_input = StyledTextInput(hint_text="Your name", size_hint_x=0.6)
        nrow.add_widget(self.name_label); nrow.add_widget(self.name_input); form.add_widget(nrow)
        # Code
        crow = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        crow.add_widget(StyledLabel(text="Access code:", font_size='16sp', size_hint_x=0.4))
        self.code_input = StyledTextInput(hint_text="Access code", password=True, size_hint_x=0.6)
        crow.add_widget(self.code_input); form.add_widget(crow)
        self.layout.add_widget(form)

        # Buttons
        btns = BoxLayout(orientation='vertical', size_hint=(0.7, 0.2),
                         pos_hint={'center_x': 0.5, 'center_y': 0.2}, spacing=10)
        self.enter_btn = StyledButton(text="Enter", font_size='18sp')
        self.enter_btn.bind(on_press=self._verify_and_launch)
        self.exit_btn = StyledButton(text="Exit", font_size='18sp')
        self.exit_btn.bind(on_press=lambda *_: App.get_running_app().stop())
        # different colors
        with self.exit_btn.canvas.before:
            Color(1, 0, 1, 1)
            self.exit_btn._rect = RoundedRectangle(size=self.exit_btn.size, pos=self.exit_btn.pos, radius=[10])
        self.exit_btn.bind(pos=self.exit_btn._update_rect, size=self.exit_btn._update_rect)
        btns.add_widget(self.enter_btn); btns.add_widget(self.exit_btn)
        self.layout.add_widget(btns)

        self.add_widget(self.layout)

    def _on_role_change(self, instance, value):
        if value:
            self.role = instance.role_value
            if self.role == 'student':
                self.name_label.text = "Enter your name:"
                self.name_input.disabled = False
                self.name_input.hint_text = "Your name"
            else:
                self.name_label.text = "Educator Name:"
                self.name_input.disabled = False
                self.name_input.hint_text = "Educator name"

    def _verify_and_launch(self, *_):
        name = self.name_input.text.strip()
        code = self.code_input.text.strip()
        if not code:
            self._popup("Error", "Please enter an access code")
            return
        if self.role == "student" and not name:
            self._popup("Error", "Please enter your name")
            return
        threading.Thread(target=self._verify_thread, args=(code, self.role, name), daemon=True).start()

    def _verify_thread(self, code, role, name):
        if db is None:
            # Offline mode: allow entry for testing
            Clock.schedule_once(lambda *_: self._launch(role, name))
            return
        try:
            access_codes = db["access_codes"]
            students = db["students"]
            code_data = access_codes.find_one({"code": code, "is_active": True})
            if not code_data:
                Clock.schedule_once(lambda *_: self._popup("Error", "Invalid access code"))
                return

            is_admin = code_data.get('is_admin_code', False)
            if role == "student" and is_admin:
                Clock.schedule_once(lambda *_: self._popup("Error", "Admin code is not for students"))
                return
            if role == "educator" and not is_admin:
                Clock.schedule_once(lambda *_: self._popup("Error", "Educator must use admin code"))
                return

            if role == "student":
                stu = students.find_one({"name": name, "access_code": code})
                if not stu:
                    # Auto-register student (or you can redirect to a Register screen)
                    students.insert_one({"name": name, "access_code": code, "registered_at": time.time()})
            # success
            Clock.schedule_once(lambda *_: self._launch(role, name))
        except Exception as e:
            Clock.schedule_once(lambda *_: self._popup("Error", f"Verification failed: {e}"))

    def _launch(self, user_type, username):
        app = App.get_running_app()
        app.user_type = user_type
        app.username = username
        painter = self.manager.get_screen('painter')
        painter.set_user(user_type, username)
        self.manager.current = 'painter'

    def _popup(self, title, msg):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(StyledLabel(text=msg))
        btn = StyledButton(text='OK', size_hint_y=None, height=40)
        pop = Popup(title=title, content=content, size_hint=(0.8, 0.4))
        btn.bind(on_press=pop.dismiss)
        content.add_widget(btn)
        pop.open()

    def on_size(self, *_):
        self._bg.size = self.size
        self._bg.pos = self.pos

# ---------------- App ----------------
class BeyondTheBrushApp(App):
    user_type = StringProperty('')
    username = StringProperty('')

    def build(self):
        # Desktop hint size; on Android this is ignored.
        Window.size = (1024, 600)
        Window.minimum_width, Window.minimum_height = Window.size
        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(LoadingScreen(name='loading'))
        sm.add_widget(EntryScreen(name='entry'))
        sm.add_widget(VirtualPainterScreen(name='painter'))  # Integrated painter
        sm.current = 'loading'
        return sm

if __name__ == '__main__':
    BeyondTheBrushApp().run()
