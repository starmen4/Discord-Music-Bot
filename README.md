# Discord-Bot
This is a discord music bot



# needed Dependencies

Python 3.8 or higher

Discord.py		-----		pip install discord.py

PyQt6			-----		pip install pyqt6

FFmpeg			-----		https://www.gyan.dev/ffmpeg/builds/ - release builds - ffmpeg-release-full.7z - 

for FFmpeg unzip the bin folder into a folder in your root directory called ffmpeg

you may also have to add it to Environment Variables under sysdm.cpl

to do this hit Win + r type in sysdm.cpl go to advanced - Environment Variables - System Variables - Path - Edit... New -   type in C:\ffmpeg\bin  

then reboot

You will need to open the bot to insert your Bot Token just edit with notepad and look for 

# Set up bot
TOKEN = "PUT TOKEN HERE"   make sure your put the token between "" 

# info
Regarding the quick files. the bot will create a text file in the root directory of where the bot is sitting. this file will point the bot to the quick files, if you want to change them just delete the corisponding line in the file. 

# running the bot
to run the bot place it in a folder, open CMD navigate to sed folder type in 		python DiscodMusicBox.py

I recommend making a quick start bat file and placing it on your desktop for ease of use.

the script looks something like this 

Echo off

cd\					<-- start by sending the script to the root directory

cd users				

cd user

cd OneDrive				<-- because windows is shit now.. 

cd Desktop

cd "Music Man Discord BOT"		<-- this is the folder the bot is located in if there is spaces in the folder name use "" around the folder name if it has spaces

python DiscodMusicBox_1.1.py		<-- command to start the bot

pause					<-- this prevents the script from closing prematurely 
