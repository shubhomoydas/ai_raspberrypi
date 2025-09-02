# README #

#### Hardware / Software
A little experiment with RaspberryPi and AI. Hardware used:
  - RaspberryPi 5
  - BuildHAT
  - Lego Motor

Software / AI:
  - TigerVNC (connect to Raspberry Pi)
  - Python 3.11
  - Claude (might use OpenAI GPT-4*) is being used for LLM completion -- an API key will be required
  - OpenAI models being used for text-to-speech and speech-to-text -- an API key will be required

I use a Macbook Pro for development, hence the commands and instructions are biased towards that.

Use the below command to get to the python shell:
```
export CLAUDE_API_KEY=<api_key> && export CLAUDE_API_URL=https://api.anthropic.com/v1/messages \
  && export CLAUDE_API_VER=2023-06-01 && export OPENAI_API_KEY=<api_key>; python
```

#### Python

```python

from buildhat import Motor

motor_a = Motor('A')

motor_a.run_for_seconds(5)

motor_a.run_for_seconds(5, speed=50)
motor_a.run_for_seconds(5, speed=-50, blocking=False)

motor_a.run_for_degrees(360, speed=None, blocking=False)

motor_a.run_to_position(degrees=180, speed=None, blocking=True, direction='shortest')

motor_a.run_for_degrees(-360)

motor_a.run_for_rotations(rotations=2, speed=None, blocking=False)

motor_a.set_default_speed(default_speed=50)

motor_a.start()

motor_a.stop()


def handle_motor(speed, pos, apos):
    """Motor data

    :param speed: Speed of motor
    :param pos: Position of motor
    :param apos: Absolute position of motor
    """
    print("Motor", speed, pos, apos)
    

for i in range(2):
    motor_a.run_for_rotations(rotations=2)
    motor_a.run_for_rotations(rotations=-2)


motor_a.when_rotated = handle_motor


i = 0
while i < 10:
    
    print("Position: ", motor_a.get_aposition())
    
    motor_a.run_for_seconds(5, speed=50)
    
    i += 1

```

#### shutdown raspberry pi
```
sudo shutdown -h now
```

```
cd /home/shubhomoydas/work/git/raspi

source /home/shubhomoydas/work/venv/python311_raspi/bin/activate

jupyter notebook --no-browser --port 8896
```

```
# sudo apt-get install libportaudio2

# pip3 install buildhat

# pip install sounddevice wavio scipy openai

# pip install jupyter
```

#### GUI

Use TigerVNCViewer to connect to Raspberry Pi UI.

```
ssh shubhomoydas@192.168.1.82

sudo raspi-config
```

*Use "Interface Options" to enable VNC*


### git

#### On office laptop, the below will fail because we have default ssh key configured for espressive bitbucket
#### git clone git@bitbucket.org:shubhomoy_das/raspi.git

#### the below should work on office laptop as well.
```
ssh-agent bash -c 'ssh-add /Users/shubhomoydas/.ssh/id_rsa_bitbucket_personal; git clone git@bitbucket.org:shubhomoy_das/raspi.git'

ssh-agent bash -c 'ssh-add /Users/shubhomoydas/.ssh/id_rsa_bitbucket_personal; git fetch'

ssh-agent bash -c 'ssh-add /Users/shubhomoydas/.ssh/id_rsa_bitbucket_personal; git push origin'
```

### Important links for help on audio
  - https://www.geeksforgeeks.org/python/create-a-voice-recorder-using-python/
  - https://platform.openai.com/docs/guides/text-to-speech
  - https://github.com/openai/openai-python/blob/main/src/openai/helpers/local_audio_player.py
  - https://raspberrypi.stackexchange.com/questions/7088/playing-audio-files-with-python
  - http://stackoverflow.com/questions/43941716/ddg#43950755


### setup for installing portaudio on OSX (required by pyaudio)
**IMPORTANT**: these are optional and should be run on Macbook to setup local development
```
brew install portaudio
brew install ffmpeg
python3 -m pip install --upgrade pip setuptools
python3 -m pip install pyaudio --global-option="build_ext" --global-option="-I/opt/homebrew/include" --global-option="-L/opt/homebrew/lib"
pip install pydub
```

### setup for playing audio on Raspberry Pi
**IMPORTANT**: these must be run ON THE Raspberry Pi
```
sudo apt-get install ffmpeg

sudo apt-get install portaudio19-dev

sudo apt-get install python3-dev

pip install pyaudio

pip install pydub pyaudio
```

### Setting up the python virtual env
**NOTE**: These should be run on the Raspberry PI
```
mkdir /home/shubhomoydas/work/venv

/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m venv ~/work/venv/python311_raspi

python3 -m venv /home/shubhomoydas/work/venv/python311_raspi

source ~/work/venv/python311_raspi/bin/activate

source /home/shubhomoydas/work/venv/python311_raspi/bin/activate
```
