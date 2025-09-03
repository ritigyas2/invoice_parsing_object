import logging
import os
import json
import requests
from factory import LLM

logger = logging.getLogger(__name__)

class OCRCheck:
    def __init__(self, client):
        self.client = client

    def ocr_local(self, path):
        uploaded_pdf = self.client.files.upload(
            file={"file_name": path, "content": open(path, "rb")},
            purpose="ocr"
        )
        signed_url = self.client.files.get_signed_url(file_id=uploaded_pdf.id)
        return self.client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "document_url", "document_url": signed_url.url}
        )

    def response_parser(self, data):
        text_blocks = [page.markdown for page in data.pages]
        return "\n".join(text_blocks)


class MistralParser:
    def __init__(self, env_path, prompt_file="prompt.md"):
        self.llm_obj = LLM(env_path)
        self.client = self.llm_obj.mistral_client
        self.ocr = OCRCheck(self.client)
        self.prompt_file = prompt_file

    def parse_and_generate_json(self, file_path):
        if file_path.endswith((".pdf", ".png", ".jpg", ".jpeg")):
            ocr_response = self.ocr.ocr_local(file_path)
        else:
            raise ValueError("Unsupported file format for OCR")

        extracted_text = self.ocr.response_parser(ocr_response)

        with open(self.prompt_file, "r") as file:
            prompt = file.read()

        final_prompt = f"{prompt}\n\n{extracted_text}"
        response = self.llm_obj.get_openai_response(final_prompt)

        # Try parsing JSON
        try:
            return json.loads(response)
        except Exception:
            return {"raw_output": response}

class LandingAIParser:
    def __init__(self):
        self.url = "https://api.va.landing.ai/v1/tools/agentic-document-analysis"
        self.headers = {
            "Authorization": "Basic Mmo5eTR3dTZhcGkxeGVjM2k2NWNjOlRPdmNoTHBJWTdNNWEyS25vUWpWZm5zdUVMRG9KRld2"
        }
        self.field_schema = {
       'type': 'object',
       'properties': {
        'Invoice date': {
            'type': 'string',
            'description': 'Date of the invoice - when the invoice was issued'
        },
        'Payment date': {
            'type': 'string',
            'description': 'Date of the payment - when the payment was made or due'
        },
        'Vendor id': {
            'type': 'string',
            'description': 'GSTIN of the vendor (other party, not Saarathi) - 15 digit alphanumeric code'
        },
        'Vendor name': {
            'type': 'string', 
            'description': 'Person who has initiated the transaction - same as beneficiary name in all invoices'
        },
        'Branch': {
            'type': 'string',
            'description': 'Shipping address branch location state (e.g., Chennai, Mumbai, Eluru)'
        },
        'Invoice type': {
            'type': 'string',
            'description': 'Type of invoice - mentions "proforma invoice" if present, otherwise empty'
        },
        'Base amount': {
            'type': 'string',
            'description': 'Base taxable amount before taxes (excluding CGST, SGST, IGST)'
        },
        'CGST': {
            'type': 'string',
            'description': 'Central Goods and Services Tax amount'
        },
        'SGST': {
            'type': 'string',
            'description': 'State Goods and Services Tax amount'
        },
        'IGST': {
            'type': 'string',
            'description': 'Integrated Goods and Services Tax amount'
        },
        'Total': {
            'type': 'string',
            'description': 'Total invoice amount including all taxes (CGST, SGST, IGST)'
        },
        'Name of the beneficiary': {
            'type': 'string',
            'description': 'Name of the person receiving the money'
        },
        'Beneficiary bank account number': {
            'type': 'string',
            'description': 'Bank account number of the beneficiary'
        },
        'IFSC code': {
            'type': 'string',
            'description': 'Indian Financial System Code - 11-character alphanumeric code for bank branch identification'
        },
        'Bank name': {
            'type': 'string',
            'description': 'Name of the bank where the beneficiary has the account'
        },
    },
    'required': ['Vendor name', 'Total', 'Base amount', 'Name of the beneficiary']
}

    def parse_and_generate_json(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "rb") as f:
            files = {"pdf": f}
            data = {"fields_schema": json.dumps(self.field_schema)}

            response = requests.post(
                self.url, files=files, data=data, headers=self.headers, timeout=120
            )
            response.raise_for_status()
            result_json = response.json()

            return result_json.get("data", {}).get("extracted_schema", {})


# ---------------- Final Hybrid Parser ----------------
class HybridInvoiceParser:
    def __init__(self, mistral_env_path=None, prompt_file="prompt.md"):
        self.mistral_env_path = mistral_env_path
        self.prompt_file = prompt_file
        self.landing_parser = LandingAIParser()
        self.mistral_parser = None

        # Try to initialize Mistral parser
        if mistral_env_path:
            try:
                self.mistral_parser = MistralParser(mistral_env_path, prompt_file)
                logger.info("Mistral parser initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Mistral parser: {e}")
                self.mistral_parser = None

    def parse_invoice(self, file_path):
        try:
            
            if self.mistral_parser:
                try:
                    logger.info("Trying Mistral Parser first...")
                    data = self.mistral_parser.parse_and_generate_json(file_path)
                    return {"success": True, "source": "mistral", "data": data}
                except Exception as e:
                    logger.error(f"Mistral parsing failed: {e}")
                    
    
            
            logger.info("Falling back to Landing.ai Parser...")
            data = self.landing_parser.parse_and_generate_json(file_path)
            return {"success": True, "source": "landing_ai", "data": data}
    
        except Exception as e:
            
            logger.exception("Invoice parsing failed completely")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }