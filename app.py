import os
import streamlit as st
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

    # Set up the LLMChain with the defined prompt template
    chain = LLMChain(llm=llm, prompt=code_prompt)

    # Text area for user instructions
    user_instructions = st.text_area(
        "Enter your Python code request:",
        value="Code that prints 'Hello from GPT' to the console"
    )

    if st.button("Generate Code"):
        with st.spinner("Generating code..."):
            generated_code = chain.run(
                {"user_instructions": user_instructions})
        st.write("### Generated Code:")
        st.code(generated_code, language="python")


if __name__ == "__main__":
    main()
