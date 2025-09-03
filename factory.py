from dotenv import load_dotenv
import os
#from google import genai
from openai import OpenAI
import base64
from mistralai import Mistral

class Auth:
    def __init__(self,env_path):
        load_dotenv(dotenv_path=env_path)
        self.gemini_api_key=os.getenv("GEMINI")
        self.__openai_client=OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        #load_dotenv(dotenv_path=env_path)
        #self.__gemini_client = genai.Client(api_key=self.gemini_api_key)
        self.mistral_api_key=os.getenv("OCR")
        self.mistral_client=Mistral(api_key=self.mistral_api_key)

    def get_openai_client(self):
        return self.__openai_client
    
    # def get_gemini_client(self):
    #     return self.__gemini_client
    def get_mistral_client(self):
        return self.mistral_client


class LLM:
    def __init__(self,env_path):
        self.auth_obj=Auth(env_path)
        #self.gemini_client=self.auth_obj.get_gemini_client()
        self.openai_client=self.auth_obj.get_openai_client()
        self.mistral_client=self.auth_obj.get_mistral_client()
    def get_openai_response(self,prompt):
        response = self.openai_client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )
        return response.output_text

    def format_prompt(self,replacer,user_input,system_prompt,isPath=False):
        if(isPath==True):
            with open(system_prompt,'r') as f:
                system_prompt=f.read()
        system_prompt=system_prompt.replace(replacer,user_input)
        return system_prompt

    # def get_gemini_response(self,prompt):
    #     response = self.gemini_client.models.generate_content(
    #         model="gemini-2.5-flash",
    #         contents=prompt
    #     )
    #     return response.text

    def get_openai_response_with_image(self,prompt,image_path):
        def encode_image(image_path):
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")


        response = self.openai_client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "user",
                    "content": [
                        { "type": "input_text", "text": prompt },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{encode_image(image_path)}",
                        }
                    ]
                }
            ]
        )
        return response.output_text


    # # def get_gemini_response_with_image(self, prompt, image_path):
    #     """Send text prompt with image to Gemini"""
    #     import base64
        
    #     # Read and encode the image
    #     with open(image_path, "rb") as image_file:
    #         image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
    #     # Create multimodal content
    #     from google import genai
    #     contents = [
    #         {
    #             "role": "user",
    #             "parts": [
    #                 {"text": prompt},
    #                 {
    #                     "inline_data": {
    #                         "mime_type": "image/jpeg",
    #                         "data": image_data
    #                     }
    #                 }
    #             ]
    #         }
    #     ]
        
    # #     response = self.gemini_client.models.generate_content(
    # #         model="gemini-2.5-flash",
    # #         contents=contents
    # #     )
    # #     return response.text

