import os
import speech_recognition as sr
import subprocess

def speak(text):
    os.system(f'termux-tts-speak "{text}"')

def record_audio():
    subprocess.run(["termux-microphone-record", "-l", "5", "-f", "input.wav"])

def convert_audio():
    subprocess.run(["ffmpeg", "-y", "-i", "input.wav", "input_converted.wav"])

def recognize_speech():
    r = sr.Recognizer()
    with sr.AudioFile("input_converted.wav") as source:
        audio = r.record(source)
    try:
        return r.recognize_google(audio, language='hi-IN')
    except sr.UnknownValueError:
        return "माफ़ कीजिए, मैं समझ नहीं पाया।"
    except sr.RequestError:
        return "नेटवर्क समस्या है।"

def get_response(user_input):
    user_input = user_input.lower()

    if "तुम कौन हो" in user_input or "tum kon ho" in user_input:
        return "मैं Friday हूँ, आपका स्मार्ट सहायक।"
    elif "तुम्हें किसने बनाया" in user_input or "kisne banaya" in user_input:
        return "मुझे Miraz Sir ने बनाया है।"
    elif "कैसे हो" in user_input or "kaisa hai" in user_input:
        return "मैं अच्छा हूँ, धन्यवाद।"
    else:
        return f"आपने कहा: {user_input}"

# Main loop
while True:
    speak("मैं सुन रहा हूँ, बोलिए")
    record_audio()
    convert_audio()
    user_input = recognize_speech()
    print("🧑‍💬 आपने कहा:", user_input)
    response = get_response(user_input)
    print("🤖 Friday:", response)
    speak(response)

    if "बंद हो जाओ" in user_input or "band ho jao" in user_input:
        break
