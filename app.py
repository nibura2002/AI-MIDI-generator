import os
import re
import streamlit as st
import subprocess
import tempfile
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

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


def main():
    st.title("AI MIDI Generator")

    st.write(
        "Enter your song image details below. These details will be used to generate Python code "
        "(using the mido library) that creates a MIDI file matching your description.")

    # User inputs for song details
    genre = st.text_input("Genre", value="Pop")
    tempo = st.number_input(
        "Tempo (BPM)",
        min_value=50,
        max_value=300,
        value=120)
    key_center = st.selectbox(
        "Key",
        options=[
            "C",
            "D",
            "E",
            "F",
            "G",
            "A",
            "B"])
    scale_type = st.selectbox("Scale Type", options=["major", "minor"])
    mood = st.text_input("Mood", value="Bright and upbeat")
    parts_info = st.text_area(
        "Parts Information",
        value="1) Piano for chords\n2) Bass for rhythm\n3) Drums for beat")
    additional_details = st.text_area(
        "Additional Details",
        value="Provide any additional details as needed.")
    measure_count = st.number_input(
        "Number of Measures",
        min_value=1,
        max_value=100,
        value=16)
    beat_subdivision = st.selectbox(
        "Main Beat Subdivision",
        options=["1/4", "1/8", "1/16", "3/4", "6/8"],
        index=0
    )

    # Define the prompt template for generating MIDI code with consistency
    # checks
    midi_prompt = PromptTemplate(
        input_variables=[
            "genre", "tempo", "key_center", "scale_type", "mood",
            "parts_info", "additional_details", "measure_count", "beat_subdivision"
        ],
        template="""
You are an excellent musician and Python programmer.
Based on the following song description, generate a complete Python code that uses the mido library to create a MIDI file.
All instrument parts must adhere to the same time signature. Compute the measure duration as follows:
- Define a constant TICKS_PER_BEAT (e.g., 480).
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
7. For each instrument, insert note events so that the total duration in each measure equals MEASURE_TICKS.
8. Save the MIDI file as "output.mid".

Output only the complete Python code (without markdown code fences).
"""
    )

    # Initialize ChatOpenAI for GPT queries
    llm = ChatOpenAI(
        model_name="gpt-4o",
        openai_api_key=openai_api_key,
    )

    # Set up the LLMChain with the prompt template
    chain = LLMChain(llm=llm, prompt=midi_prompt)

    if st.button("Generate & Execute MIDI Code"):
        with st.spinner("Generating MIDI..."):
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

        st.write("### Generated Code:")
        st.code(generated_code, language="python")

        # Remove markdown code fences if present
        cleaned_code = strip_markdown_code(generated_code)

        # Write the cleaned code to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp_file:
            tmp_file.write(cleaned_code.encode("utf-8"))
            tmp_file_name = tmp_file.name

        # Execute the generated code using a subprocess
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
                st.download_button(
                    label="Download Generated MIDI File",
                    data=f,
                    file_name="output.mid",
                    mime="audio/midi"
                )
        else:
            st.error(
                "MIDI file 'output.mid' was not found. Please check the generated code.")


if __name__ == "__main__":
    main()
