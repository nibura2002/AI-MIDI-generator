import os
import re
import streamlit as st
import subprocess
import tempfile
import base64
import mido
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import streamlit.components.v1 as components

# Load environment variables from the .env file
load_dotenv()

# Retrieve the API key from the environment
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("OPENAI_API_KEY is not set. Please set it in the .env file.")

def strip_markdown_code(text: str) -> str:
    """
    Remove markdown code fences from the text.
    For example, remove leading ```python and trailing ``` if present.
    """
    text = re.sub(r"^```[^\n]*\n", "", text)  # Remove leading fence
    text = re.sub(r"\n```$", "", text)          # Remove trailing fence
    return text

def get_midi_info(midi_path: str, user_tempo: int, user_measure_count: int) -> str:
    """
    Parse the MIDI file using mido and return a human-friendly summary.
    The summary includes:
      - The user-specified tempo and measure count.
      - The actual tempo from the first set_tempo message (if available).
      - The total length in seconds.
      - The number of tracks (interpreted as parts).
      - For each track, the count of note on/off events and a preview of the first few messages.
    """
    try:
        mid = mido.MidiFile(midi_path)
        actual_tempo = None
        for msg in mid.tracks[0]:
            if msg.type == "set_tempo":
                actual_tempo = mido.tempo2bpm(msg.tempo)
                break

        info_text = "MIDI File Information:\n"
        info_text += f"User Specified Tempo (BPM): {user_tempo}\n"
        if actual_tempo:
            info_text += f"Actual Tempo (BPM): {actual_tempo:.2f}\n"
        else:
            info_text += "Actual Tempo (BPM): Not found\n"
        info_text += f"User Specified Number of Measures: {user_measure_count}\n"
        info_text += f"Total Length: {mid.length:.2f} seconds\n"
        info_text += f"Number of Tracks (Parts): {len(mid.tracks)}\n\n"
        
        for i, track in enumerate(mid.tracks):
            track_name = getattr(track, "name", "") or f"Part {i+1}"
            info_text += f"{track_name}:\n"
            note_on_count = sum(1 for msg in track if msg.type == "note_on")
            note_off_count = sum(1 for msg in track if msg.type == "note_off")
            info_text += f"  Note On events: {note_on_count}\n"
            info_text += f"  Note Off events: {note_off_count}\n"
            info_text += "  Preview messages:\n"
            for msg in track[:5]:
                info_text += f"    {msg}\n"
            info_text += "\n"
        return info_text
    except Exception as e:
        return f"Error reading MIDI file information: {e}"

def main():
    st.title("AI MIDI Generator")

    # Place the input form in the sidebar
    st.sidebar.header("Song Details")
    genre = st.sidebar.text_input("Genre", value="Pop")
    tempo = st.sidebar.number_input("Tempo (BPM)", min_value=50, max_value=300, value=120)
    key_center = st.sidebar.selectbox("Key", options=["C", "D", "E", "F", "G", "A", "B"])
    scale_type = st.sidebar.selectbox("Scale Type", options=["major", "minor"])
    mood = st.sidebar.text_input("Mood", value="Bright and upbeat")
    parts_info = st.sidebar.text_area(
        "Parts Information",
        value="1) Piano for chords\n2) Bass for rhythm\n3) Drums for beat"
    )
    additional_details = st.sidebar.text_area(
        "Additional Details",
        value="Provide any additional details as needed."
    )
    measure_count = st.sidebar.number_input("Number of Measures", min_value=1, max_value=100, value=16)
    beat_subdivision = st.sidebar.selectbox(
        "Main Beat Subdivision",
        options=["1/4", "1/8", "1/16", "3/4", "6/8"],
        index=0
    )

    # Define the prompt template for generating MIDI code with consistency checks
    midi_prompt = PromptTemplate(
        input_variables=[
            "genre", "tempo", "key_center", "scale_type", "mood",
            "parts_info", "additional_details", "measure_count", "beat_subdivision"
        ],
        template="""
You are an excellent musician and Python programmer.
Based on the following song description, generate a complete Python code that uses the mido library to create a MIDI file.
All instrument parts must adhere to the same time signature. Compute the measure duration as follows:
- Define a constant TICKS_PER_BEAT (for example, 480).
- Determine the number of beats per measure based on the "Main Beat Subdivision" input:
    - If the value is "1/4", assume 4 beats per measure.
    - If the value is "3/4", assume 3 beats per measure.
    - If the value is "6/8", assume 3 beats per measure (since 6 eighth notes equal 3 quarter notes).
    - For values like "1/8" or "1/16", default to 4 beats per measure.
- Calculate MEASURE_TICKS = TICKS_PER_BEAT * (number of beats per measure).
Ensure that for every measure, the sum of note durations for each instrument equals MEASURE_TICKS.
Use MEASURE_TICKS consistently across all instrument parts.

Details:
- Genre: {genre}
- Tempo (BPM): {tempo}
- Key: {key_center}
- Scale: {scale_type}
- Mood: {mood}
- Parts Information: {parts_info}
- Additional Details: {additional_details}
- Number of Measures: {measure_count}
- Main Beat Subdivision: {beat_subdivision}

Requirements:
1. Import necessary libraries (such as mido, MidiFile, MidiTrack, MetaMessage, etc.).
2. Define a constant TICKS_PER_BEAT (for example, 480).
3. Determine the number of beats per measure based on the "Main Beat Subdivision" as described above, and calculate MEASURE_TICKS.
4. Create a new MIDI file.
5. Set the tempo using the provided BPM.
6. Create MIDI tracks for each instrument part (for example, piano, bass, and drums).
   For each instrument, create a new MidiTrack (e.g., piano_track = MidiTrack()) and append messages to that track. Do not append individual MetaMessage objects directly to the file.
7. For each instrument, insert note events so that the total duration in each measure equals MEASURE_TICKS.
8. Save the MIDI file as "output.mid".

Output only the complete Python code (without markdown code fences).
"""
    )

    # Initialize ChatOpenAI
    llm = ChatOpenAI(
        model_name="gpt-4o",
        openai_api_key=openai_api_key,
    )

    # Set up the LLMChain with the prompt template
    chain = LLMChain(llm=llm, prompt=midi_prompt)

    if st.sidebar.button("Generate & Execute MIDI Code"):
        with st.spinner("Generating MIDI code..."):
            generated_code = chain.run({
                "genre": genre,
                "tempo": tempo,
                "key_center": key_center,
                "scale_type": scale_type,
                "mood": mood,
                "parts_info": parts_info,
                "additional_details": additional_details,
                "measure_count": measure_count,
                "beat_subdivision": beat_subdivision
            })
        
        # Display generated code in an expandable/collapsible section
        with st.expander("View Generated Code"):
            st.code(generated_code, language="python")
        
        # Remove markdown code fences if present
        cleaned_code = strip_markdown_code(generated_code)
        
        # Write the cleaned code to a temporary file and execute it
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp_file:
            tmp_file.write(cleaned_code.encode("utf-8"))
            tmp_file_name = tmp_file.name
        
        try:
            output = subprocess.check_output(
                ["python", tmp_file_name], stderr=subprocess.STDOUT)
            st.success("MIDI code executed successfully.")
            st.write("Execution Output:")
            st.text(output.decode("utf-8"))
        except subprocess.CalledProcessError as e:
            st.error("An error occurred while executing the code.")
            st.text(e.output.decode("utf-8"))
            return

        # Check if the MIDI file was generated and offer it for download
        midi_file = "output.mid"
        if os.path.exists(midi_file):
            with open(midi_file, "rb") as f:
                midi_data = f.read()
            st.download_button(
                label="Download Generated MIDI File",
                data=midi_data,
                file_name="output.mid",
                mime="audio/midi"
            )
            # Display a human-friendly summary of the MIDI file information
            midi_info = get_midi_info(midi_file, user_tempo=tempo, user_measure_count=measure_count)
            st.subheader("MIDI File Information")
            st.text_area("Details", value=midi_info, height=300)
        else:
            st.error("MIDI file 'output.mid' was not found. Please check the generated code.")

if __name__ == "__main__":
    main()