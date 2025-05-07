# LINE Official Account Advanced Exam Assistant

This repository contains a Retrieval-Augmented Generation (RAG) + few-shot prompt solution for automatically answering LINE Official Account Advanced certification exam questions via a Gradio UI.

---

## Setup

1. **Create & activate an Anaconda environment**  
   ```bash
   conda create -n scrapeline-env python=3.11 -y
   conda activate scrapeline-env
   ```

2. **Install Python dependencies**
    ```bash
    pip install -r requirements.txt
    ```
3. **Install Playwright browser binaries**
    ```bash
    playwright install
    ```
4. **Add Google Vision credentials**

Save your Google Cloud Vision API JSON key file as
vision-api.json in the project root.



## Run the model on Ollama
The notebook uses a `MODEL` constant—make sure it matches the model you run below. I used `qwen3:14b-q4_K_M`:
    ```bash
    ollama run qwen3:14b-q4_K_M
    ```
If you want to use a different Ollama model, replace  
> `qwen3:14b-q4_K_M` above and update  
> `MODEL = "<your-model-name>"` in the notebook.

## Scrape the data from LINE Campus

You’ll need your LINE Business ID and saved cookies to pull down the official exam content:

### Save your cookies
1. **Run and login**
    ```bash
    python save_cookies.py 
    ```

2. **Scrape each course’s questions**
    ```bash
    python scrape_shiken.py --course basic
    python scrape_shiken.py --course advanced
    python scrape_manabu.py
    ```

## Few-Shot Prompt

RAG alone wasn't enough to pass the advance certification, so I injected a small set of questions and answers I knew (plus a brief explanation):

1. **Create a file** called `few_shots.py` next to your main script:

   ```python
   # few_shots.py

   SYSTEM_PROMPT = """\
   You are an expert on the LINE Official Account Advanced certification exam.
   Your task is to read each “question + 4 answer choices” and use ONLY the
   materials retrieved from the vector database to produce the correct answer.

   Output rules:
   1. If the question says “multiple answers,” select **all** correct choices.
      Otherwise select **exactly one**.
   2. Do not output just “A/B/C/D”; list the full text of each chosen option.
   3. Include a concise reason (≤ 50 characters).
   4. Strict format:

   Answer:
   - <correct choice 1>
   - <correct choice 2>   ← only one line if single-choice

   Reason:
   <very brief justification>
   """

   FEW_SHOTS = [
       (
           "…sample question text 1…",
           """Answer:
   - …correct option full text…

   Reason:
   …short justification…"""
       ),
       # …add 3–8 more high-value examples…
   ]

## Launch the Gradio UI

After completing all of the above steps:

```bash
jupyter lab         
```

Open notebook.ipynb.

Run all cells to build the vector DB and set up the chain.

In the final cell, execute demo.launch() (or run python app.py) to start the Gradio interface.

Navigate to http://0.0.0.0:7860, paste your exam question + answer choices, and click 解答する.








