# VirtualPainterMobile.py
import os
import time
import cv2
import numpy as np
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp

# Optional (your module must be present beside these files)
import HandTrackingModule as htm

# --------------- Text / Keyboard helper (same as your class, trimmed docstrings) ---------------
class KeyboardInput:
    def __init__(self):
        self.text = ""
        self.active = False
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_blink_interval = 0.5
        self.text_objects = []
        self.dragging = False
        self.drag_object_index = -1
        self.drag_offset = (0, 0)
        self.default_font = cv2.FONT_HERSHEY_SIMPLEX
        self.default_scale = 1.0
        self.default_thickness = 2
        self.default_color = (255, 255, 255)
        self.outline_color = (0, 0, 0)
        self.outline_thickness = 4
        self.current_input_position = (640, 360)
        self.input_dragging = False
        self.input_drag_offset = (0, 0)
        self.selected_object_index = -1
        self.text_history = []
        self.history_index = -1
        self.last_key_time = time.time()
        self.key_repeat_delay = 0.03
        self.initial_delay = 0.2
        self.last_key = None
        self.smooth_text = []
        self.text_fade_in = 1.0
        self.touch_point = None
        self.is_touching = False
        self.touch_start_time = 0
        self.touch_threshold = 0.5

    def toggle_keyboard_mode(self):
        self.active = not self.active
        if self.active:
            self.text = ""
            self.cursor_visible = True
            self.cursor_timer = 0
            self.current_input_position = (640, 360)

    def process_key_input(self, key):
        if not self.active:
            return False
        current_time = time.time()
        time_since_last_key = current_time - self.last_key_time
        if key == self.last_key and time_since_last_key < self.key_repeat_delay:
            return False
        if key != self.last_key:
            self.last_key_time = current_time - self.initial_delay
            self.last_key = key
        else:
            self.last_key_time = current_time

        selected_index = self.get_selected_index()

        if key == 13:
            if selected_index >= 0:
                self.clear_selection()
                self.text = ""
            else:
                if self.text:
                    self.add_text_object()
                    self.text = ""
                    self.current_input_position = (640, 360)
            return True
        elif key == 8:
            if selected_index >= 0:
                text = self.text_objects[selected_index]['text']
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
        elif isinstance(key, int) and 32 <= key <= 126:
            if selected_index >= 0:
                self.text_objects[selected_index]['text'] += chr(key)
                self.smooth_text.append({'char': chr(key), 'alpha': 0, 'target_pos': len(self.text_objects[selected_index]['text']) - 1})
            else:
                self.text += chr(key)
                self.smooth_text.append({'char': chr(key), 'alpha': 0, 'target_pos': len(self.text) - 1})
            return True
        elif isinstance(key, str) and len(key) == 1 and ord(key) >= 32:
            if selected_index >= 0:
                self.text_objects[selected_index]['text'] += key
                self.smooth_text.append({'char': key, 'alpha': 0, 'target_pos': len(self.text_objects[selected_index]['text']) - 1})
            else:
                self.text += key
                self.smooth_text.append({'char': key, 'alpha': 0, 'target_pos': len(self.text) - 1})
            return True
        return False

    def get_selected_index(self):
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
        idx = self.get_selected_index()
        if idx >= 0:
            self.save_state()
            del self.text_objects[idx]
            self.clear_selection()

    def save_state(self):
        if self.history_index < len(self.text_history) - 1:
            self.text_history = self.text_history[:self.history_index + 1]
        self.text_history.append([obj.copy() for obj in self.text_objects])
        self.history_index = len(self.text_history) - 1

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.text_objects = [obj.copy() for obj in self.text_history[self.history_index]]
            return True
        return False

    def redo(self):
        if self.history_index < len(self.text_history) - 1:
            self.history_index += 1
            self.text_objects = [obj.copy() for obj in self.text_history[self.history_index]]
            return True
        return False

    def update(self, dt):
        if not self.active:
            return
        self.cursor_timer += dt
        if self.cursor_timer >= self.cursor_blink_interval:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible
        for char_data in self.smooth_text[:]:
            char_data['alpha'] = min(1.0, char_data['alpha'] + dt * 5)
            if char_data['alpha'] >= 1.0:
                self.smooth_text.remove(char_data)

    def draw(self, img):
        # existing objects
        for i, obj in enumerate(self.text_objects):
            cv2.putText(img, obj['text'], obj['position'], obj['font'], obj['scale'], (0, 0, 0), 4)
            cv2.putText(img, obj['text'], obj['position'], obj['font'], obj['scale'], obj['color'], obj['thickness'])
            if obj['selected']:
                text_size = cv2.getTextSize(obj['text'], obj['font'], obj['scale'], obj['thickness'])[0]
                tl = (obj['position'][0] - 5, obj['position'][1] - text_size[1] - 5)
                br = (obj['position'][0] + text_size[0] + 5, obj['position'][1] + 5)
                cv2.rectangle(img, tl, br, (0, 255, 0), 2)

        # current input
        if self.active and (self.text or self.cursor_visible):
            base_text = self.text
            for char_data in self.smooth_text:
                pos = char_data['target_pos']
                alpha = char_data['alpha']
                color = tuple(int(c * alpha) for c in (255, 255, 255))
                text_before = base_text[:pos]
                text_size = cv2.getTextSize(text_before, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
                char_pos = (self.current_input_position[0] + text_size[0], self.current_input_position[1])
                cv2.putText(img, char_data['char'], char_pos, cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

            cv2.putText(img, self.text, self.current_input_position, cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

            if self.cursor_visible:
                text_size = cv2.getTextSize(self.text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
                cursor_pos = (self.current_input_position[0] + text_size[0], self.current_input_position[1])
                cv2.line(img, cursor_pos, (cursor_pos[0], cursor_pos[1] - 30), (255, 255, 255), 2)

    def check_drag_start(self, x, y):
        for i, obj in enumerate(reversed(self.text_objects)):
            idx = len(self.text_objects) - 1 - i
            text_size = cv2.getTextSize(obj['text'], obj['font'], obj['scale'], obj['thickness'])[0]
            left, right = obj['position'][0], obj['position'][0] + text_size[0]
            top, bottom = obj['position'][1] - text_size[1], obj['position'][1]
            if (left <= x <= right and top <= y <= bottom):
                for other in self.text_objects: other['selected'] = False
                self.text_objects[idx]['selected'] = True
                self.drag_object_index = idx
                self.drag_offset = (x - obj['position'][0], y - obj['position'][1])
                self.dragging = True
                self.active = True
                self.text = obj['text']
                self.current_input_position = obj['position']
                return True
        if self.active and (self.text or self.cursor_visible):
            text_size = cv2.getTextSize(self.text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
            left, right = self.current_input_position[0], self.current_input_position[0] + text_size[0]
            top, bottom = self.current_input_position[1] - text_size[1], self.current_input_position[1]
            if (left <= x <= right and top <= y <= bottom):
                self.input_dragging = True
                self.input_drag_offset = (x - self.current_input_position[0], y - self.current_input_position[1])
                return True
        for obj in self.text_objects:
            obj['selected'] = False
        self.drag_object_index = -1
        return False

    def update_drag(self, x, y):
        if self.input_dragging:
            self.current_input_position = (x - self.input_drag_offset[0], y - self.input_drag_offset[1])
        elif self.dragging and self.drag_object_index >= 0:
            new_pos = (x - self.drag_offset[0], y - self.drag_offset[1])
            self.text_objects[self.drag_object_index]['position'] = new_pos
            self.current_input_position = new_pos

    def end_drag(self):
        if self.input_dragging or self.dragging:
            self.save_state()
        self.input_dragging = False
        self.dragging = False
        self.drag_object_index = -1

    def clear_selection(self):
        for obj in self.text_objects: obj['selected'] = False
        self.drag_object_index = -1
        self.text = ""

# --------------- Painter Screen ---------------
class VirtualPainterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # State
        self.user_type = ""
        self.username = ""
        self.brushSize = 15
        self.eraserSize = 40
        self.drawColor = (255, 0, 255)  # Pink
        self.detector = htm.handDetector(detectionCon=0.85)
        self.xp, self.yp = 0, 0
        self.imgCanvas = np.zeros((600, 1024, 3), np.uint8)
        self.undoStack, self.redoStack = [], []
        self.show_guide = False
        self.current_guide_index = 0
        self.guideList = []
        self.cap = None
        self.use_kivy_camera = False
        self.camera_widget = None
        self.is_drawing = False
        self.fingers = [0, 0, 0, 0, 0]
        self.dragging_text = False
        self.selected_text_index = -1
        self.keyboard = KeyboardInput()

        # UI
        self._build_ui()
        # Guides
        self._load_guides()
        # Camera init
        self._init_camera()
        # Keyboard events
        Window.bind(on_key_down=self._on_keyboard_down)
        # Update loop
        Clock.schedule_interval(self._update, 1.0 / 30.0)  # 30 FPS

    # --------- Public API ---------
    def set_user(self, user_type, username):
        self.user_type = user_type
        self.username = username

    # --------- UI ----------
    def _build_ui(self):
        main_layout = BoxLayout(orientation='horizontal', padding=5, spacing=5)

        # Left panel
        left = BoxLayout(orientation='vertical', size_hint=(0.18, 1), spacing=5)
        # Brush
        brush_label = Label(text=f"Brush: {self.brushSize}", size_hint=(1, 0.07))
        brush_slider = Slider(min=5, max=50, value=self.brushSize, size_hint=(1, 0.07))
        brush_slider.bind(value=lambda inst, val: setattr(self, 'brushSize', int(val)))
        brush_slider.bind(value=lambda inst, val: setattr(brush_label, 'text', f"Brush: {int(val)}"))
        left.add_widget(brush_label); left.add_widget(brush_slider)
        # Eraser
        eraser_label = Label(text=f"Eraser: {self.eraserSize}", size_hint=(1, 0.07))
        eraser_slider = Slider(min=10, max=100, value=self.eraserSize, size_hint=(1, 0.07))
        eraser_slider.bind(value=lambda inst, val: setattr(self, 'eraserSize', int(val)))
        eraser_slider.bind(value=lambda inst, val: setattr(eraser_label, 'text', f"Eraser: {int(val)}"))
        left.add_widget(eraser_label); left.add_widget(eraser_slider)
        # Guide
        left.add_widget(Label(text="Guide Controls", size_hint=(1, 0.06)))
        guide_toggle = Button(text="Show Guide", size_hint=(1, 0.06))
        guide_toggle.bind(on_press=self._toggle_guide)
        guide_next = Button(text="Next Guide", size_hint=(1, 0.06))
        guide_next.bind(on_press=self._next_guide)
        left.add_widget(guide_toggle); left.add_widget(guide_next)
        # Keyboard
        keyboard_btn = Button(text="Show Keyboard", size_hint=(1, 0.06))
        keyboard_btn.bind(on_press=self._toggle_keyboard)
        left.add_widget(keyboard_btn)
        # Text ops
        left.add_widget(Label(text="Text Controls", size_hint=(1, 0.06)))
        trow = BoxLayout(size_hint=(1, 0.06), spacing=3)
        undo_t = Button(text="Undo Text"); redo_t = Button(text="Redo Text")
        undo_t.bind(on_press=lambda *_: self._text_undo()); redo_t.bind(on_press=lambda *_: self._text_redo())
        trow.add_widget(undo_t); trow.add_widget(redo_t)
        left.add_widget(trow)
        del_text = Button(text="Delete Text", size_hint=(1, 0.06))
        del_text.bind(on_press=lambda *_: self.keyboard.delete_selected())
        left.add_widget(del_text)
        left.add_widget(Label(size_hint=(1, 0.25)))  # spacer

        main_layout.add_widget(left)

        # Right panel
        right = BoxLayout(orientation='vertical', size_hint=(0.82, 1), padding=5, spacing=5)
        self.camera_display = Image(size_hint=(1, 0.85))
        right.add_widget(self.camera_display)

        controls = BoxLayout(size_hint=(1, 0.15), spacing=3)
        colors_layout = BoxLayout(size_hint=(0.6, 1), spacing=3)
        for name, val in [('Pink', (255, 0, 255)), ('Blue', (255, 0, 0)),
                          ('Green', (0, 255, 0)), ('Yellow', (0, 255, 255)),
                          ('Eraser', (0, 0, 0))]:
            b = ToggleButton(text=name, group='colors')
            b.bind(on_press=lambda inst, c=val: setattr(self, 'drawColor', c))
            colors_layout.add_widget(b)

        tools_layout = BoxLayout(size_hint=(0.4, 1), orientation='vertical', spacing=3)
        ur = BoxLayout(size_hint=(1, 0.5), spacing=3)
        undo_btn = Button(text='Undo'); redo_btn = Button(text='Redo')
        undo_btn.bind(on_press=lambda *_: self._undo()); redo_btn.bind(on_press=lambda *_: self._redo())
        ur.add_widget(undo_btn); ur.add_widget(redo_btn)
        sc = BoxLayout(size_hint=(1, 0.5), spacing=3)
        save_btn = Button(text='Save'); clear_btn = Button(text='Clear')
        save_btn.bind(on_press=lambda *_: self._save_canvas()); clear_btn.bind(on_press=lambda *_: self._clear_canvas())
        sc.add_widget(save_btn); sc.add_widget(clear_btn)
        tools_layout.add_widget(ur); tools_layout.add_widget(sc)

        controls.add_widget(colors_layout); controls.add_widget(tools_layout)
        right.add_widget(controls)
        main_layout.add_widget(right)

        self.add_widget(main_layout)

    # --------- Guides ----------
    def _load_guides(self):
        guide_path = os.path.join('assets', 'guide')
        if os.path.exists(guide_path) and os.path.isdir(guide_path):
            try:
                files = sorted([f for f in os.listdir(guide_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
                for f in files:
                    img = cv2.imread(os.path.join(guide_path, f))
                    if img is not None:
                        img = cv2.resize(img, (1024, 600))
                        self.guideList.append(img)
            except Exception as e:
                print(f"Error loading guides: {e}")

    def _toggle_guide(self, btn):
        if self.guideList:
            self.show_guide = not self.show_guide
            btn.text = "Hide Guide" if self.show_guide else "Show Guide"

    def _next_guide(self, *_):
        if self.guideList and self.show_guide:
            self.current_guide_index = (self.current_guide_index + 1) % len(self.guideList)

    def _toggle_keyboard(self, btn):
        self.keyboard.toggle_keyboard_mode()
        btn.text = "Hide Keyboard" if self.keyboard.active else "Show Keyboard"

    # --------- Keyboard ----------
    def _on_keyboard_down(self, window, key, scancode, codepoint, modifiers):
        # On Android, physical keyboard might not exist; soft keyboard events come via TextInput typically.
        # This still supports desktop testing.
        if codepoint:
            key_code = ord(codepoint)
            return self.keyboard.process_key_input(key_code)
        elif key == 8:
            return self.keyboard.process_key_input(8)
        elif key == 13:
            return self.keyboard.process_key_input(13)
        elif key == 27:
            self.keyboard.active = False
            return True
        return False

    def _text_undo(self):
        if self.keyboard.undo():
            idx = self.keyboard.get_selected_index()
            if idx >= 0:
                self.keyboard.text = self.keyboard.text_objects[idx]['text']
                self.keyboard.current_input_position = self.keyboard.text_objects[idx]['position']

    def _text_redo(self):
        if self.keyboard.redo():
            idx = self.keyboard.get_selected_index()
            if idx >= 0:
                self.keyboard.text = self.keyboard.text_objects[idx]['text']
                self.keyboard.current_input_position = self.keyboard.text_objects[idx]['position']

    # --------- Drawing stacks ----------
    def _undo(self):
        if self.undoStack:
            self.redoStack.append({'canvas': self.imgCanvas.copy()})
            state = self.undoStack.pop()
            self.imgCanvas = state['canvas'].copy()

    def _redo(self):
        if self.redoStack:
            self.undoStack.append({'canvas': self.imgCanvas.copy()})
            state = self.redoStack.pop()
            self.imgCanvas = state['canvas'].copy()

    def _save_canvas(self):
        combined = self.imgCanvas.copy()
        self.keyboard.draw(combined)
        save_dir = os.path.join(os.path.expanduser("~"), "Pictures", "VirtualPainter")
        os.makedirs(save_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(save_dir, f"painting_{ts}.png")
        cv2.imwrite(path, combined)
        print(f"Saved: {path}")

    def _clear_canvas(self):
        self.undoStack.append({'canvas': self.imgCanvas.copy()})
        self.imgCanvas = np.zeros((600, 1024, 3), np.uint8)
        self.keyboard.text_objects = []
        self.keyboard.text_history = []
        self.keyboard.history_index = -1
        self.keyboard.text = ""

    # --------- Camera ----------
    def _init_camera(self):
        # Try OpenCV first
        try:
            cap = cv2.VideoCapture(0)
            if not cap or not cap.isOpened():
                raise RuntimeError("cv2 camera not available")
            cap.set(3, 1024); cap.set(4, 600)
            self.cap = cap
            self.use_kivy_camera = False
            print("Using OpenCV VideoCapture")
            return
        except Exception as e:
            print(f"OpenCV camera failed: {e}")

        # Fallback to Kivy Camera
        try:
            from kivy.uix.camera import Camera
            self.camera_widget = Camera(play=True, resolution=(1024, 600))
            # We won't add the widget directly (we use our own Image for compositing),
            # but we keep it hidden offscreen—Kivy will still fill the texture.
            self.camera_widget.opacity = 0
            self.add_widget(self.camera_widget)
            self.use_kivy_camera = True
            print("Using Kivy Camera fallback")
        except Exception as e:
            print(f"Kivy Camera fallback failed: {e}")

    def _get_frame(self):
        """Return a BGR image (1024x600) or None."""
        if self.cap is not None:
            ok, img = self.cap.read()
            if not ok: return None
            img = cv2.flip(img, 1)
            img = cv2.resize(img, (1024, 600))
            return img
        if self.use_kivy_camera and self.camera_widget and self.camera_widget.texture:
            tex = self.camera_widget.texture
            # texture is RGBA; convert to numpy array
            w, h = tex.size
            # tex.pixels is bytes in RGBA
            buf = tex.pixels  # length w*h*4
            frame = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            frame = cv2.flip(frame, 1)
            if (w, h) != (1024, 600):
                frame = cv2.resize(frame, (1024, 600))
            return frame
        return None

    # --------- Main update loop ----------
    def _update(self, dt):
        img = self._get_frame()
        if img is None:
            return

        # Hand tracking
        img_proc = self.detector.findHands(img, draw=False)
        lmList = self.detector.findPosition(img, draw=False)

        if lmList and len(lmList) >= 21:
            # Fix: Get coordinates correctly from lmList
            x1, y1 = lmList[8][1], lmList[8][2]  # index finger tip
            x2, y2 = lmList[12][1], lmList[12][2]  # middle finger tip
            
            self.fingers = self.detector.fingersUp()

            # Two fingers up -> drag text
            if self.fingers[1] and self.fingers[2]:
                if not self.dragging_text:
                    if self.keyboard.check_drag_start(x1, y1):
                        self.dragging_text = True
                        self.selected_text_index = self.keyboard.drag_object_index
                if self.dragging_text:
                    self.keyboard.update_drag(x1, y1)
                    self.is_drawing = False
                    self.xp, self.yp = 0, 0

            # One finger up -> draw
            elif self.fingers[1] and not self.fingers[2]:
                self.dragging_text = False
                self.selected_text_index = -1
                self.keyboard.end_drag()

                if not self.is_drawing:
                    self.is_drawing = True
                    self.undoStack.append({'canvas': self.imgCanvas.copy()})
                    self.redoStack = []

                if self.xp == 0 and self.yp == 0:
                    self.xp, self.yp = x1, y1

                if self.drawColor == (0, 0, 0):
                    cv2.line(self.imgCanvas, (self.xp, self.yp), (x1, y1), self.drawColor, self.eraserSize)
                else:
                    cv2.line(self.imgCanvas, (self.xp, self.yp), (x1, y1), self.drawColor, self.brushSize)

                self.xp, self.yp = x1, y1

            else:
                self.is_drawing = False
                self.dragging_text = False
                self.selected_text_index = -1
                self.keyboard.end_drag()
                self.xp, self.yp = 0, 0

        # Update keyboard animations
        self.keyboard.update(dt)

        # Composite canvas onto camera
        imgGray = cv2.cvtColor(self.imgCanvas, cv2.COLOR_BGR2GRAY)
        _, imgInv = cv2.threshold(imgGray, 50, 255, cv2.THRESH_BINARY_INV)
        imgInv = cv2.cvtColor(imgInv, cv2.COLOR_GRAY2BGR)
        img_out = cv2.bitwise_and(img, imgInv)
        img_out = cv2.bitwise_or(img_out, self.imgCanvas)

        # Draw keyboard text on output
        self.keyboard.draw(img_out)

        # Guide overlay
        if self.show_guide and self.guideList:
            guide = self.guideList[self.current_guide_index]
            img_out = cv2.addWeighted(img_out, 0.7, guide, 0.3, 0)

        # Send to Kivy Image (BGR->BGR expected, flipped vertically)
        buf = cv2.flip(img_out, 0).tobytes()
        texture = Texture.create(size=(img_out.shape[1], img_out.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.camera_display.texture = texture

    def on_leave(self, *_):
        # Stop camera if leaving screen
        if self.cap and self.cap.isOpened():
            self.cap.release()
        Window.unbind(on_key_down=self._on_keyboard_down)