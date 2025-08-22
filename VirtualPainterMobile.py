# VirtualPainterMobile.py
import cv2
import numpy as np
import os
import time
import HandTrackingModule as htm
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.core.window import Window
from kivy.uix.modalview import ModalView
from kivy.metrics import dp
import json

# Set window size for mobile - larger screen
Window.size = (1024, 600)  # Increased resolution for better visibility

# KeyboardInput class
class KeyboardInput:
    def __init__(self):
        self.text = ""
        self.active = False
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_blink_interval = 0.5  # seconds
        self.text_objects = []  # Stores all text objects
        self.dragging = False
        self.drag_object_index = -1
        self.drag_offset = (0, 0)
        self.default_font = cv2.FONT_HERSHEY_SIMPLEX
        self.default_scale = 1.0
        self.default_thickness = 2
        self.default_color = (255, 255, 255)  # White
        self.outline_color = (0, 0, 0)  # Black for outline
        self.outline_thickness = 4
        self.current_input_position = (640, 360)  # Center position
        self.input_dragging = False
        self.input_drag_offset = (0, 0)
        self.selected_object_index = -1  # Track selected text object
        self.text_history = []  # To store text object states for undo/redo
        self.history_index = -1

        self.last_key_time = time.time()
        self.key_repeat_delay = 0.03  # Faster repeat rate
        self.initial_delay = 0.2  # Shorter initial delay
        self.last_key = None
        self.smooth_text = []  # Buffer for smooth text rendering
        self.text_fade_in = 1.0  # Text fade-in animation

        # Add touch-related properties
        self.touch_point = None
        self.is_touching = False
        self.touch_start_time = 0
        self.touch_threshold = 0.5  # seconds for touch to trigger keyboard

    def toggle_keyboard_mode(self):
        self.active = not self.active
        if self.active:
            self.text = ""
            self.cursor_visible = True
            self.cursor_timer = 0
            # Create a new text object at center when toggling on
            self.current_input_position = (640, 360)

    def process_key_input(self, key):
        if not self.active:
            return False

        current_time = time.time()
        time_since_last_key = current_time - self.last_key_time

        # Handle key repeat logic
        if key == self.last_key and time_since_last_key < self.key_repeat_delay:
            return False

        # Reset repeat timer if different key
        if key != self.last_key:
            self.last_key_time = current_time - self.initial_delay
            self.last_key = key
        else:
            self.last_key_time = current_time

        selected_index = self.get_selected_index()
        
        if key == 13:  # Enter key
            if selected_index >= 0:
                # Finish editing selected text
                self.clear_selection()
                self.text = ""
            else:
                if self.text:
                    # Add new text object
                    self.add_text_object()
                    self.text = ""
                    self.current_input_position = (640, 360)
            return True
        elif key == 8:  # Backspace
            if selected_index >= 0:
                text = self.text_objects[selected_index]['text']
                # Fast backspace when held
                chars_to_delete = 1
                if time_since_last_key < self.key_repeat_delay:
                    chars_to_delete = min(3, len(text))
                self.text_objects[selected_index]['text'] = text[:-chars_to_delete]
                if not self.text_objects[selected_index]['text']:
                    self.delete_selected()
            else:
                chars_to_delete = 1
                if time_since_last_key < self.key_repeat_delay:
                    chars_to_delete = min(3, len(self.text))
                self.text = self.text[:-chars_to_delete]
            return True
        elif isinstance(key, int) and 32 <= key <= 126:  # Printable ASCII characters
            if selected_index >= 0:
                self.text_objects[selected_index]['text'] += chr(key)
                # Add to smooth text buffer
                self.smooth_text.append({
                    'char': chr(key),
                    'alpha': 0,
                    'target_pos': len(self.text_objects[selected_index]['text']) - 1
                })
            else:
                self.text += chr(key)
                # Add to smooth text buffer
                self.smooth_text.append({
                    'char': chr(key),
                    'alpha': 0,
                    'target_pos': len(self.text) - 1
                })
            return True
        elif isinstance(key, str) and len(key) == 1 and ord(key) >= 32:  # Handle string input
            char_code = ord(key)
            if selected_index >= 0:
                self.text_objects[selected_index]['text'] += key
                # Add to smooth text buffer
                self.smooth_text.append({
                    'char': key,
                    'alpha': 0,
                    'target_pos': len(self.text_objects[selected_index]['text']) - 1
                })
            else:
                self.text += key
                # Add to smooth text buffer
                self.smooth_text.append({
                    'char': key,
                    'alpha': 0,
                    'target_pos': len(self.text) - 1
                })
            return True

        return False

    def get_selected_index(self):
        """Get the index of currently selected text object"""
        for i, obj in enumerate(self.text_objects):
            if obj['selected']:
                return i
        return -1

    def add_text_object(self):
        if not self.text:
            return

        self.save_state()

        self.text_objects.append({
            'text': self.text,
            'position': self.current_input_position,
            'color': self.default_color,
            'font': self.default_font,
            'scale': self.default_scale,
            'thickness': self.default_thickness,
            'selected': False
        })

    def delete_selected(self):
        """Delete the currently selected text object"""
        selected_index = self.get_selected_index()
        if selected_index >= 0:
            # Remove the selected object
            self.save_state()
            del self.text_objects[selected_index]
            self.clear_selection()

    def save_state(self):
        """Save current text objects state for undo/redo"""
        # Truncate history if we're not at the end
        if self.history_index < len(self.text_history) - 1:
            self.text_history = self.text_history[:self.history_index + 1]

        # Save current state
        self.text_history.append([obj.copy() for obj in self.text_objects])
        self.history_index = len(self.text_history) - 1

    def undo(self):
        """Undo the last text operation"""
        if self.history_index > 0:
            self.history_index -= 1
            self.text_objects = [obj.copy() for obj in self.text_history[self.history_index]]
            return True
        return False

    def redo(self):
        """Redo the last undone text operation"""
        if self.history_index < len(self.text_history) - 1:
            self.history_index += 1
            self.text_objects = [obj.copy() for obj in self.text_history[self.history_index]]
            return True
        return False

    def update(self, dt):
        if not self.active:
            return

        # Update cursor blink
        self.cursor_timer += dt
        if self.cursor_timer >= self.cursor_blink_interval:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible

        # Update smooth text animations
        for char_data in self.smooth_text[:]:
            char_data['alpha'] = min(1.0, char_data['alpha'] + dt * 5)
            if char_data['alpha'] >= 1.0:
                self.smooth_text.remove(char_data)

    def draw(self, img):
        # Draw all existing text objects
        for i, obj in enumerate(self.text_objects):
            # Draw outline
            cv2.putText(
                img,
                obj['text'],
                obj['position'],
                obj['font'],
                obj['scale'],
                self.outline_color,
                self.outline_thickness
            )
            # Draw main text
            cv2.putText(
                img,
                obj['text'],
                obj['position'],
                obj['font'],
                obj['scale'],
                obj['color'],
                obj['thickness']
            )

            # Draw selection rectangle if selected
            if obj['selected']:
                text_size = cv2.getTextSize(
                    obj['text'],
                    obj['font'],
                    obj['scale'],
                    obj['thickness']
                )[0]
                top_left = (
                    obj['position'][0] - 5,
                    obj['position'][1] - text_size[1] - 5
                )
                bottom_right = (
                    obj['position'][0] + text_size[0] + 5,
                    obj['position'][1] + 5
                )
                cv2.rectangle(img, top_left, bottom_right, (0, 255, 0), 2)

        # Draw current input text with smooth animation
        if self.active and (self.text or self.cursor_visible):
            base_text = self.text
            
            # Draw smooth text animations
            for char_data in self.smooth_text:
                pos = char_data['target_pos']
                alpha = char_data['alpha']
                color = tuple(int(c * alpha) for c in self.default_color)
                
                text_before = base_text[:pos]
                text_size = cv2.getTextSize(text_before, self.default_font, 
                                          self.default_scale, self.default_thickness)[0]
                
                char_pos = (self.current_input_position[0] + text_size[0],
                           self.current_input_position[1])
                
                # Draw animated character
                cv2.putText(img, char_data['char'], char_pos, self.default_font,
                           self.default_scale, color, self.default_thickness)

            # Draw main text
            cv2.putText(img, self.text, self.current_input_position,
                       self.default_font, self.default_scale,
                       self.default_color, self.default_thickness)

            # Draw cursor
            if self.cursor_visible:
                text_size = cv2.getTextSize(
                    self.text,
                    self.default_font,
                    self.default_scale,
                    self.default_thickness
                )[0]
                cursor_pos = (
                    self.current_input_position[0] + text_size[0],
                    self.current_input_position[1]
                )
                cv2.line(
                    img,
                    cursor_pos,
                    (cursor_pos[0], cursor_pos[1] - 30),
                    self.default_color,
                    2
                )

    def check_drag_start(self, x, y):
        # First check if we're selecting existing text objects
        for i, obj in enumerate(reversed(self.text_objects)):
            idx = len(self.text_objects) - 1 - i  # Get original index
            text_size = cv2.getTextSize(
                obj['text'],
                obj['font'],
                obj['scale'],
                obj['thickness']
            )[0]

            text_left = obj['position'][0]
            text_right = obj['position'][0] + text_size[0]
            text_top = obj['position'][1] - text_size[1]
            text_bottom = obj['position'][1]

            if (text_left <= x <= text_right and
                    text_top <= y <= text_bottom):
                # Deselect all other objects
                for other_obj in self.text_objects:
                    other_obj['selected'] = False
                # Select this object
                self.text_objects[idx]['selected'] = True
                self.drag_object_index = idx
                self.drag_offset = (x - obj['position'][0], y - obj['position'][1])
                self.dragging = True
                # Make keyboard active when selecting text
                self.active = True
                # Set current text to selected text for editing
                self.text = obj['text']
                self.current_input_position = obj['position']
                return True
    
        # Then check if we're dragging current input text (only if keyboard active)
        if self.active and (self.text or self.cursor_visible):
            text_size = cv2.getTextSize(
                self.text,
                self.default_font,
                self.default_scale,
                self.default_thickness
            )[0]

            text_left = self.current_input_position[0]
            text_right = self.current_input_position[0] + text_size[0]
            text_top = self.current_input_position[1] - text_size[1]
            text_bottom = self.current_input_position[1]

            if (text_left <= x <= text_right and
                    text_top <= y <= text_bottom):
                self.input_dragging = True
                self.input_drag_offset = (
                    x - self.current_input_position[0],
                    y - self.current_input_position[1]
                )
                return True

        # If clicking elsewhere, deselect all
        for obj in self.text_objects:
            obj['selected'] = False
        self.drag_object_index = -1
        return False

    def update_drag(self, x, y):
        if self.input_dragging:
            # Update position of current input text
            self.current_input_position = (
                x - self.input_drag_offset[0],
                y - self.input_drag_offset[1]
            )
        elif self.dragging and self.drag_object_index >= 0:
            # Update position of dragged text object
            obj = self.text_objects[self.drag_object_index]
            new_pos = (x - self.drag_offset[0], y - self.drag_offset[1])
            self.text_objects[self.drag_object_index]['position'] = new_pos
            # Also update current input position for editing
            self.current_input_position = new_pos

    def end_drag(self):
        if self.input_dragging or self.dragging:
            self.save_state()  # Save state after dragging
        self.input_dragging = False
        self.dragging = False
        self.drag_object_index = -1

    def clear_selection(self):
        """Clear all text selections"""
        for obj in self.text_objects:
            obj['selected'] = False
        self.drag_object_index = -1
        self.text = ""

    def check_touch(self, x, y):
        """Handle touch/click input on the canvas"""
        if not self.active:
            # Store touch point and start timer
            self.touch_point = (x, y)
            self.is_touching = True
            self.touch_start_time = time.time()
            return True
        return False

    def process_touch(self, x, y):
        """Process touch movement for drawing text"""
        if self.active and self.text:
            # Update position of current text
            self.current_input_position = (x, y)
            return True
        return False

    def end_touch(self):
        """Handle end of touch/click"""
        if self.is_touching:
            self.is_touching = False
            # If touch lasted long enough, activate keyboard
            if time.time() - self.touch_start_time > self.touch_threshold:
                self.toggle_keyboard_mode()
                if self.touch_point:
                    self.current_input_position = self.touch_point
                return True
        return False

class VirtualPainterMobile(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.brushSize = 15
        self.eraserSize = 40
        self.drawColor = (255, 0, 255)  # Pink
        self.detector = htm.handDetector(detectionCon=0.85)
        self.xp, self.yp = 0, 0
        # Larger canvas to match the increased screen size
        self.imgCanvas = np.zeros((600, 1024, 3), np.uint8)
        self.undoStack = []
        self.redoStack = []
        self.show_guide = False
        self.current_guide_index = 0
        self.guideList = []
        self.cap = None
        self.is_drawing = False
        self.fingers = [0, 0, 0, 0, 0]
        self.dragging_text = False
        self.selected_text_index = -1
        
        # Initialize keyboard input
        self.keyboard = KeyboardInput()
        
        # Load guides if available
        self.load_guides()
        
    def load_guides(self):
        # Load guide images if they exist
        guide_path = 'guide'
        if os.path.exists(guide_path) and os.path.isdir(guide_path):
            try:
                guide_files = sorted([f for f in os.listdir(guide_path) 
                                    if f.endswith(('.png', '.jpg', '.jpeg'))])
                for guide_file in guide_files:
                    img = cv2.imread(os.path.join(guide_path, guide_file))
                    if img is not None:
                        img = cv2.resize(img, (1024, 600))  # Resize to fit new drawing area
                        self.guideList.append(img)
            except Exception as e:
                print(f"Error loading guides: {e}")

    def toggle_guide(self, instance):
        if self.guideList:
            self.show_guide = not self.show_guide
            if self.show_guide:
                instance.text = "Hide Guide"
            else:
                instance.text = "Show Guide"
    
    def next_guide(self, instance):
        if self.guideList and self.show_guide:
            self.current_guide_index = (self.current_guide_index + 1) % len(self.guideList)

    def toggle_keyboard(self, instance):
        self.keyboard.toggle_keyboard_mode()
        if self.keyboard.active:
            instance.text = "Hide Keyboard"
        else:
            instance.text = "Show Keyboard"

    def build(self):
        # Main layout
        main_layout = BoxLayout(orientation='horizontal', padding=5, spacing=5)
        
        # Left panel for sliders - smaller relative to screen
        left_panel = BoxLayout(orientation='vertical', size_hint=(0.15, 1), spacing=5)
        
        # Brush size slider
        brush_label = Label(text=f"Brush: {self.brushSize}", size_hint=(1, 0.1), font_size='12sp')
        left_panel.add_widget(brush_label)
        
        brush_slider = Slider(min=5, max=50, value=self.brushSize, size_hint=(1, 0.1))
        brush_slider.bind(value=lambda instance, value: setattr(self, 'brushSize', int(value)))
        brush_slider.bind(value=lambda instance, value: setattr(brush_label, 'text', f"Brush: {int(value)}"))
        left_panel.add_widget(brush_slider)
        
        # Eraser size slider
        eraser_label = Label(text=f"Eraser: {self.eraserSize}", size_hint=(1, 0.1), font_size='12sp')
        left_panel.add_widget(eraser_label)
        
        eraser_slider = Slider(min=10, max=100, value=self.eraserSize, size_hint=(1, 0.1))
        eraser_slider.bind(value=lambda instance, value: setattr(self, 'eraserSize', int(value)))
        eraser_slider.bind(value=lambda instance, value: setattr(eraser_label, 'text', f"Eraser: {int(value)}"))
        left_panel.add_widget(eraser_slider)
        
        # Guide controls
        guide_label = Label(text="Guide Controls", size_hint=(1, 0.1), font_size='12sp')
        left_panel.add_widget(guide_label)
        
        guide_toggle = Button(text="Show Guide", size_hint=(1, 0.1), font_size='10sp')
        guide_toggle.bind(on_press=self.toggle_guide)
        left_panel.add_widget(guide_toggle)
        
        guide_next = Button(text="Next Guide", size_hint=(1, 0.1), font_size='10sp')
        guide_next.bind(on_press=self.next_guide)
        left_panel.add_widget(guide_next)
        
        # Keyboard button
        keyboard_btn = Button(text="Show Keyboard", size_hint=(1, 0.1), font_size='10sp')
        keyboard_btn.bind(on_press=self.toggle_keyboard)
        left_panel.add_widget(keyboard_btn)
        
        # Text controls
        text_label = Label(text="Text Controls", size_hint=(1, 0.1), font_size='12sp')
        left_panel.add_widget(text_label)
        
        # Undo/Redo buttons for text
        text_undo_redo = BoxLayout(size_hint=(1, 0.1), spacing=3)
        text_undo_btn = Button(text='Undo Text', size_hint=(1, 1), font_size='8sp')
        text_undo_btn.bind(on_press=lambda x: self.text_undo())
        text_undo_redo.add_widget(text_undo_btn)
        
        text_redo_btn = Button(text='Redo Text', size_hint=(1, 1), font_size='8sp')
        text_redo_btn.bind(on_press=lambda x: self.text_redo())
        text_undo_redo.add_widget(text_redo_btn)
        left_panel.add_widget(text_undo_redo)
        
        # Delete text button
        delete_text_btn = Button(text='Delete Text', size_hint=(1, 0.1), font_size='8sp')
        delete_text_btn.bind(on_press=lambda x: self.delete_text())
        left_panel.add_widget(delete_text_btn)
        
        # Add some spacing
        left_panel.add_widget(Label(size_hint=(1, 0.2)))
        
        main_layout.add_widget(left_panel)
        
        # Right panel for camera and controls - larger portion of screen
        right_panel = BoxLayout(orientation='vertical', size_hint=(0.85, 1), padding=5, spacing=5)
        
        # Camera display - larger portion of the screen
        self.camera_display = Image(size_hint=(1, 0.85))  # Increased height percentage
        right_panel.add_widget(self.camera_display)
        
        # Controls layout - same height but smaller relative to screen
        controls_layout = BoxLayout(size_hint=(1, 0.15), spacing=3)  # Reduced height percentage
        
        # Color selection buttons
        colors_layout = BoxLayout(size_hint=(0.6, 1), spacing=3)
        colors = [
            ('Pink', (255, 0, 255)),
            ('Blue', (255, 0, 0)),
            ('Green', (0, 255, 0)),
            ('Yellow', (0, 255, 255)),
            ('Eraser', (0, 0, 0))
        ]
        
        for color_name, color_val in colors:
            btn = ToggleButton(text=color_name, group='colors', size_hint=(1, 1), font_size='10sp')
            btn.bind(on_press=lambda instance, c=color_val: self.set_color(c))
            colors_layout.add_widget(btn)
        
        # Tools layout
        tools_layout = BoxLayout(size_hint=(0.4, 1), orientation='vertical', spacing=3)
        
        # Undo/Redo buttons
        undo_redo_layout = BoxLayout(size_hint=(1, 0.5), spacing=3)
        undo_btn = Button(text='Undo', size_hint=(1, 1), font_size='10sp')
        undo_btn.bind(on_press=lambda x: self.undo())
        undo_redo_layout.add_widget(undo_btn)
        
        redo_btn = Button(text='Redo', size_hint=(1, 1), font_size='10sp')
        redo_btn.bind(on_press=lambda x: self.redo())
        undo_redo_layout.add_widget(redo_btn)
        
        # Save/Clear buttons
        save_clear_layout = BoxLayout(size_hint=(1, 0.5), spacing=3)
        save_btn = Button(text='Save', size_hint=(1, 1), font_size='10sp')
        save_btn.bind(on_press=lambda x: self.save_canvas())
        save_clear_layout.add_widget(save_btn)
        
        clear_btn = Button(text='Clear', size_hint=(1, 1), font_size='10sp')
        clear_btn.bind(on_press=lambda x: self.clear_canvas())
        save_clear_layout.add_widget(clear_btn)
        
        tools_layout.add_widget(undo_redo_layout)
        tools_layout.add_widget(save_clear_layout)
        
        controls_layout.add_widget(colors_layout)
        controls_layout.add_widget(tools_layout)
        
        right_panel.add_widget(controls_layout)
        
        main_layout.add_widget(right_panel)
        
        # Initialize camera
        self.init_camera()
        
        # Bind keyboard events to the window
        Window.bind(on_key_down=self._on_keyboard_down)
        
        # Start updating the display
        Clock.schedule_interval(self.update, 1.0 / 30.0)  # 30 FPS
        
        return main_layout

    def _on_keyboard_down(self, window, key, scancode, codepoint, modifier):
        # Handle keyboard input
        if codepoint:  # This is the actual character
            # Convert to integer for processing
            key_code = ord(codepoint) if codepoint else key
            return self.keyboard.process_key_input(key_code)
        elif key == 8:  # Backspace
            return self.keyboard.process_key_input(8)
        elif key == 13:  # Enter
            return self.keyboard.process_key_input(13)
        elif key == 27:  # ESC key
            self.keyboard.active = False
            return True
            
        return False

    def text_undo(self):
        """Undo text operation"""
        if self.keyboard.undo():
            # Update the current text if a text object is selected
            selected_index = self.keyboard.get_selected_index()
            if selected_index >= 0:
                self.keyboard.text = self.keyboard.text_objects[selected_index]['text']
                self.keyboard.current_input_position = self.keyboard.text_objects[selected_index]['position']

    def text_redo(self):
        """Redo text operation"""
        if self.keyboard.redo():
            # Update the current text if a text object is selected
            selected_index = self.keyboard.get_selected_index()
            if selected_index >= 0:
                self.keyboard.text = self.keyboard.text_objects[selected_index]['text']
                self.keyboard.current_input_position = self.keyboard.text_objects[selected_index]['position']

    def delete_text(self):
        """Delete selected text"""
        self.keyboard.delete_selected()

    def init_camera(self):
        # Try to open camera
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            # Try different camera indices for mobile devices
            for i in range(1, 4):
                self.cap = cv2.VideoCapture(i)
                if self.cap.isOpened():
                    break
        
        if self.cap.isOpened():
            self.cap.set(3, 1024)  # Increased width
            self.cap.set(4, 600)   # Increased height

    def set_color(self, color):
        self.drawColor = color

    def undo(self):
        if self.undoStack:
            self.redoStack.append({
                'canvas': self.imgCanvas.copy(),
            })
            state = self.undoStack.pop()
            self.imgCanvas = state['canvas'].copy()

    def redo(self):
        if self.redoStack:
            self.undoStack.append({
                'canvas': self.imgCanvas.copy(),
            })
            state = self.redoStack.pop()
            self.imgCanvas = state['canvas'].copy()

    def save_canvas(self):
        # Create a combined image with both drawing and text
        combined_img = self.imgCanvas.copy()
        
        # Draw all text objects on the combined image
        self.keyboard.draw(combined_img)
        
        # Create directory if it doesn't exist
        save_dir = os.path.join(os.path.expanduser("~"), "Pictures", "VirtualPainter")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # Generate filename with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(save_dir, f"painting_{timestamp}.png")
        
        # Save the combined image
        cv2.imwrite(save_path, combined_img)
        
        # Show confirmation
        popup = Popup(title='Success', 
                     content=Label(text=f'Painting saved to:\n{save_path}'),
                     size_hint=(0.8, 0.4))
        popup.open()

    def clear_canvas(self):
        self.undoStack.append({
            'canvas': self.imgCanvas.copy(),
        })
        self.imgCanvas = np.zeros((600, 1024, 3), np.uint8)  # Updated size
        # Also clear all text objects
        self.keyboard.text_objects = []
        self.keyboard.text_history = []
        self.keyboard.history_index = -1
        self.keyboard.text = ""

    def update(self, dt):
        if self.cap and self.cap.isOpened():
            success, img = self.cap.read()
            if success:
                # Flip image horizontally for mirror effect
                img = cv2.flip(img, 1)
                
                # Resize to fit our display
                img = cv2.resize(img, (1024, 600))  # Updated size
                
                # Find hand landmarks
                img = self.detector.findHands(img, draw=False)
                lmList = self.detector.findPosition(img, draw=False)
                
                if lmList and len(lmList) >= 21:
                    # Get finger positions
                    x1, y1 = lmList[8][1:]  # Index finger
                    x2, y2 = lmList[12][1:]  # Middle finger
                    
                    # Check which fingers are up
                    self.fingers = self.detector.fingersUp()
                    
                    # Text dragging mode - two fingers up
                    if self.fingers[1] and self.fingers[2]:
                        # Check if we're starting to drag text
                        if not self.dragging_text:
                            # Try to select text at the finger position
                            if self.keyboard.check_drag_start(x1, y1):
                                self.dragging_text = True
                                self.selected_text_index = self.keyboard.drag_object_index
                        
                        # Continue dragging if we're already dragging
                        if self.dragging_text:
                            self.keyboard.update_drag(x1, y1)
                            self.is_drawing = False
                            self.xp, self.yp = 0, 0
                    
                    # Drawing mode - one finger up
                    elif self.fingers[1] and not self.fingers[2]:
                        self.dragging_text = False
                        self.selected_text_index = -1
                        self.keyboard.end_drag()
                        
                        if not self.is_drawing:
                            self.is_drawing = True
                            self.undoStack.append({
                                'canvas': self.imgCanvas.copy(),
                            })
                            self.redoStack = []
                        
                        # Draw on canvas
                        if self.xp == 0 and self.yp == 0:
                            self.xp, self.yp = x1, y1
                        
                        # Draw line
                        if self.drawColor == (0, 0, 0):  # Eraser
                            cv2.line(self.imgCanvas, (self.xp, self.yp), (x1, y1), self.drawColor, self.eraserSize)
                        else:  # Brush
                            cv2.line(self.imgCanvas, (self.xp, self.yp), (x1, y1), self.drawColor, self.brushSize)
                        
                        self.xp, self.yp = x1, y1
                    
                    else:
                        self.is_drawing = False
                        self.dragging_text = False
                        self.selected_text_index = -1
                        self.keyboard.end_drag()
                        self.xp, self.yp = 0, 0
                
                # Update keyboard
                self.keyboard.update(dt)
                
                # Combine camera image with canvas
                imgGray = cv2.cvtColor(self.imgCanvas, cv2.COLOR_BGR2GRAY)
                _, imgInv = cv2.threshold(imgGray, 50, 255, cv2.THRESH_BINARY_INV)
                imgInv = cv2.cvtColor(imgInv, cv2.COLOR_GRAY2BGR)
                img = cv2.bitwise_and(img, imgInv)
                img = cv2.bitwise_or(img, self.imgCanvas)
                
                # Draw keyboard text
                self.keyboard.draw(img)
                
                # Show guide if enabled
                if self.show_guide and self.guideList:
                    guide = self.guideList[self.current_guide_index]
                    # Blend guide with image
                    img = cv2.addWeighted(img, 0.7, guide, 0.3, 0)
                
                # Convert to texture for display
                buf = cv2.flip(img, 0).tobytes()
                texture = Texture.create(size=(img.shape[1], img.shape[0]), colorfmt='bgr')
                texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
                self.camera_display.texture = texture

    def on_stop(self):
        # Release camera when app closes
        if self.cap and self.cap.isOpened():
            self.cap.release()
        # Unbind keyboard events
        Window.unbind(on_key_down=self._on_keyboard_down)

if __name__ == '__main__':
    VirtualPainterMobile().run()