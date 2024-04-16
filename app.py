from io import BytesIO
import os
import sqlite3
from PIL import Image as PILImage
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import torchvision.transforms as transforms
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.slider import Slider
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics.texture import Texture
from kivy.properties import StringProperty
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from random import choice
import random

# Check if GPU is available
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


class ColorAdjustmentApp(App):
    B_G_IMG = StringProperty("B_image.png")

    def __init__(self, **kwargs):
        super(ColorAdjustmentApp, self).__init__(**kwargs)
        self.conn = sqlite3.connect('image_database.db')
        self.cursor = self.conn.cursor()
        self.create_table()
        self.image_path = "C:/Users/Mor/Desktop/img"  # Path to the directory containing images
        self.colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # Add more colors as needed
        self.color_buttons = [Button(text=f"Color {i+1}", on_press=self.apply_color) for i in range(len(self.colors))]

    def apply_color(self, instance):
        # Apply color adjustment based on the selected color button
        index = self.color_buttons.index(instance)
        color = self.colors[index]
        
        # Extract RGB values from the selected color
        red, green, blue = color
        
        # Update the RGB sliders with the corresponding values
        self.red_slider.value = red
        self.green_slider.value = green
        self.blue_slider.value = blue
        
        # Update the image based on the new color adjustment
        self.update_image()



    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                data BLOB NOT NULL
            )
        ''')
        self.conn.commit()

    def build(self):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.image_widget = Image(size_hint=(1, None), height=500)  # Adjusted size hint

        # Color adjustment sliders
        self.red_slider = Slider(min=-100, max=100, value=0)
        self.green_slider = Slider(min=-100, max=100, value=0)
        self.blue_slider = Slider(min=-100, max=100, value=0)

        self.red_slider.bind(value=self.on_slider_change)
        self.green_slider.bind(value=self.on_slider_change)
        self.blue_slider.bind(value=self.on_slider_change)

        # Buttons
        button_layout = BoxLayout(size_hint=(1, None), height=50, spacing=10)
        self.select_button = Button(text="Select Image", on_press=self.show_dropdown, size_hint=(None, 1), width=150)
        self.style_button = Button(text="Style", on_press=self.change_style, size_hint=(None, 1), width=150)
        self.save_button = Button(text="Save Image", on_press=self.save_image, size_hint=(None, 1), width=150)
        self.reset_button = Button(text="Reset", on_press=self.reset_values, size_hint=(None, 1), width=150)
        self.zoom_in_button = Button(text="Zoom In", on_press=self.zoom_in, size_hint=(None, 1), width=150)
        self.zoom_out_button = Button(text="Zoom Out", on_press=self.zoom_out, size_hint=(None, 1), width=150)

        # Additional buttons
        self.flip_button = Button(text="Flip", on_press=self.flip_image, size_hint=(None, 1), width=150)
        self.rotate_button = Button(text="Rotate", on_press=self.rotate_image, size_hint=(None, 1), width=150)

        button_layout.add_widget(self.select_button)
        button_layout.add_widget(self.style_button)
        button_layout.add_widget(self.save_button)
        button_layout.add_widget(self.reset_button)
        button_layout.add_widget(self.zoom_in_button)
        button_layout.add_widget(self.zoom_out_button)
        button_layout.add_widget(self.flip_button)
        button_layout.add_widget(self.rotate_button)

        layout.add_widget(self.image_widget)
        layout.add_widget(button_layout)
        layout.add_widget(self.red_slider)
        layout.add_widget(self.green_slider)
        layout.add_widget(self.blue_slider)

        return layout

    def show_dropdown(self, instance):
        dropdown = DropDown()
        img_files = [f for f in os.listdir(self.image_path) if f.endswith(('.png', '.jpg', '.jpeg'))]
        if not img_files:
            popup = Popup(title='No images found', content=Label(text='No images found in the folder.'),
                          size_hint=(None, None), size=(400, 200))
            popup.open()
            return

        for img_option in img_files:
            btn = Button(text=img_option, size_hint_y=None, height=44)
            btn.bind(on_release=lambda btn: dropdown.select(btn.text))
            btn.bind(on_release=self.update_selected_img)
            dropdown.add_widget(btn)
        dropdown.open(instance)

    def update_selected_img(self, instance):
        self.selected_img = os.path.join(self.image_path, instance.text)
        self.update_image()

    def save_image(self, instance):
        # Convert the modified image to a PIL image
        pil_image = PILImage.frombytes(mode='RGBA', size=self.image_widget.texture.size,
                                       data=self.image_widget.texture.pixels)

        # Construct the file path for the new image
        img_name = os.path.basename(self.selected_img)
        img_name, img_ext = os.path.splitext(img_name)
        new_img_path = os.path.join('C:/Users/Mor/Desktop/img', f'{img_name}_modified{img_ext}')  # Modify the image name

        # Save the modified image
        pil_image.save(new_img_path)

        print(f"Image saved to: {new_img_path}")
    
    
    def reset_values(self, instance):
        # Reset sliders to default values
        self.red_slider.value = 0
        self.green_slider.value = 0
        self.blue_slider.value = 0

        # Reset selected image to None
        self.selected_img = None
        
        # Update the image
        self.update_image()


    def change_style(self, instance):
        # Randomly select colors for the sliders from the additional color buttons
        random_color_button = random.choice(self.color_buttons)
        self.apply_color(random_color_button)

    def on_slider_change(self, instance, value):
        self.update_image()

    def update_image(self):
        if self.selected_img is None:
            return  # No image selected, so do nothing

        # Load the selected image
        pil_image = PILImage.open(self.selected_img)
        img = np.array(pil_image)

        # Apply color adjustments
        img[:, :, 0] = np.clip(img[:, :, 0] + self.red_slider.value, 0, 255)
        img[:, :, 1] = np.clip(img[:, :, 1] + self.green_slider.value, 0, 255)
        img[:, :, 2] = np.clip(img[:, :, 2] + self.blue_slider.value, 0, 255)

        # Flip image vertically
        img = np.flipud(img)

        # Update the image widget
        texture = Texture.create(size=(img.shape[1], img.shape[0]), colorfmt='rgb')
        texture.blit_buffer(img.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        self.image_widget.texture = texture

    def zoom_in(self, instance):
        # Get the current texture size
        texture_size = self.image_widget.texture.size

        # Calculate the new size for zoom in (increase by 10%)
        new_width = int(texture_size[0] * 1.1)
        new_height = int(texture_size[1] * 1.1)

        # Adjust the texture coordinates for zoom in
        self.image_widget.texture.uvsize = (new_width / self.image_widget.width, new_height / self.image_widget.height)

    def zoom_out(self, instance):
        # Get the current texture size
        texture_size = self.image_widget.texture.size

        # Calculate the new size for zoom out (reduce by 10%)
        new_width = int(texture_size[0] * 0.9)
        new_height = int(texture_size[1] * 0.9)

        # Adjust the texture coordinates for zoom out
        self.image_widget.texture.uvsize = (new_width / self.image_widget.width, new_height / self.image_widget.height)

    def flip_image(self, instance):
        # Flip the image horizontally
        pil_image = PILImage.open(self.selected_img)
        pil_image = pil_image.transpose(PILImage.FLIP_LEFT_RIGHT)

        # Convert the flipped image to numpy array and update the texture
        img = np.array(pil_image)
        texture = Texture.create(size=(img.shape[1], img.shape[0]), colorfmt='rgb')
        texture.blit_buffer(img.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        self.image_widget.texture = texture


    def rotate_image(self, instance):
        # Load the selected image
        pil_image = PILImage.open(self.selected_img)

        # Rotate the image by 90 degrees clockwise
        pil_image = pil_image.rotate(-90, expand=True)

        # Convert the rotated image to numpy array and update the texture
        img = np.array(pil_image)
        texture = Texture.create(size=(img.shape[1], img.shape[0]), colorfmt='rgb')
        texture.blit_buffer(img.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        self.image_widget.texture = texture


if __name__ == '__main__':
    ColorAdjustmentApp().run()
