import os
import time
import threading
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.progressbar import ProgressBar
from kivy.uix.checkbox import CheckBox
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ObjectProperty
from kivy.uix.popup import Popup
from kivy.uix.anchorlayout import AnchorLayout
from kivy.metrics import dp
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection - moved to separate function for reuse
def get_db_connection():
    try:
        MONGODB_URI = os.getenv("MONGODB_URI")
        if not MONGODB_URI:
            raise ValueError("MONGODB_URI not set in environment variables")
        
        client = MongoClient(
            MONGODB_URI,
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000
        )
        client.admin.command('ping')
        db = client["beyond_the_brush"]
        print("MongoDB connection successful")
        return db
    except Exception as e:
        print(f"MongoDB connection failed: {str(e)}")
        return None

# Global db connection
db = get_db_connection()

# Custom styled components
class StyledLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = "Roboto" if os.name != 'nt' else "Arial"
        self.color = (1, 1, 1, 1)  # White text
        self.halign = 'left'
        self.valign = 'middle'

class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = "Roboto" if os.name != 'nt' else "Arial"
        self.background_color = (0, 0, 0, 0)  # Transparent background
        self.color = (1, 1, 1, 1)  # White text
        self.bold = True
        self.size_hint_y = None
        self.height = dp(50)
        
        # Create rounded rectangle background
        with self.canvas.before:
            Color(0.145, 0.458, 0.988, 1)  # Blue color
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[10])
            
        self.bind(pos=self.update_rect, size=self.update_rect)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class StyledTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = "Roboto" if os.name != 'nt' else "Arial"
        self.font_size = '16sp'
        self.size_hint_y = None
        self.height = dp(40)
        self.background_color = (0, 0, 0, 0)  # Fully transparent background
        self.foreground_color = (1, 1, 1, 1)  # White text
        self.cursor_color = (1, 1, 1, 1)  # White cursor
        self.hint_text_color = (1, 1, 1, 0.7)  # Semi-transparent white hint text
        self.multiline = False
        self.padding = [dp(10), dp(10)]
        
        # Create rounded rectangle background
        with self.canvas.before:
            Color(1, 1, 1, 0.2)  # Semi-transparent white
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[5])
            
        self.bind(pos=self.update_rect, size=self.update_rect)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class StyledCheckBox(CheckBox):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(30), dp(30))
        self.color = (0.145, 0.458, 0.988, 1)  # Blue color
        self.background_color = (0, 0, 0, 0)  # Transparent background

class LoadingScreen(Screen):
    progress_value = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super(LoadingScreen, self).__init__(**kwargs)
        self.layout = FloatLayout()
        
        with self.layout.canvas.before:
            Color(0, 0, 0, 1)  
            self.rect = Rectangle(size=Window.size, pos=self.layout.pos)
        
        # Logo
        try:
            self.logo = Image(source='icon/logo.png', size_hint=(None, None), size=(200, 200),
                             pos_hint={'center_x': 0.5, 'center_y': 0.7})
            self.layout.add_widget(self.logo)
        except:
            self.logo_label = StyledLabel(text="Beyond The Brush", font_size='48sp', bold=True,
                                   pos_hint={'center_x': 0.5, 'center_y': 0.7})
            self.layout.add_widget(self.logo_label)
        
        # Loading text
        self.loading_label = StyledLabel(text="Loading...", font_size='24sp',
                                  pos_hint={'center_x': 0.5, 'center_y': 0.4})
        self.layout.add_widget(self.loading_label)
        
        # Progress bar
        self.progress_bar = ProgressBar(max=100, value=0, size_hint=(0.6, None), height=30,
                                       pos_hint={'center_x': 0.5, 'center_y': 0.3})
        self.layout.add_widget(self.progress_bar)
        
        self.add_widget(self.layout)
        self.bind(progress_value=self.update_progress)
    
    def update_progress(self, instance, value):
        self.progress_bar.value = value
    
    def on_enter(self):
        # Start loading process
        Clock.schedule_interval(self.increment_progress, 0.03)
    
    def increment_progress(self, dt):
        if self.progress_value < 100:
            self.progress_value += 1
        else:
            Clock.unschedule(self.increment_progress)
            # Transition to entry screen after loading completes
            Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'entry'), 0.5)
            return False
    
    def on_size(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

class EntryScreen(Screen):
    role = StringProperty('student')
    
    def __init__(self, **kwargs):
        super(EntryScreen, self).__init__(**kwargs)
        self.layout = FloatLayout()
        
        with self.layout.canvas.before:
            Color(0.219, 0.196, 0.196, 1)  # #383232
            self.rect = Rectangle(size=Window.size, pos=self.layout.pos)
        
        # Logo
        try:
            self.logo = Image(source='icon/logo.png', size_hint=(None, None), size=(150, 150),
                             pos_hint={'center_x': 0.5, 'center_y': 0.8})
            self.layout.add_widget(self.logo)
        except:
            self.logo_label = StyledLabel(text="Beyond The Brush", font_size='36sp', bold=True,
                                   pos_hint={'center_x': 0.5, 'center_y': 0.8})
            self.layout.add_widget(self.logo_label)
            
        
        # Title
        self.title_label = StyledLabel(text="Beyond The Brush", font_size='36sp', bold=True,
                                pos_hint={'center_x': 0.5, 'center_y': 0.65})
        self.layout.add_widget(self.title_label)
        
        # Role selection - centered container
        role_container = AnchorLayout(size_hint=(1, None), height=50, 
                                    pos_hint={'center_x': 0.5, 'center_y': 0.55})
        
        role_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), 
                               size=(300, 50), spacing=20)
        
        # Student option
        student_option = BoxLayout(orientation='horizontal', size_hint_x=None, width=150)
        student_rb = StyledCheckBox(group='role', active=True)
        student_rb.role_value = 'student'  # Add custom attribute
        student_label = StyledLabel(text='Student', font_size='18sp', bold=True)
        student_option.add_widget(student_rb)
        student_option.add_widget(student_label)
        
        # Educator option
        educator_option = BoxLayout(orientation='horizontal', size_hint_x=None, width=150)
        educator_rb = StyledCheckBox(group='role')
        educator_rb.role_value = 'educator'  # Add custom attribute
        educator_label = StyledLabel(text='Educator', font_size='18sp', bold=True)
        educator_option.add_widget(educator_rb)
        educator_option.add_widget(educator_label)
        
        role_layout.add_widget(student_option)
        role_layout.add_widget(educator_option)
        
        role_container.add_widget(role_layout)
        self.layout.add_widget(role_container)
        
        # Bind radio buttons to role property
        student_rb.bind(active=self.on_role_change)
        educator_rb.bind(active=self.on_role_change)
        
        # Form container
        form_layout = BoxLayout(orientation='vertical', size_hint=(0.6, 0.2),
                               pos_hint={'center_x': 0.5, 'center_y': 0.4}, spacing=10)
        
        # Name field
        name_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        self.name_label = StyledLabel(text="Enter your name:", font_size='16sp', size_hint_x=0.4)
        self.name_input = StyledTextInput(hint_text="Your name", size_hint_x=0.6)
        name_layout.add_widget(self.name_label)
        name_layout.add_widget(self.name_input)
        form_layout.add_widget(name_layout)
        
        # Code field
        code_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        code_label = StyledLabel(text="Access code:", font_size='16sp', size_hint_x=0.4)
        self.code_input = StyledTextInput(hint_text="Access code", password=True, size_hint_x=0.6)
        code_layout.add_widget(code_label)
        code_layout.add_widget(self.code_input)
        form_layout.add_widget(code_layout)
        
        self.layout.add_widget(form_layout)
        
        # Buttons
        button_layout = BoxLayout(orientation='vertical', size_hint=(0.6, 0.2),
                                 pos_hint={'center_x': 0.5, 'center_y': 0.2}, spacing=10)
        
        self.enter_btn = StyledButton(text="Enter", font_size='18sp')
        self.enter_btn.bind(on_press=self.verify_and_launch)
        button_layout.add_widget(self.enter_btn)
        
        self.exit_btn = StyledButton(text="Exit", font_size='18sp')
        with self.exit_btn.canvas.before:
            Color(1, 0, 1, 1)  # Magenta color for exit button
            self.exit_btn.rect = RoundedRectangle(size=self.exit_btn.size, pos=self.exit_btn.pos, radius=[10])
        self.exit_btn.bind(on_press=self.force_close)
        button_layout.add_widget(self.exit_btn)
        
        self.layout.add_widget(button_layout)
        
        self.add_widget(self.layout)
    
    def on_role_change(self, instance, value):
        if value:  # This means the checkbox was checked
            self.role = instance.role_value  # Use the custom attribute we added
            if self.role == 'student':
                self.name_label.text = "Enter your name:"
                self.name_input.disabled = False
                self.name_input.hint_text = "Your name"
                self.name_input.background_color = (0, 0, 0, 0)  # Transparent
            else:
                self.name_label.text = "Educator Name:"
                self.name_input.disabled = False
                self.name_input.hint_text = "Educator name"
                self.name_input.background_color = (0, 0, 0, 0)  # Transparent
    
    def verify_and_launch(self, instance):
        name = self.name_input.text.strip()
        code = self.code_input.text.strip()
        
        if not code:
            self.show_popup("Error", "Please enter an access code")
            return
            
        if self.role == "student" and not name:
            self.show_popup("Error", "Please enter your name")
            return
        
        # Verify code in a separate thread to avoid UI freezing
        threading.Thread(target=self.verify_code_thread, args=(code, self.role, name)).start()
    
    def verify_code_thread(self, code, role, name):
        success, user_type, username = self.verify_code(code, role, name)
        
        # Schedule UI updates on the main thread
        if success:
            Clock.schedule_once(lambda dt: self.show_popup("Success", f"Access granted for {user_type}!"))
            Clock.schedule_once(lambda dt: self.launch_application(user_type, username), 1)
        elif user_type == "register":
            Clock.schedule_once(lambda dt: self.show_register_page(name, code))
        else:
            if role == "student":
                Clock.schedule_once(lambda dt: self.show_popup("Error", "Invalid name or access code"))
            else:
                Clock.schedule_once(lambda dt: self.show_popup("Error", "Invalid access code"))
    
    def verify_code(self, code, role, name):
        global db
        if db is None:
            db = get_db_connection()
            if db is None:
                return False, None, None
        
        try:
            access_codes_collection = db["access_codes"]
            students_collection = db["students"]
            
            code_data = access_codes_collection.find_one({"code": code, "is_active": True})
            
            if not code_data:
                return False, None, None
            
            is_admin_code = code_data.get('is_admin_code', False)
            
            if role == "student" and is_admin_code:
                return False, None, None
                
            if role == "educator" and not is_admin_code:
                return False, None, None
                
            if role == "student":
                student_data = students_collection.find_one({"access_code": code, "name": name})
                
                if student_data:
                    return True, "student", name
                else:
                    # In Kivy, we'll handle the registration prompt differently
                    return False, "register", name
                    
            elif role == "educator":
                if code_data:
                    return True, "educator", name
                else:
                    return False, None, None
            else:
                return False, None, None
                
        except Exception as e:
            return False, None, None
    
    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(StyledLabel(text=message))
        
        btn = StyledButton(text='OK', size_hint_y=None, height=40)
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.4))
        btn.bind(on_press=popup.dismiss)
        content.add_widget(btn)
        
        popup.open()
    
    def show_register_page(self, name, code):
        self.manager.get_screen('register').set_fields(name, code)
        self.manager.current = 'register'
    
    def launch_application(self, user_type, username):
        print(f"Launching application as {user_type}: {username}")
        # Launch the VirtualPainter application
        app = App.get_running_app()
        app.user_type = user_type
        app.username = username
        app.start_virtual_painter()
    
    def force_close(self, instance):
        App.get_running_app().stop()
    
    def on_size(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super(RegisterScreen, self).__init__(**kwargs)
        self.layout = FloatLayout()
        
        with self.layout.canvas.before:
            Color(0.219, 0.196, 0.196, 1)  # #383232
            self.rect = Rectangle(size=Window.size, pos=self.layout.pos)
        
        # Logo
        try:
            self.logo = Image(source='icon/logo.png', size_hint=(None, None), size=(150, 150),
                             pos_hint={'center_x': 0.5, 'center_y': 0.8})
            self.layout.add_widget(self.logo)
        except:
            self.logo_label = StyledLabel(text="Beyond The Brush", font_size='36sp', bold=True,
                                   pos_hint={'center_x': 0.5, 'center_y': 0.8})
            self.layout.add_widget(self.logo_label)
        
        # Title
        self.title_label = StyledLabel(text="Student Registration", font_size='36sp', bold=True,
                                pos_hint={'center_x': 0.5, 'center_y': 0.65})
        self.layout.add_widget(self.title_label)
        
        # Form container
        form_layout = BoxLayout(orientation='vertical', size_hint=(0.6, 0.3),
                               pos_hint={'center_x': 0.5, 'center_y': 0.45}, spacing=10)
        
        # Name field
        name_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        name_label = StyledLabel(text="Full Name:", font_size='16sp', size_hint_x=0.4)
        self.name_input = StyledTextInput(hint_text="Your full name", size_hint_x=0.6)
        name_layout.add_widget(name_label)
        name_layout.add_widget(self.name_input)
        form_layout.add_widget(name_layout)
        
        # Code field
        code_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        code_label = StyledLabel(text="Access Code:", font_size='16sp', size_hint_x=0.4)
        self.code_input = StyledTextInput(hint_text="Access code", password=True, size_hint_x=0.6)
        code_layout.add_widget(code_label)
        code_layout.add_widget(self.code_input)
        form_layout.add_widget(code_layout)
        
        self.layout.add_widget(form_layout)
        
        # Buttons
        button_layout = BoxLayout(orientation='vertical', size_hint=(0.6, 0.2),
                                 pos_hint={'center_x': 0.5, 'center_y': 0.2}, spacing=10)
        
        self.register_btn = StyledButton(text="REGISTER", font_size='18sp')
        with self.register_btn.canvas.before:
            Color(1, 0.4, 0, 1)  # Orange color for register button
            self.register_btn.rect = RoundedRectangle(size=self.register_btn.size, pos=self.register_btn.pos, radius=[10])
        self.register_btn.bind(on_press=self.register_student)
        button_layout.add_widget(self.register_btn)
        
        self.back_btn = StyledButton(text="BACK", font_size='18sp')
        with self.back_btn.canvas.before:
            Color(0.4, 0.4, 0.4, 1)  # Gray color for back button
            self.back_btn.rect = RoundedRectangle(size=self.back_btn.size, pos=self.back_btn.pos, radius=[10])
        self.back_btn.bind(on_press=self.go_back)
        button_layout.add_widget(self.back_btn)
        
        self.layout.add_widget(button_layout)
        
        self.add_widget(self.layout)
    
    def set_fields(self, name, code):
        self.name_input.text = name
        self.code_input.text = code
    
    def register_student(self, instance):
        name = self.name_input.text.strip()
        code = self.code_input.text.strip()
        
        if not name or not code:
            self.show_popup("Error", "Please fill in all fields")
            return
        
        if len(name) < 3:
            self.show_popup("Error", "Name must be at least 3 characters")
            return
        
        # Register in a separate thread
        threading.Thread(target=self.register_thread, args=(name, code)).start()
    
    def register_thread(self, name, code):
        try:
            access_codes_collection = db["access_codes"]
            students_collection = db["students"]
            
            code_data = access_codes_collection.find_one({"code": code, "is_active": True})
            if not code_data:
                Clock.schedule_once(lambda dt: self.show_popup("Error", "Invalid access code"))
                return
                
            if code_data.get('is_admin_code', False):
                Clock.schedule_once(lambda dt: self.show_popup("Error", "Cannot register with admin code"))
                return
                
            existing_student = students_collection.find_one({"name": name})
            if existing_student:
                Clock.schedule_once(lambda dt: self.show_popup("Error", "Student already exists"))
                return
                
            students_collection.insert_one({
                "name": name,
                "access_code": code,
                "registered_at": time.time()
            })
            
            Clock.schedule_once(lambda dt: self.show_popup("Success", "Registration successful!"))
            Clock.schedule_once(lambda dt: self.launch_application("student", name), 1)
            
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_popup("Error", f"Registration failed: {str(e)}"))
    
    def launch_application(self, user_type, username):
        print(f"Launching application as {user_type}: {username}")
        # Launch the VirtualPainter application
        app = App.get_running_app()
        app.user_type = user_type
        app.username = username
        app.start_virtual_painter()
    
    def go_back(self, instance):
        self.manager.current = 'entry'
    
    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(StyledLabel(text=message))
        
        btn = StyledButton(text='OK', size_hint_y=None, height=40)
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.4))
        btn.bind(on_press=popup.dismiss)
        content.add_widget(btn)
        
        popup.open()
    
    def on_size(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

class BeyondTheBrushApp(App):
    user_type = StringProperty('')
    username = StringProperty('')
    
    def build(self):
        # Set window size to 1024x600
        Window.size = (1024, 600)
        Window.minimum_width, Window.minimum_height = Window.size
        
        # Add window resize handler
        Window.bind(on_resize=self.on_window_resize)
        
        # Create screen manager
        sm = ScreenManager(transition=SlideTransition())
        
        # Add screens
        sm.add_widget(LoadingScreen(name='loading'))
        sm.add_widget(EntryScreen(name='entry'))
        sm.add_widget(RegisterScreen(name='register'))
        
        return sm
    
    def on_window_resize(self, instance, width, height):
        # Maintain minimum window size
        if width < Window.minimum_width:
            Window.size = (Window.minimum_width, height)
        if height < Window.minimum_height:
            Window.size = (width, Window.minimum_height)
    
    def start_virtual_painter(self):
        # Import and run the VirtualPainter in a separate process
        import subprocess
        import sys
        
        # Pass user info as command line arguments
        cmd = [sys.executable, "VirtualPainterMobile.py", self.user_type, self.username]
        
        # For compiled apps, we might need a different approach
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_path = sys._MEIPASS
            cmd = [os.path.join(base_path, "VirtualPainterMobile"), self.user_type, self.username]
        
        try:
            subprocess.Popen(cmd)
            self.stop()  # Close the Kivy launcher
        except Exception as e:
            print(f"Failed to start VirtualPainterMobile: {e}")
            # Fallback: show a message
            self.show_error_popup("Failed to start painting application")

    def show_error_popup(self, message):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(StyledLabel(text=message))
        
        btn = StyledButton(text='OK', size_hint_y=None, height=40)
        popup = Popup(title='Error', content=content, size_hint=(0.8, 0.4))
        btn.bind(on_press=popup.dismiss)
        content.add_widget(btn)
        
        popup.open()

if __name__ == '__main__':
    BeyondTheBrushApp().run()