import sys

def scrub_xa0_from_file(input_filepath, output_filepath):
    """
    Reads a text file, removes all instances of '\xa0', and writes the
    cleaned content to a new file.

    Args:
        input_filepath (str): The path to the input text file.
        output_filepath (str): The path to the output cleaned text file.
    """
    try:
        with open(input_filepath, 'r', encoding='utf-8') as infile:
            content = infile.read()

        cleaned_content = content.replace('\xa0', '')  # Replace with a regular space

        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(cleaned_content)

        print(f"Successfully scrubbed '\\xa0' from '{input_filepath}' and saved to '{output_filepath}'.")

    except FileNotFoundError:
        print(f"Error: The file '{input_filepath}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if (len(sys.argv) < 3):
        print("Usage: scrub_text <inputfilename> <outputfilename>")
        exit(1)
    
    scrub_xa0_from_file(sys.argv[1], sys.argv[2])
