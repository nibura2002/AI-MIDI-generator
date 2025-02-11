# MIDI Generation

## Project overview
### Back groud of the project
- Common music generation AI can output completed form of songs. It is usefull in many situation, especially for non music producers.  
- However, for music producers, a completed song has no room for improvement and is difficult to handle as music material.
- I wanted an AI that could generate music materials in MIDI format, which are editable materials.

### Concept of the tool
- MIDI generation tool with streamlit UI.
- Use a LLM (currently openai GPT) to understand the image of the song.
- Output python scrypt for midi generation based on the LLM interpretation of the song, also using a LLM.