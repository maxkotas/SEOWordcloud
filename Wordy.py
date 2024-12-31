import requests
from bs4 import BeautifulSoup
from googlesearch import search
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import re
from openai import OpenAI
import subprocess

MY_API_KEY = ""

# Set your OpenAI API key here
client = OpenAI(api_key="MY_API_KEY")

def get_text_from_url(url):
    """Fetch and extract text content from a URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=" ")
        return text
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return ""

def process_text(text):
    """Clean and tokenize text."""
    words = re.findall(r'\b\w+\b', text.lower())
    stop_words = set([
        "the", "and", "to", "of", "in", "a", "is", "for", "on", "it", "that",
        "with", "as", "by", "at", "this", "an", "be", "from", "are", "was", "or",
        "not", "but", "can", "has", "have", "you", "will", "your", "about", "which",
        "we", "all", "their", "more", "also", "its", "one", "so", "if", "when",
        "they", "how", "some", "other", "what", "there", "such", "who", "these"
    ])
    words = [word for word in words if word not in stop_words and len(word) > 2]
    return words

def generate_wordcloud(word_freq):
    """Generate and display a word cloud based on a word frequency dictionary."""
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate_from_frequencies(word_freq)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

def send_to_openai_api(text):
    """
    Send text to the GPT model using the OpenAI API, prompting it to generate
    a LaTeX document comparing the user's website content vs the top 10 results.
    """
    try:
        print("Sending data to OpenAI API...")
        prompt_content = (
            r"""You are a LaTeX generator. Your task is to analyze the following content for SEO insights and generate a fully compilable LaTeX document. 
Compare **MY WEBSITE CONTENT** against **TOP 10 COMPETITOR WEBSITES** to identify strengths, weaknesses, and opportunities. 
Do not add anything besides the LaTeX document, and ensure the response starts with \documentclass and includes \begin{document} and \end{document}. 
Make each suggestion highly specific to the keywords, referencing differences between my website and competitor content.

The LaTeX document must include:

\section{Introduction}  
Summarize the overall topic and intent of both my website and the competitor content.  
Highlight the primary keywords and themes.  

\section{Keyword Analysis}  
List the top keywords and phrases with their frequency of occurrence across all content.  
Suggest potential long-tail keywords for optimization.  

\section{Content Gaps and Recommendations}  
Identify gaps in both my website and competitor content.  
Suggest additional topics, keywords, or sections to improve SEO.  

\section{Competitor Insights}  
Analyze how the competitor content is structured and any standout SEO strategies.  
Highlight opportunities where my website can outperform them.  

\section{Technical SEO Suggestions}  
Offer technical improvements (e.g., meta descriptions, internal links).  
Suggest ways to enhance readability or accessibility.  

\section{Conclusion}  
Summarize the key takeaways for improving SEO and content quality.

Rules for Output:
1) Do not include Markdown formatting (```latex, ```, or any other code block markers).  
2) Ensure all LaTeX commands are syntactically correct and follow the required structure.  
3) Start with \documentclass and include all required sections.  
4) Do not include any explanation, comments, or text outside the LaTeX document.

Here is the content to analyze:
"""
            + text
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "assistant",
                    "content": prompt_content
                }
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Failed to send data to OpenAI API: {e}")
        return ""

def compile_latex_to_pdf(latex_code, output_filename):
    """
    Compile LaTeX code to a PDF file.
    
    Args:
        latex_code (str): The LaTeX code as a string.
        output_filename (str): The desired output PDF filename.
    """
    temp_tex_file = "temp.tex"

    # Write the LaTeX code to a temporary .tex file
    with open(temp_tex_file, "w") as f:
        f.write(latex_code)
    
    # Run pdflatex to compile the LaTeX file into a PDF
    try:
        process = subprocess.Popen(
            ["pdflatex", temp_tex_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Stream output line by line
        for line in process.stdout:
            print(line, end="")
        
        process.wait()
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, "pdflatex")
        
        # Move the compiled PDF to the desired output file name
        compiled_pdf = temp_tex_file.replace(".tex", ".pdf")
        subprocess.run(["mv", compiled_pdf, output_filename], check=True)
        print(f"\nPDF compiled and saved as {output_filename}")
    except subprocess.CalledProcessError as e:
        print("An error occurred during LaTeX compilation.")
        if e.stderr:
            print(e.stderr.decode())
    finally:
        # Clean up auxiliary files
        for ext in [".aux", ".log", ".tex"]:
            try:
                subprocess.run(["rm", temp_tex_file.replace(".tex", ext)], check=False)
            except Exception as cleanup_error:
                print(f"Failed to remove {ext} file: {cleanup_error}")

def main():
    my_website_url = input("Enter your website URL: ").strip()
    keyword = input("Enter the keyword to search for: ").strip()
    
    print("Fetching and processing MY WEBSITE content...")
    my_website_text = get_text_from_url(my_website_url)
    my_website_words = process_text(my_website_text)

    print(f"\nGathering top 10 Google results for '{keyword}' (excluding your own site if it appears)...")
    top_urls = search(keyword, num_results=10)

    competitor_texts = []
    competitor_text_combined = ""
    
    print("\nFetching and processing COMPETITOR content...")
    for url in top_urls:
        # Skip if the result is the user's own URL
        if url.strip("/") == my_website_url.strip("/"):
            continue
        print(f"Processing {url}")
        text = get_text_from_url(url)
        processed = process_text(text)
        competitor_texts.extend(processed)
        competitor_text_combined += text + "\n\n"

    all_text = my_website_text + "\n\n" + competitor_text_combined
    # Create frequency distributions for the combined text
    word_freq = Counter(process_text(all_text))

    print("\nGenerating word cloud from all content (my website + competitors)...")
    generate_wordcloud(word_freq)

    print("\nSending combined content to OpenAI API for analysis...")
    openai_response = send_to_openai_api(all_text)
    print("\nGPT Analysis (LaTeX output):\n", openai_response)

    output_filename = "seo_comparison_output.pdf"
    compile_latex_to_pdf(openai_response, output_filename)

if __name__ == "__main__":
    main()