#!/usr/bin/env python3

from typing import Sequence

import argparse
import os
import sounddevice as sd
import soundfile as sf
import time
import requests
import base64

parser = argparse.ArgumentParser(
    prog="GenerateVC.py",
#    usage="%(prog)s [-options]",
#    add_help=False,
#    formatter_class=lambda prog: argparse.HelpFormatter(
#        prog, max_help_position=45, width=100)
)

# Set options
# options = parser.add_argument_group("options")
parser.add_argument("--file", metavar="<path>", nargs="?", help="Path to Vision Clip File", required=True)
parser.add_argument("--record", metavar="1", help="The customer side is recorded using the microphone rather than TTS")

args = parser.parse_args()

# Note: if only language is set, the default voice of that language is chosen.
# speech_config.speech_synthesis_language = "en-US" # e.g. "de-DE"
# The voice setting will overwrite language setting.
# The voice setting will not overwrite the voice element in input SSML.
# speech_config.speech_synthesis_voice_name ="en-US-JennyNeural"
api_key = os.getenv('GOOGLE_API_KEY')
url = f'https://texttospeech.googleapis.com/v1beta1/text:synthesize?alt=json&key={api_key}'

ignore = True
fnum = 1
SoxURL = "sox-14.4.2/sox "
RecURL = "sox-14.4.2/rec "
PlayURL = "afplay "

vfile = open(args.file, "r")
for line in vfile:

    if ignore is True:
        if line.startswith('<ringback>'):
            ignore = False
            finalAudio = ' Audio/ringback.wav '
    else:
        if line.startswith('<hangup>'):
            ignore = True
        else:
            if line.startswith('<backend>'):
                finalAudio += 'Audio/backend.wav '
            elif line.startswith('<sendmail>'):
                finalAudio += 'Audio/swoosh.wav '
            elif line.startswith('<transfer>'):
                finalAudio += 'Audio/ringback.wav '
            elif line.startswith('<text>'):
                finalAudio += 'Audio/text-received.wav '
            elif line.startswith('IVA'):
                ivr = line.split(':', 1)
                print(line)
                text = ivr[1]
                # ssml = '<speak version="1.0" xmlns="https://www.w3.org/2001/10/synthesis" xml:lang="en-US">' + text + '</speak>'
                ssml = text
                fn = str(fnum) + '.wav'

                hheaders = {'content-type': 'application/json'}
                payload = {
                    "audioConfig": {
                        "audioEncoding": "LINEAR16",
                        "effectsProfileId": [
                            "telephony-class-application"
                        ],
                        "pitch": 0,
                        "speakingRate": 1
                    },
                    "input": {
                        "text": ssml
                    },
                    "voice": {
                        "languageCode": "en-US",
                        "name": "en-US-Studio-O"
                    }
                }

                r = requests.post(url, json=payload, headers=hheaders)
                # print(r.json())
                aJson = r.json()
                audioContent = aJson['audioContent']
                decoded_data = base64.b64decode(audioContent, ' /')
                with open(fn, 'wb') as pcm:
                    pcm.write(decoded_data)

                # Try sleeping to see if the audio file just needs some time to close
                time.sleep(1)

                os.system(PlayURL + fn)
                finalAudio += fn + ' '
                fnum = fnum + 1
            elif line.startswith('Caller'):
                caller = line.split(':', 2)
                print(line)
                text = caller[2]
                fn = str(fnum) + '.wav'
                # Determine if the caller should be recorded with the microphone or generated with TTS
                if args.record is not None:
                    print("Speak now")
                    # Record
                    # command = RecURL + '--norm -b 16 -r 16000 ' + fn + ' silence -l 1 2 1% 1 3.0 1% '
                    # print(command)
                    # os.system(command)
                    # Record for 10 seconds
                    numsamples = int(caller[1]) * 24000
                    myrecording = sd.rec(numsamples, samplerate=24000, channels=1)
                    sd.wait()

                    sf.write('tmp.wav', myrecording, 24000)
                    os.system(SoxURL + 'tmp.wav ' + fn + ' ')
                    # os.system(SoxURL + 'tmp.wav ' + fn + ' echo 0.8 0.88 6 0.4 bandpass 1250 1500')
                    # os.system(SoxURL + 'tmpn.wav -p synth whitenoise vol 0.005 | ' + SoxURL + "-m " + 'tmpn.wav - ' + fn)


                else:
                    # ssml = '<speak version="1.0" xmlns="https://www.w3.org/2001/10/synthesis" xml:lang="en-US">' + '<voice name="en-US-ChristopherNeural">' + text + '</voice>' + '</speak>'
                    ssml = text

                    # audio_config = AudioOutputConfig(filename=fn)

                    # synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
                    # synthesizer.speak_text_async(ssml)
                    text_to_wav("en-US-Studio-M", ssml, fn)

                finalAudio += fn + ' '
                fnum = fnum + 1

os.system(SoxURL + finalAudio + ' vc.wav')
vfile.close()
