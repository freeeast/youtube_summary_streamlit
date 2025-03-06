import json, os, toml
from openai import OpenAI
import streamlit as st

# Load API key from credentials.txt or secrets manager
file_path = 'credentials'
if os.path.exists(file_path):
    with open(file_path, 'r') as f:
        secrets = toml.load(f)
else:
    secrets = st.secrets


def answer(system_prompt, user_prompt, model_type="github"):
    if model_type == "github":
        print("Answer using Github API")
        endpoint = "https://models.inference.ai.azure.com"
        

        if 'GITHUB' not in secrets and 'GITHUB_API_KEY' not in secrets:
            # throw an error if the API key is not found
            raise ValueError("Github API key not found")
        else:
            token = secrets['GITHUB']['GITHUB_API_KEY'] 

    elif model_type == "openrouter":
        print("Answer using Openrouter API")
        endpoint="https://openrouter.ai/api/v1"
        if 'OPENROUTER' not in secrets and 'OPENROUTER_API_KEY' not in secrets['OPENROUTER']:
            # throw an error if the API key is not found
            raise ValueError("OpenRouter API key not found")
        else:
            token = secrets['OPENROUTER']['OPENROUTER_API_KEY']
    else:
        raise ValueError("Invalid API type")

    model_name = "gpt-4o-mini"

    client = OpenAI(
        base_url=endpoint,
        api_key=token,
    )

    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            }
        ],
        temperature=1.0,
        top_p=1.0,
        max_tokens=1000,
        model=model_name
    )

    return response.choices[0].message.content
    
        
# execute if the script is run directly
if __name__ == "__main__":
    # model_type = "openrouter"
    model_type = "github"
    result = answer("Answer in chinese", "What is the capital of France?", model_type)
    print(result)

