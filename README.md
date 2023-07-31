# VisionClip Generator

## Pre-requisites

To run the Vision Clip generator application first you need to install any prerequisites. In this directory you will find a file called requirements.txt. Please download that to the directory where you have expanded the zip file. Then run the following command:

```shell
pip3 install -r requirements.txt
```

## Configure API Key

```angular2html
export GOOGLE_API_KEY=<Google API Key>
```

## How to Execute the Script

From the command line:

```shell
GoogleGenerateVC.py --file ScriptName.txt --record 1
```

**Note**: in the above there are two _- signs before “file” and “record”. The script name is the name of the vision clip definition file (the script of the conversation). Without the record option the script is supposed to record both sides of the conversation in TTS, caller in one voice and the IVA in another. Currently I have not updated that code so it should fail, if for some reason we want to support this to make quick pro-types without re-recording every time I can update the script to support this. Currently we also would need to modify the python script to change the voice used in the demo.

Operation
After running the script it will iterate through the text file. When it hits an IVA line it will call the API to generate the audio from the text and then play the TTS through the laptop speakers. When it hits a User line it will print out what you are supposed to say and print out “Speak Now” when you are supposed to speak. The User audio is recorded through the laptop microphone. At the end of the call it will stitch all of the audio together in a file called “vc.wav”. 


>>>>>>> 2462758 (Minimal pieces)
