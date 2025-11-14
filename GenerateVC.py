#!/usr/bin/env python3

from azure.cognitiveservices.speech import AudioDataStream, SpeechConfig, SpeechSynthesizer, SpeechSynthesisOutputFormat
from azure.cognitiveservices.speech.audio import AudioOutputConfig
import argparse
import os
import sounddevice as sd
import soundfile as sf
import time
    
# Generates the .wav file header for a given set of parameters
def generate_wav_header(sample_rate, bits_per_sample, channels, datasize, formattype):
    # (4byte) Marks file as RIFF
    o = bytes("RIFF", 'ascii')
    # (4byte) File size in bytes excluding this and RIFF marker
    o += (datasize + 36).to_bytes(4, 'little')
    # (4byte) File type
    o += bytes("WAVE", 'ascii')
    # (4byte) Format Chunk Marker
    o += bytes("fmt ", 'ascii')
    # (4byte) Length of above format data
    o += (16).to_bytes(4, 'little')
    # (2byte) Format type (1 - PCM)
    o += (formattype).to_bytes(2, 'little')
    # (2byte) Will always be 1 for TTS
    o += (channels).to_bytes(2, 'little')
    # (4byte)
    o += (sample_rate).to_bytes(4, 'little')
    o += (sample_rate * channels * bits_per_sample // 8).to_bytes(4, 'little')  # (4byte)
    o += (channels * bits_per_sample // 8).to_bytes(2,'little')               # (2byte)
    # (2byte)
    o += (bits_per_sample).to_bytes(2, 'little')
    # (4byte) Data Chunk Marker
    o += bytes("data", 'ascii')
    # (4byte) Data size in bytes
    o += (datasize).to_bytes(4, 'little')

    return o

parser = argparse.ArgumentParser(
    prog="GenerateVC.py",
    usage="%(prog)s [-options]",
    add_help=False,
    formatter_class=lambda prog: argparse.HelpFormatter(
    prog, max_help_position=45, width=100)
)
 
# Set options
options = parser.add_argument_group("options")
options.add_argument("--file", nargs="?", help="Vision Clip File", required=True)
options.add_argument("--record", help="The customer side is recorded using the microphone rather than TTS")

args = parser.parse_args()

#speech_config = SpeechConfig(subscription="aa4f5859d38548c58f6c6f10143ac481", region="eastus")
speech_config = SpeechConfig(subscription="5d0043a4a5e3454392a9ff0a5e984516", region="eastus")

# Note: if only language is set, the default voice of that language is chosen.
speech_config.speech_synthesis_language = "en-US" # e.g. "de-DE"
# The voice setting will overwrite language setting.
# The voice setting will not overwrite the voice element in input SSML.
speech_config.speech_synthesis_voice_name ="en-US-JennyNeural"

#audio_config = AudioOutputConfig(filename="file.wav")

#synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
#synthesizer.speak_text_async("A simple test to write to a file.")

ignore = True
fnum = 1
SoxURL = "sox-14.4.2/sox "
RecURL = "sox-14.4.2/rec "
PlayURL = "afplay "
#PlayURL = "sox-14.4.2/play "

    
vfile = open(args.file,"r")
for line in vfile:
      
  if ignore is True:
    if line.startswith('<ringback>'):
      ignore = False
      finalAudio = ' audio/ringback.wav '
  else:
    if line.startswith('<hangup>'):
      ignore = True
    else:
      if line.startswith('<backend>'):
        finalAudio += 'audio/backend.wav '
      elif line.startswith('<sendmail>'):
        finalAudio += 'audio/swoosh.wav '
      elif line.startswith('<transfer>'):
        finalAudio += 'audio/ringback.wav '
      elif line.startswith('<text>'):
        finalAudio += 'audio/text-received.wav '
      elif line.startswith('IVA'):
        ivr = line.split(':',1)
        print(line)
        text = ivr[1] 
        #ssml = '<speak version="1.0" xmlns="https://www.w3.org/2001/10/synthesis" xml:lang="en-US">' + text + '</speak>'
        ssml = text
        fn = str(fnum) + '.wav'
        audio_config = AudioOutputConfig(filename=fn)

        synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        synthesizer.speak_text_async(ssml)

        #Try sleeping to see if the audio file just needs some time to close
        time.sleep(2)

        os.system(PlayURL + fn)
        finalAudio += fn + ' '
        fnum = fnum + 1
      elif line.startswith('Caller'):
        caller = line.split(':',2)
        print(line)
        text = caller[2]
        fn = str(fnum) + '.wav'
        #Determine if the caller should be recorded with the microphone or generated with TTS
        if args.record is not None:
          print("Speak now")
          # Record 
          #command = RecURL + '--norm -b 16 -r 16000 ' + fn + ' silence -l 1 2 1% 1 3.0 1% '
          #print(command)
          #os.system(command)
          # Record for 10 seconds
          numsamples = int(caller[1]) * 16000
          myrecording = sd.rec(numsamples, samplerate=16000, channels=1)
          sd.wait()
           
          sf.write('tmp.wav', myrecording, 16000) 
          os.system(SoxURL + 'tmp.wav ' + fn + ' ')
          #os.system(SoxURL + 'tmp.wav ' + fn + ' echo 0.8 0.88 6 0.4 bandpass 1250 1500')
          #os.system(SoxURL + 'tmpn.wav -p synth whitenoise vol 0.005 | ' + SoxURL + "-m " + 'tmpn.wav - ' + fn)

              
        else:
          #ssml = '<speak version="1.0" xmlns="https://www.w3.org/2001/10/synthesis" xml:lang="en-US">' + '<voice name="en-US-ChristopherNeural">' + text + '</voice>' + '</speak>'
          ssml = text
            
          audio_config = AudioOutputConfig(filename=fn)

          synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
          synthesizer.speak_text_async(ssml)

        finalAudio += fn + ' '
        fnum = fnum + 1
            
    
os.system(SoxURL + finalAudio + ' vc.wav')      
vfile.close()
