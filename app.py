import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

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

    # Input field for user query
    user_prompt = st.text_input("Enter a question:")
    if st.button("Submit"):
        with st.spinner("Querying..."):
            response = llm(user_prompt)
        st.write("### Response:")
        st.write(response)

if __name__ == "__main__":
    main()