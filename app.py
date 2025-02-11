import os
import re
import tempfile
import subprocess
import mido
import logging

from dotenv import load_dotenv
from flask import Flask, request, send_file, render_template, redirect, url_for, flash

# LangChain & OpenAI imports
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

###############################################################################
# Logging configuration
###############################################################################
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

###############################################################################
# Load environment variables & check for OpenAI key
###############################################################################
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.error("OPENAI_API_KEY is not set. Please set it in the .env file.")
    raise EnvironmentError("OPENAI_API_KEY is not set. Please set it in the .env file.")
logger.info("OPENAI_API_KEY successfully loaded.")

###############################################################################
# Utility functions
###############################################################################
def strip_markdown_code(text: str) -> str:
    """
    Remove markdown code fences from the text.
    For example, remove leading ```python and trailing ``` if present.
    """
    text = re.sub(r"^```[^\n]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return text

def get_midi_info(midi_path: str, user_tempo: int, user_measure_count: int) -> str:
    """
    Parse the MIDI file using mido and return a human-friendly summary.
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
            note_on_count = sum(1 for msg in track if msg.type == "note_on")
            note_off_count = sum(1 for msg in track if msg.type == "note_off")
            info_text += f"{track_name}:\n"
            info_text += f"  Note On events: {note_on_count}\n"
            info_text += f"  Note Off events: {note_off_count}\n"
            info_text += "  Preview messages:\n"
            for preview_msg in track[:5]:
                info_text += f"    {preview_msg}\n"
            info_text += "\n"
        return info_text
    except Exception as e:
        logger.error("Error reading MIDI file: %s", e)
        return f"Error reading MIDI file information: {e}"

###############################################################################
# Genre extra details
###############################################################################
genre_extra_details = {
    "Pop": "Typically features catchy melodies, simple chord progressions like I-V-vi-IV, and a clear, danceable rhythm.",
    "Rock": "Often uses power chords, a strong backbeat, and progressions such as I-IV-V. Electric guitar and drums are prominent.",
    "Hip Hop": "Features syncopated rhythms, sampled loops, and repetitive beats. Often uses minor scales and simple, repetitive chord patterns.",
    "Jazz": "Characterized by complex chords, improvisation, swing rhythms, and extended harmonies like 7th and 9th chords.",
    "Blues": "Utilizes the 12-bar blues progression, blue notes, and a soulful, expressive rhythm pattern.",
    "Classical": "Employs rich harmonic progressions, counterpoint, and structured forms with traditional chord movements.",
    "Electronic": "Often incorporates synthesized sounds, repetitive loops, and driving rhythms with modern production techniques.",
    "Country": "Features simple chord progressions (I-IV-V), twangy melodies, and a steady, straightforward rhythm.",
    "Reggae": "Uses off-beat rhythms, simple progressions, and a laid-back groove with emphasis on the backbeat.",
    "Folk": "Characterized by acoustic instrumentation, simple chord structures, and a narrative lyrical quality.",
    "Metal": "Often uses distorted guitars, aggressive rhythms, and complex, heavy chord progressions.",
    "Soul": "Features expressive melodies, rich chord progressions, and smooth rhythms with an emphasis on groove.",
    "R&B": "Incorporates smooth, soulful melodies, extended chords like 7ths and 9ths, and a laid-back, groovy rhythm.",
    "Latin": "Characterized by rhythmic complexity, syncopated beats, and lively chord progressions influenced by Latin styles.",
    "Punk": "Uses fast tempos, power chords, and simple, high-energy progressions with a raw, driving rhythm.",
    "Disco": "Features steady four-on-the-floor beats, syncopated basslines, and catchy, repetitive chord progressions.",
    "Funk": "Utilizes syncopated rhythms, groovy basslines, and extended chords with a strong emphasis on the downbeat.",
    "House": "Characterized by repetitive 4/4 beats, synthesized basslines, and simple, driving chord progressions.",
    "Techno": "Features electronic, repetitive beats, synthetic textures, and minimalistic chord progressions.",
    "Trance": "Uses layered synths, driving rhythms, and euphoric chord progressions with gradual builds and breakdowns.",
    "Ambient": "Focuses on atmospheric textures, minimalistic progressions, and slow-evolving rhythms.",
    "Ska": "Combines Caribbean influences with jazz and R&B elements, featuring off-beat rhythms and simple progressions.",
    "Gospel": "Characterized by uplifting chord progressions, strong vocal harmonies, and a soulful, expressive rhythm.",
    "World": "Incorporates diverse instruments and scales from various cultures, with unique rhythmic patterns and modal progressions.",
    "K-Pop": "Features a blend of pop, hip hop, and electronic elements with catchy hooks and polished, modern chord progressions.",
    "J-Pop": "Often includes bright melodies, eclectic influences, and polished production with standard pop progressions.",
    "EDM": "Utilizes electronic synthesizers, repetitive beats, and build-drop structures with energetic progressions.",
    "Indie": "Characterized by a mix of traditional and experimental sounds, often featuring unconventional chord progressions and rhythms.",
    "Alternative": "Blends elements from various genres with varied chord progressions and eclectic rhythmic patterns."
}

###############################################################################
# Flask App Initialization (Production Settings)
###############################################################################
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "replace_with_a_secure_random_key")
app.config['ENV'] = 'production'
app.config['DEBUG'] = False
app.config['TESTING'] = False

###############################################################################
# Initialize the LLM and PromptTemplate for MIDI generation
###############################################################################
llm = ChatOpenAI(model_name="gpt-4o", openai_api_key=openai_api_key)

midi_prompt = PromptTemplate(
    input_variables=[
        "genre", "extra_details", "tempo", "key_center", "scale_type", "mood",
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
- Ensure that all instrument patterns align properly with each measure to create a cohesive groove (avoid mismatched feels).

Details:
- Genre: {genre}
- Extra Genre Details: {extra_details}
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
   For each instrument, create a new MidiTrack and append messages to that track.
   Do not append individual MetaMessage objects directly to the file.
7. Use consistent rhythmic subdivisions for all instruments so the overall feel is coherent.
8. Use distinct channels and program changes for each track so that different instruments are recognized.
   - For example, channel 0 with program=0 for piano, channel 1 with program=32 for bass, and channel 9 for drums.
   - Insert a 'program_change' message at the beginning of each track for non-drum instruments.
   - For the drum track, simply set the channel to 9 (GM standard for percussion).
9. For each instrument, insert note events so that the total duration in each measure equals MEASURE_TICKS.
10. Save the MIDI file as "output.mid".

Output only the complete Python code (without markdown code fences).
"""
)

###############################################################################
# Routes & Handlers
###############################################################################
@app.route("/", methods=["GET", "POST"])
def index():
    # Default values
    default_genre = "Pop"
    default_tempo = 120
    default_key = "C"
    default_scale_type = "major"
    default_mood = "Bright and upbeat"
    default_parts_info = "1) Piano for chords\n2) Bass for rhythm\n3) Drums for beat"
    default_additional_details = "Provide any additional details as needed."
    default_measure_count = 16
    default_beat_subdivision = "1/4"

    genre_options = list(genre_extra_details.keys())

    if request.method == "POST":
        # Gather input from form
        genre = request.form.get("genre", default_genre)
        try:
            tempo = int(request.form.get("tempo", default_tempo))
        except ValueError:
            tempo = default_tempo
        key_center = request.form.get("key_center", default_key)
        scale_type = request.form.get("scale_type", default_scale_type)
        mood = request.form.get("mood", default_mood)
        parts_info = request.form.get("parts_info", default_parts_info)
        additional_details = request.form.get("additional_details", default_additional_details)
        try:
            measure_count = int(request.form.get("measure_count", default_measure_count))
        except ValueError:
            measure_count = default_measure_count
        beat_subdivision = request.form.get("beat_subdivision", default_beat_subdivision)

        extra_details = genre_extra_details.get(genre, "")
        logger.info("Received POST request with genre=%s, tempo=%d, key=%s", genre, tempo, key_center)

        # Run the LLM chain to generate the Python MIDI code
        chain = LLMChain(llm=llm, prompt=midi_prompt)
        try:
            generated_code_raw = chain.run({
                "genre": genre,
                "extra_details": extra_details,
                "tempo": tempo,
                "key_center": key_center,
                "scale_type": scale_type,
                "mood": mood,
                "parts_info": parts_info,
                "additional_details": additional_details,
                "measure_count": measure_count,
                "beat_subdivision": beat_subdivision
            })
            logger.info("LLM chain completed successfully.")
        except Exception as e:
            logger.error("Error while calling LLM chain: %s", e)
            flash(f"Error while calling LLM chain: {str(e)}", "error")
            return redirect(url_for("index"))

        generated_code = strip_markdown_code(generated_code_raw)
        logger.info("Generated code length: %d characters", len(generated_code))

        # Write the generated code to a temporary file and execute it
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp_file:
            tmp_file.write(generated_code.encode("utf-8"))
            tmp_file_name = tmp_file.name
        logger.info("Temporary file created: %s", tmp_file_name)

        execution_output = ""
        midi_file_path = "output.mid"

        try:
            out = subprocess.check_output(["python", tmp_file_name], stderr=subprocess.STDOUT)
            execution_output = out.decode("utf-8")
            logger.info("Execution output: %s", execution_output)
        except subprocess.CalledProcessError as e:
            execution_output = e.output.decode("utf-8")
            logger.error("Error executing generated code: %s", execution_output)
            flash("An error occurred while executing the generated code.", "error")

        midi_info = ""
        if os.path.exists(midi_file_path):
            midi_info = get_midi_info(midi_file_path, user_tempo=tempo, user_measure_count=measure_count)
            logger.info("MIDI file generated successfully.")
        else:
            logger.error("MIDI file was not generated.")

        return render_template(
            "result.html",
            generated_code=generated_code,
            execution_output=execution_output,
            midi_exists=os.path.exists(midi_file_path),
            midi_info=midi_info
        )
    return render_template(
        "index.html",
        genre_options=genre_options,
        default_genre=default_genre,
        default_tempo=default_tempo,
        default_key=default_key,
        default_scale_type=default_scale_type,
        default_mood=default_mood,
        default_parts_info=default_parts_info,
        default_additional_details=default_additional_details,
        default_measure_count=default_measure_count,
        default_beat_subdivision=default_beat_subdivision
    )

@app.route("/download_midi")
def download_midi():
    midi_file_path = "output.mid"
    if os.path.exists(midi_file_path):
        logger.info("Providing MIDI file for download.")
        return send_file(
            midi_file_path,
            as_attachment=True,
            download_name="output.mid",
            mimetype="audio/midi"
        )
    else:
        logger.error("No MIDI file found for download.")
        flash("No MIDI file found.", "error")
        return redirect(url_for("index"))

###############################################################################
# Run the Flask App
###############################################################################
if __name__ == "__main__":
    # In production, it is recommended to run with a WSGI server such as Gunicorn.
    # For example: gunicorn -w 4 -b :$PORT app:app
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=False)