import logging
import json
import pandas as pd
import base64
import anthropic
import re
import argparse
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF
import csv
from collections import OrderedDict

logger = logging.getLogger(__name__)

def natural_sort_key(s):
    return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', s)]

def extract_json_from_text(text):
    try:
        # Find the JSON object in the text
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            json_str = match.group(1)
            # Parse the JSON string
            json_data = json.loads(json_str)
            logger.debug("JSON successfully extracted and parsed")
            return json_data
        else:
            logger.error("No JSON object found in the text")
            return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {e}")
        logger.error(f"Content that failed to parse: {json_str}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while extracting JSON: {e}")
        return None

def convert_pdf_to_images(pdf_path):
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap()
        img = fitz.Pixmap(pix, 0) if pix.alpha else pix
        images.append(img)
    return images

def process_image_with_llm(image, client):
    img_bytes = image.tobytes("png")
    image_data = base64.b64encode(img_bytes).decode("utf-8")

    try:
        logger.debug("Attempting to create message...")
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Please analyze this survey image and return the results in the following JSON format:

{
  "question_number_subquestion": {
    "question": "question text or option text",
    "answer": boolean or string value
  }
}

For multiple choice or checkbox questions:
- Create a separate entry for each option
- Use 'question_number_optionnumber' as the key
- Set 'question' to the text of the option
- Set 'answer' to true if selected, false if not selected

For open-ended questions:
- Use 'question_number' as the key (no subquestion)
- Set 'question' to the full question text
- Set 'answer' to the exact text written

Important: Ensure the JSON is valid and can be parsed directly. You do not need to port in internal punctuation like quotation marks from the text--just skip them.

Example:
{
  "1_1": {
    "question": "Yes",
    "answer": true
  },
  "1_2": {
    "question": "No",
    "answer": false
  },
  "2": {
    "question": "What is your favorite color?",
    "answer": "Blue"
  }
}"""
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        }
                    ],
                }
            ],
        )
        logger.debug("Message created successfully.")
        
        if message.content and isinstance(message.content, list) and len(message.content) > 0:
            message_text = message.content[0]
            if message_text.type == "text":
                logger.info("Message content\n-----------------")
                logger.info(message_text.text)
                json_data = extract_json_from_text(message_text.text)
                if json_data:
                    return json_data
                else:
                    logger.error("Failed to extract JSON data from the message")
            else:
                logger.error("First content item is not of type 'text'")
        else:
            logger.error("Unexpected message content structure")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    
    return None

def process_pdf(pdf_path, client, output_file, survey_length):
    logger.info("Processing PDF...")
    images = convert_pdf_to_images(pdf_path)
    
    question_structure = []
    all_data = []
    
    for i in range(0, len(images), survey_length):
        survey_data = OrderedDict()
        for j in range(survey_length):
            if i + j < len(images):
                logger.info(f"Processing page {i+j+1}")
                try:
                    structured_data = process_image_with_llm(images[i+j], client)
                    survey_data.update(structured_data)
                    
                    # For the first survey, build the question structure
                    if i == 0:
                        question_structure.extend(structured_data.keys())
                except Exception as e:
                    logger.error(f"Error processing page {i+j+1}: {str(e)}")
        
        # After processing the first survey, sort and finalize the question structure
        if i == 0:
            question_structure = sorted(set(question_structure), key=natural_sort_key)
            logger.info(f"Determined question structure: {question_structure}")
        
        # Prepare row data based on the question structure
        row_data = [i // survey_length + 1]  # response_id
        for q in question_structure:
            row_data.append(survey_data.get(q, {}).get('answer', ''))
        
        all_data.append(row_data)
        
        logger.info(f"Successfully processed survey {i // survey_length + 1}")
    
    # Write data to CSV
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['response_id'] + question_structure)
        writer.writerows(all_data)
        logger.info(f"Data written to {output_file}")
    
    logger.info("PDF processing complete.")
    return output_file

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='survey_processing.log')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    load_dotenv()

    parser = argparse.ArgumentParser(description="Process a PDF survey and convert it to structured data.")
    parser.add_argument("pdf_path", help="Path to the PDF file to be processed")
    parser.add_argument("--output", default="processed_survey_data.csv", help="Output CSV file name (default: processed_survey_data.csv)")
    parser.add_argument("--survey-length", type=int, required=True, help="Number of pages per survey")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in .env file or environment variables")
        raise ValueError("ANTHROPIC_API_KEY not found in .env file or environment variables")

    logger.info(f"Using API key: {api_key[:4]}...{api_key[-4:]}")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    logger.info(f"Client API key: {client.api_key[:4]}...{api_key[-4:]}")
    logger.info(f"Client base URL: {client.base_url}")

    try:
        output_file = process_pdf(args.pdf_path, client, args.output, args.survey_length)
        logger.info(f"Processing complete. Data saved to '{output_file}'")
        
        # Optionally, read and display a few rows of the output file
        df = pd.read_csv(output_file, nrows=5)
        print("First few rows of the data:")
        print(df)
    except Exception as e:
        logger.exception("An error occurred during processing")
        raise

if __name__ == "__main__":
    main()