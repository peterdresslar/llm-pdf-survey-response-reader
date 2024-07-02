# PDF Survey Processor
## Overview
This project is a Python-based tool designed to process PDF surveys and convert them into structured data. It uses computer vision and natural language processing techniques to extract information from scanned survey forms and output the results in a CSV format.
## Features

- Processes multi-page PDF surveys
- Handles surveys that span two pages
- Uses AI to interpret and extract survey responses
- Outputs results in a structured CSV format

## Requirements

Python 3.7+
Required Python packages (install via pip install -r requirements.txt):

- pandas
- PyMuPDF (fitz)
- anthropic
- python-dotenv

## Setup

- Clone this repository
- Install required packages: pip install -r requirements.txt
- Create a .env file in the project root and add your Anthropic API key: ANTHROPIC_API_KEY=your_api_key_here

## Usage
Run the script from the command line:
`python main.py path/to/your/survey.pdf --output output_file.csv`
Options:

-- output: Specify the name of the output CSV file (default: processed_survey_data.csv)

## How it Works

- The script converts each page of the PDF to an image.
- Each image is processed using the Anthropic API to extract survey responses.
- Responses from pairs of pages are combined to form complete survey entries.
- The data is structured into a pandas DataFrame and output as a CSV.

## Limitations

- Currently assumes each survey spans exactly two pages
- May not handle PDFs with odd numbers of pages gracefully
- Was coded almost entirely by Claude

## Future Improvements

- Flexible Page Handling: Implement logic to handle surveys that span variable numbers of pages.
- Error Handling: Improve error handling for PDFs with odd numbers of pages or unexpected formats.
- Unit Testing: Develop a comprehensive suite of unit tests to ensure reliability across different inputs.
- Survey Length Parameter: Add a command-line argument to specify the expected number of questions in each survey.
- Progress Tracking: Implement a progress bar or more detailed logging for processing large PDFs.
- Data Validation: Add checks to ensure extracted data matches expected survey structure.
- GUI Interface: Develop a graphical user interface for easier use by non-technical users.

## Contributing
Contributions to improve the PDF Survey Processor are welcome. Please feel free to submit pull requests or open issues to discuss proposed changes or report bugs.

## License
MIT