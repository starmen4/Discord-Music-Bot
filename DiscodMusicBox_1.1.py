import os
import discord
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QFileDialog, QListWidgetItem, QMessageBox,
    QSlider, QLabel
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QColor
from discord.ext import commands
import threading
from queue import Queue
import time

# Set up bot
TOKEN = " Put Your Token HERE "  # Replace with your actual bot token

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Define the file path to store selected quick play files
QUICK_PLAY_FILE = "quick_play_files.txt"

# Global variables
vc = None
file_queue = Queue()
paused_file = None
paused_position = 0
current_file = None
start_time = None
music_volume = 1.0
quick_sound_volume = 1.0
vc_lock = asyncio.Lock()
is_playing_quick_sound = False

# Loads quick play sound file paths from a text file
def load_quick_play_files():
    quick_play_files = {}
    if os.path.exists(QUICK_PLAY_FILE):
        with open(QUICK_PLAY_FILE, "r") as f:
            lines = f.readlines()
            for line in lines:
                name, path = line.strip().split(":", 1)
                quick_play_files[name] = path
    return quick_play_files

# Saves a quick play sound file path to a text file
def save_quick_play_file(name, file_path):
    quick_play_files = load_quick_play_files()
    quick_play_files[name] = file_path
    with open(QUICK_PLAY_FILE, "w") as f:
        for name, path in quick_play_files.items():
            f.write(f"{name}:{path}\n")

# Bot thread to run the Discord bot
class BotThread(QThread):
    update_signal = pyqtSignal()
    ready_signal = pyqtSignal(bool)

    def run(self):
        asyncio.run(self.start_bot())

    async def start_bot(self):
        @bot.event
        async def on_ready():
            print(f"Bot is logged in as {bot.user}")
            if bot.guilds:
                print(f"Connected to {len(bot.guilds)} guild(s).")
            else:
                print("❌ ERROR: Bot is not in any guilds!")
            self.ready_signal.emit(True)

        await bot.start(TOKEN)

# Main GUI window class for the Discord music player
class MainWindow(QMainWindow):
    stop_button_signal = pyqtSignal(bool)

    def __init__(self, bot_thread):
        super().__init__()
        self.setWindowTitle("Discord Music Player")
        self.setGeometry(100, 100, 600, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        # Connection Controls
        connection_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_voice)
        self.connect_button.setEnabled(False)
        connection_layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_from_voice)
        self.disconnect_button.setEnabled(False)
        connection_layout.addWidget(self.disconnect_button)
        layout.addLayout(connection_layout)

        # Playback Controls
        playback_layout = QHBoxLayout()
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(lambda: asyncio.run_coroutine_threadsafe(self.pause_music(), bot.loop))
        playback_layout.addWidget(self.pause_button)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(lambda: asyncio.run_coroutine_threadsafe(self.resume_music(), bot.loop))
        playback_layout.addWidget(self.play_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(lambda: asyncio.run_coroutine_threadsafe(self.stop_music(), bot.loop))
        self.stop_button.setEnabled(False)
        playback_layout.addWidget(self.stop_button)

        self.skip_button = QPushButton("Skip")
        self.skip_button.clicked.connect(lambda: asyncio.run_coroutine_threadsafe(self.skip_to_next(), bot.loop))
        playback_layout.addWidget(self.skip_button)

        layout.addLayout(playback_layout)

        # Volume Controls
        volume_layout = QHBoxLayout()
        self.music_volume_slider = QSlider()
        self.music_volume_slider.setMinimum(0)
        self.music_volume_slider.setMaximum(100)
        self.music_volume_slider.setValue(100)
        self.music_volume_slider.valueChanged.connect(self.update_music_volume)
        volume_layout.addWidget(QLabel("Music Volume"))
        volume_layout.addWidget(self.music_volume_slider)
        layout.addLayout(volume_layout)

        quick_volume_layout = QHBoxLayout()
        self.quick_sound_volume_slider = QSlider()
        self.quick_sound_volume_slider.setMinimum(0)
        self.quick_sound_volume_slider.setMaximum(100)
        self.quick_sound_volume_slider.setValue(100)
        self.quick_sound_volume_slider.valueChanged.connect(self.update_quick_sound_volume)
        quick_volume_layout.addWidget(QLabel("Quick Sound Volume"))
        quick_volume_layout.addWidget(self.quick_sound_volume_slider)
        layout.addLayout(quick_volume_layout)

        # File Picker
        self.pick_file_button = QPushButton("Pick File")
        self.pick_file_button.clicked.connect(self.pick_file)
        layout.addWidget(self.pick_file_button)

        # Queue Display
        self.queue_list = QListWidget()
        layout.addWidget(self.queue_list)

        # Quick Sound Buttons
        quick_sound_layout = QVBoxLayout()
        self.quick_buttons = {}
        for i in range(1, 13):
            button = QPushButton(f"Quick Sound {i}")
            button.clicked.connect(lambda _, i=i: self.play_quick_sound(i))
            quick_sound_layout.addWidget(button)
            self.quick_buttons[i] = button
        layout.addLayout(quick_sound_layout)

        # Connect signals
        bot_thread.ready_signal.connect(self.on_bot_ready)
        self.stop_button_signal.connect(self.stop_button.setEnabled)

        # Load existing quick play files
        quick_play_files = load_quick_play_files()
        for i in range(1, 13):
            if f"Quick Sound {i}" in quick_play_files:
                file_path = quick_play_files[f"Quick Sound {i}"]
                self.quick_buttons[i].setText(os.path.basename(file_path))

    # Handles bot ready event to enable connection button
    def on_bot_ready(self, ready):
        if ready:
            self.connect_button.setEnabled(True)
            print("Bot is ready, connect button enabled.")

    # Initiates connection to voice channel
    def connect_to_voice(self):
        asyncio.run_coroutine_threadsafe(self.connect_to_voice_async(), bot.loop)

    # Asynchronous method to connect to voice channel
    async def connect_to_voice_async(self):
        global vc
        print("Attempting to connect to voice...")
        if not bot.guilds:
            print("❌ ERROR: Bot is not in any servers!")
            return
        guild = bot.guilds[0]
        print(f"🔍 Searching for voice channel in: {guild.name}")
        voice_channel = discord.utils.get(guild.voice_channels, name="tutturu~")
        if voice_channel:
            print(f"🎤 Found voice channel: {voice_channel.name}, joining...")
            try:
                vc = await voice_channel.connect()
                print("🎶 Successfully connected to voice channel.")
                self.disconnect_button.setEnabled(True)
                self.connect_button.setEnabled(False)
            except discord.errors.ClientException:
                print("❌ ERROR: Already connected to a voice channel!")
        else:
            print("❌ ERROR: Voice channel 'tutturu~' not found!")

    # Disconnects from voice channel
    def disconnect_from_voice(self):
        global vc
        if vc:
            asyncio.run_coroutine_threadsafe(vc.disconnect(), bot.loop)
            print("👋 Disconnected from voice channel.")
            self.disconnect_button.setEnabled(False)
            self.connect_button.setEnabled(True)
        else:
            print("❌ ERROR: Not connected to any voice channel.")

    # Pauses the currently playing music
    async def pause_music(self):
        async with vc_lock:
            print(f"Pausing music. Is playing: {vc.is_playing() if vc else False}")
            if vc and vc.is_playing():
                vc.pause()
            else:
                print("Nothing is playing, cannot pause.")

    # Resumes paused music
    async def resume_music(self):
        async with vc_lock:
            if vc and vc.is_paused():
                vc.resume()

    # Stops the currently playing music
    async def stop_music(self):
        global paused_file, paused_position, current_file
        async with vc_lock:
            if vc:
                if vc.is_playing():
                    vc.stop()
                while not file_queue.empty():
                    file_queue.get()
                paused_file = None
                paused_position = 0
                current_file = None
        self.update_stop_button_state()
        self.update_queue_display()
    
    # Skips to next track 
    async def skip_to_next(self):
        async with vc_lock:
            if vc and vc.is_playing():
                vc.stop()
                while vc.is_playing():  # Wait for the voice client to stop playing audio
                    await asyncio.sleep(0.1)
        await self.play_next()
        self.update_stop_button_state()
    
    # Opens a file dialog to select a music file and adds it to the queue
    def pick_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "MP3 files (*.mp3);;All Files (*)")
        if file_path:
            self.add_to_queue(file_path)
    
    # Adds a file to the music queue
    def add_to_queue(self, file_path):
        print(f"🎶 Adding to queue: {file_path}")
        file_queue.put(file_path)
        self.update_queue_display()
        self.update_stop_button_state()
        if not vc or not vc.is_playing():
            asyncio.run_coroutine_threadsafe(self.play_next(), bot.loop)
             
    # Updates the queue display in the GUI
    def update_queue_display(self):
        self.queue_list.clear()
        queue_list = list(file_queue.queue)
        for i, item in enumerate(queue_list):
            item_display = QListWidgetItem(f"{i+1}: {item}")
            if i == 0 and vc and vc.is_playing():
                item_display.setForeground(QColor("green"))
            elif i == 1:
                item_display.setForeground(QColor("orange"))
            self.queue_list.addItem(item_display)

    # Assigns a sound to a quick sound button
    def assign_sound(self, button_index):
        button = self.quick_buttons[button_index]
        file_path, _ = QFileDialog.getOpenFileName(self, f"Select Sound for {button.text()}", "", "MP3 files (*.mp3);;All Files (*)")
        if file_path:
            button.setText(os.path.basename(file_path))
            save_quick_play_file(f"Quick Sound {button_index}", file_path)

    # Pauses the current music to play a quick sound
    async def pause_current_music(self):
        global paused_file, paused_position, start_time
        async with vc_lock:
            if vc and vc.is_playing():
                paused_file = current_file
                paused_position = time.time() - start_time
                vc.stop()

    # Resumes the paused music after a quick sound finishes
    async def resume_current_music(self):
        global paused_file, paused_position, start_time, music_volume
        async with vc_lock:
            if paused_file:
                while vc.is_playing():
                    await asyncio.sleep(0.1)
                original_source = discord.FFmpegPCMAudio(paused_file, before_options=f"-ss {paused_position}")
                volume_source = discord.PCMVolumeTransformer(original_source, volume=music_volume)
                vc.play(volume_source, after=self.after_playing)
                start_time = time.time() - paused_position
                paused_file = None
                paused_position = 0
        self.update_stop_button_state()

    # Plays a quick sound with volume control
    async def play_quick_sound_coroutine(self, sound_file):
        global quick_sound_volume, is_playing_quick_sound, paused_file, paused_position
        async with vc_lock:
            if vc and vc.is_playing():
                paused_file = current_file
                paused_position = time.time() - start_time
                vc.stop()  # Stop the current music
            is_playing_quick_sound = True
            original_source = discord.FFmpegPCMAudio(sound_file)
            volume_source = discord.PCMVolumeTransformer(original_source, volume=quick_sound_volume)
            if vc:
                vc.play(volume_source, after=lambda e: asyncio.run_coroutine_threadsafe(self.resume_music_after_quick_sound(e), bot.loop))
            else:
                print("Not connected to voice.")
    
    # Resumes track after quick sound has played
    async def resume_music_after_quick_sound(self, error):
        global is_playing_quick_sound, paused_file, paused_position, start_time, music_volume
        async with vc_lock:
            is_playing_quick_sound = False
            if error:
                print(f"Quick sound playback error: {error}")
            if paused_file:
                if not vc:
                    await self.connect_to_voice_async()
                while vc.is_playing():
                    await asyncio.sleep(0.1)
                original_source = discord.FFmpegPCMAudio(paused_file, before_options=f"-ss {paused_position}")
                volume_source = discord.PCMVolumeTransformer(original_source, volume=music_volume)
                vc.play(volume_source, after=self.after_playing)
                start_time = time.time() - paused_position
                paused_file = None
                paused_position = 0

     # Handles playing a quick sound when a button is clicked
    def play_quick_sound(self, button_index):
        button = self.quick_buttons[button_index]
        sound_file = load_quick_play_files().get(f"Quick Sound {button_index}")
        if sound_file:
            print(f"🎶 Playing assigned sound: {sound_file}")
            asyncio.run_coroutine_threadsafe(self.pause_current_music(), bot.loop)
            asyncio.run_coroutine_threadsafe(self.play_quick_sound_coroutine(sound_file), bot.loop)
        else:
            self.prompt_assign_sound(button_index)

    # Prompts the user to assign a sound to a quick sound button
    def prompt_assign_sound(self, button_index):
        button = self.quick_buttons[button_index]
        response = QMessageBox.question(
            self,
            "No Sound Assigned",
            f"No sound is currently assigned to {button.text()}. Would you like to assign one now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if response == QMessageBox.StandardButton.Yes:
            self.assign_sound(button_index)

     # Plays the next song in the queue
    async def play_next(self):
        global current_file, start_time, music_volume
        async with vc_lock:
            if vc is not None and not file_queue.empty():
                current_file = file_queue.get()
                original_source = discord.FFmpegPCMAudio(current_file)
                volume_source = discord.PCMVolumeTransformer(original_source, volume=music_volume)
                if not vc.is_playing():  # Check if the voice client is not already playing audio
                    vc.play(volume_source, after=self.after_playing)
                    start_time = time.time()
                    print(f"Playing next track: {current_file}")
                else:
                    print("Already playing audio, skipping...")
            else:
                print("No more tracks in the queue.")
        self.update_stop_button_state()
        self.update_queue_display()

    def after_playing(self, error):
        global is_playing_quick_sound
        if error:
            print(f"Playback stopped with error: {error}")
        if not is_playing_quick_sound:  # Only proceed to next track if not a quick sound
            asyncio.run_coroutine_threadsafe(self.play_next(), bot.loop)
        else:
            print("Quick sound finished, not advancing queue.")

    # Updates the music volume based on the slider
    def update_music_volume(self):
        global music_volume
        music_volume = self.music_volume_slider.value() / 100
        asyncio.run_coroutine_threadsafe(self.set_music_volume(music_volume), bot.loop)

    # Updates the quick sound volume based on the slider
    def update_quick_sound_volume(self):
        global quick_sound_volume
        quick_sound_volume = self.quick_sound_volume_slider.value() / 100

    # Sets the volume of the currently playing music
    async def set_music_volume(self, new_volume):
        async with vc_lock:
            if vc and vc.source:
                vc.source.volume = new_volume
    # Handles the stop button 
    def update_stop_button_state(self):
        is_enabled = vc and (vc.is_playing() or not file_queue.empty())
        self.stop_button_signal.emit(is_enabled)
    # Handles closing the application window
    def closeEvent(self, event):
        event.accept()
# Main function to start the application
def main():
    import sys
    app = QApplication(sys.argv)
    bot_thread = BotThread()
    main_window = MainWindow(bot_thread)
    bot_thread.start()
    main_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()