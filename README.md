# MIDI Generation

## Project overview
### Back groud of the project
- Common music generation AI can output completed form of songs. It is usefull in many situation, especially for non music producers.  
- However, for music producers, a completed song has no room for improvement and is difficult to handle as music material.
- I wanted an AI that could generate music materials in MIDI format, which are editable materials.

### Concept of the tool
- MIDI generation tool with Flask UI.
- Use a LLM (currently openai GPT) to understand the image of the song.
- Output python scrypt for midi generation based on the LLM interpretation of the song, also using a LLM.

## Running Locally

This project uses Docker to containerize the application. Follow these steps to build and run the app locally:

1. **Build the Docker Image**

   Open a terminal in the project root directory (where the `Dockerfile` is located) and run:

   ```bash
   docker build -t midi-generation .
   ```

2. **Run the Docker Container**

   Once the image is built, run a container by mapping port 5001 (the port Flask uses) to your host's port 8501:

   ```bash
   docker run --env-file .env -p 8501:5001 midi-generation
   ```

   Alternatively, you can specify each environment variable individually using the -e flag:

   ```bash
   docker run -e OPENAI_API_KEY=your_api_key_here -p 8501:5001 midi-generation
   ```

3. **Access the Application**

   Open your web browser and navigate to [http://localhost:8501](http://localhost:8501) to view the Flask app.

### Using Environment Variables

- **Local Development:**  
  If you use a `.env` file for local configuration, ensure that the file is listed in your `.dockerignore` so that sensitive information does not get included in the Docker image.

- **Production Deployment:**  
  When deploying to services like Cloud Run, inject the necessary environment variables through the platform’s configuration settings rather than including them in your Docker image.