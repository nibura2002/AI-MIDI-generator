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
    # Remove leading markdown fence
    text = re.sub(r"^```[^\n]*\n", "", text)
    # Remove trailing markdown fence
    text = re.sub(r"\n```$", "", text)
    return text

def main():
    st.title("MIDI Generator")

    # Initialize ChatOpenAI
    llm = ChatOpenAI(
        model_name="gpt-4o",
        openai_api_key=openai_api_key,
    )

    # Define the prompt template for code generation
    code_prompt = PromptTemplate(
        input_variables=["user_instructions"],
        template="""
        You are an excellent Python programmer.
        Based on the user's request, generate a complete Python code.

        Request:
        {user_instructions}

        Output only the Python code.
        """
            )

    chain = LLMChain(llm=llm, prompt=code_prompt)

    # Text area for user instructions
    user_instructions = st.text_area(
        "Enter your Python code request:",
        value="Code that prints 'Hello from GPT' to the console"
    )

    if st.button("Generate & Execute Code"):
        with st.spinner("Generating code..."):
            generated_code = chain.run({"user_instructions": user_instructions})

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
            output = subprocess.check_output(["python", tmp_file_name], stderr=subprocess.STDOUT)
            st.success("Code executed successfully.")
            st.write("Execution Output:")
            st.text(output.decode("utf-8"))
        except subprocess.CalledProcessError as e:
            st.error("An error occurred while executing the code.")
            st.text(e.output.decode("utf-8"))

if __name__ == "__main__":
    main()