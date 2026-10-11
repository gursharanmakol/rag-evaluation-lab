# RAG Evaluation Lab: Six Escalated Answers

Support escalated six answers from TechNova's assistant this week, and the team lead wants to switch to a bigger model. Before anyone approves that, find out which answers actually failed and where, fix the failure that comes from the code, and prove the fix with the evaluation.

Set aside about 75 to 90 minutes. Your time will vary with your familiarity with Python projects, Git, and RAG.

## Who this is for

You should be comfortable with Python project work: navigating code you did not write, finding a function, reading short Python, making a small edit, rerunning the project, and reading basic error messages. You should also be familiar with Git, a terminal, and an editor or IDE.

You do **not** need production RAG experience, prior RAG debugging experience, advanced Python, vector database expertise, deep embedding knowledge, or an IDE debugger. Basic RAG awareness is enough.

## What you'll practice

This lab gives you practice working out where a RAG answer went wrong by reading recorded evidence instead of guessing. For each escalated answer you'll check the retrieved chunks first, then the prompt that was sent, then the answer, and stop at the first layer that failed. You'll fix the failure that comes from the code, confirm it with two evaluation checks, and add an evaluation question that fails on the original code and passes after your fix.

## What's in the lab

You get a small working copy of TechNova's support assistant. It answers customer questions from 9 help-center documents, split into 17 chunks. Alongside the code, you get two sets of cases.

| | What it is | What you use it for | Command |
| --- | --- | --- | --- |
| **Incidents I1 to I6** | Six customer conversations support escalated this week. Each has a trace recorded at the time, and a support note saying what happened to the customer. | Decide whether each answer actually failed, and if it did, find the first layer that failed. | `trace I1` |
| **Evaluation questions Q01 to Q10** | The team's regression test. Each question names the help-center chunk that should answer it. | See whether retrieval and prompt assembly work on the current code, and prove your fix. | `evaluate` |

The two sets answer different questions. The incidents show what customers actually got. The evaluation shows how the system behaves now, on questions with a known right chunk. It never calls a model, so it can't see an answer that ignored its evidence.

When the evaluation fails, the failing questions point at a problem in the system as it runs today. Part of your job is working out which incidents reflect the problem the evaluation exposes, and which failed for a different reason.

The lab never calls a model, so you don't need an API key.

## Your assignment

**TechNova support assistant: six escalated answers**

Support escalated six answers from the assistant this week. Some customers got a wrong answer. A complaint doesn't always mean the assistant was wrong, though. The team lead's proposal is to switch to a bigger model. Before anyone approves that, find out what actually went wrong.

1. **Check the system.** Run `evaluate`. Note which check fails and which questions cause it. Don't fix anything yet.
2. **Diagnose the incidents.** Run `trace` for each of I1 to I6. In `diagnosis.md`, write whether the answer actually failed, the first layer that failed, and one or two trace observations that show it.
3. **Write a regression question.** Add one question to `eval/questions.yaml` that reproduces the code-related failure. Run `evaluate` and confirm it fails. Don't reuse an incident question.
4. **Fix the code.** Make the smallest appropriate change.
5. **Prove it.** Run `evaluate` again. Your new question passes, and both checks say PASS.

Don't change the existing evaluation questions, their expected chunks, or the context budget.

**What you'll have when you're done**

- `diagnosis.md` with all six incidents filled in, each with one or two trace observations as evidence
- one new question in `eval/questions.yaml` that failed before your change
- a small code change
- an `evaluate` run where your question passes and both checks say PASS

## How this system works

<details>
<summary>Reading a trace</summary>

Each trace follows one question through the system, in the same order as the `trace` output. Watch where the chunk that should have answered goes.

1. **Candidates by similarity.** The question is compared with all 17 chunks, using a small embedding model bundled with the lab, and the chunks are ranked by similarity.
2. **After reranking.** A keyword reranker adds a boost for words the question shares with a chunk, and reorders the results.
3. **Kept (top 3).** The first 3 results are kept for the answer.
4. **Prompt assembly.** The kept chunks are added after any earlier conversation, within a 500-token context budget. Each chunk shows as reached or cut.
5. **Prompt sent to the model.** The exact text the model saw.
6. **Recorded answer.** What the assistant said, followed by the support note.

Sections 1 to 3 are the chunks check in the habit diagram on the lab page, 4 and 5 are the prompt check, and 6 is the answer check. `inspect` shows sections 1 to 4 for any question, run live on the current code. A trace shows what happened at the time. Your fix changes what the system would send next time, not the recorded answers.

Token counts come from the bundled Model2Vec potion-base-8M model's tokenizer. They're labeled "lab tokenizer" because a production model would count a little differently. The budget is a teaching constant, not a model limit.

</details>

<details>
<summary>The three layers, with an example</summary>

An answer can go wrong at three layers. Check them in this order and stop at the first one that failed.

| Layer | It failed when |
| --- | --- |
| Retrieval | The chunk that answers the question isn't in the kept results. |
| Assembly | The chunk was kept, but it didn't reach the prompt intact. |
| Generation | The right evidence was in the prompt, and the answer ignored it or claimed something the prompt doesn't support. |

If the right chunk reached the prompt and the answer matches it, nothing failed, even if the customer complained.

**Try the three checks on a made-up example.** It isn't one of the six incidents. A customer asks whether gift wrapping is free, and the assistant says no. The help center has a chunk saying gift wrapping is free on orders over 50 dollars.

1. **Chunks. Was the right chunk kept?** If the gift-wrapping chunk isn't in the kept results, retrieval failed. Stop there.
2. **Prompt. Did it reach the prompt intact?** If it was kept but cut before the prompt, assembly failed. Stop there.
3. **Answer. Does the answer follow it?** If it reached the prompt and the answer still says no, generation failed.

If the chunk reached the prompt and the order was under 50 dollars, "no" was the right answer, and nothing failed.

Same habit every time. Chunks, then prompt, then answer, and stop at the first check that fails.

</details>

<details>
<summary>Reading the evaluation</summary>

`evaluate` runs every evaluation question through the current code. Each row shows where the expected chunk landed in the ranked results (its position), whether that's in the first 3 and the first 10, its reciprocal rank, and how many kept chunks reached the prompt.

- **Expected.** The chunk that should answer the question.
- **Position.** Where that expected chunk ranked.
- **Top 3.** Whether the expected chunk is in the first 3 positions. These are the results the system keeps.
- **Top 10.** Whether the expected chunk appears in the first 10 ranked positions.
- **RR.** Reciprocal rank. It is `1 / position`, so position 1 is 1.00, position 2 is 0.50, and position 8 is 0.125.
- **Kept chunks in prompt.** How many of the kept chunks actually reached the prompt.

`recall@3`, `recall@10`, and `MRR` summarize ranking quality across all evaluation questions. You do not need to optimize those numbers directly in this lab; use them as evidence while diagnosing the failing questions.

Below the rows are two checks. Both must pass.

- **Retrieval check.** Every question's expected chunk is in the kept results.
- **Assembly check.** Every kept chunk reached the prompt intact. This must stay true whatever you change.

Read it top down. Start with the two checks at the bottom. Which check failed? Which questions caused it? Don't fix anything yet.

A failed retrieval check means at least one expected chunk didn't make the kept results. A passing assembly check means everything that was kept reached the prompt.

Later, you'll add one evaluation question of your own that reproduces the code-related failure, then rerun `evaluate` to prove your fix.

</details>


## Where things are

| Path | What it is |
| --- | --- |
| `lab.py` | The command-line tool you run |
| `corpus/` | The 9 help-center documents. Each `##` section is one chunk. |
| `src/corpus.py` | Loads the documents and splits them into chunks |
| `src/embed.py` | Loads the embedding model, embeds text, and counts tokens |
| `src/search.py` | Similarity search over the chunks |
| `src/rerank.py` | The keyword reranker |
| `src/pipeline.py` | Retrieval and prompt assembly, and the settings they use |
| `src/report.py` | Formats the command output |
| `eval/questions.yaml` | Evaluation questions and the chunk that should answer each one |
| `eval/metrics.py` | Computes positions, recall, MRR, and the two checks |
| `incidents/` | Six recorded conversations that support escalated |
| `diagnosis.md` | Where you write your findings |
| `CHANGES.md` | The changelog |
| `models/` | The bundled embedding model |
| `HINTS.md` | Three hints, one step at a time |
| `solution/` | The reference answer. Open it when you're done or truly stuck. |

## What you'll need

- **Python 3.12** (the project requires `>=3.12,<3.13`; tested on CPython 3.12.9)
- **Git** to clone the lab repository
- **A terminal** to run the lab commands (PowerShell, Terminal, or your editor's built-in terminal)
- **An editor or IDE** to read and change the code

`uv` is the recommended and tested way to run the lab. It can install Python 3.12 for you. You may also use your own activated Python 3.12 environment (venv, Conda, or an IDE interpreter) after installing `requirements.txt`.

## How you'll work

Open the entire lab folder in the editor or IDE you normally use. You may use its built-in terminal.

Run the lab commands in the terminal to reproduce the problem and investigate what is happening. Make the code change you think is needed, then run the commands again to verify your fix.

You'll also write short notes in `diagnosis.md`.

## Using AI tools

You may use AI for incidental technical help: environment or setup issues, terminal or path problems, Python syntax, understanding an error message, or editor and tool usage.

Please do not use AI to do the core diagnosis for you. Prompts like "Find the bug in this RAG system," "What line should I change?," "What is the correct fix?," or "Why is this evaluation failing?" remove the reasoning this lab is meant to practice.

## Setup

### 1. Check your setup

**Recommended (uv):**

```bash
git --version
uv --version
```

If both commands print a version, continue to step 2. If either command is not found, open the install steps below. You do not need to install Python yourself when using uv. uv installs Python 3.12 the first time you run the lab.

<details>
<summary>Need to install Git or uv?</summary>

Git: https://git-scm.com/downloads

uv for Windows PowerShell:

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

uv for macOS or Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen your terminal after installing uv. Then run the version checks again.

</details>

**Alternative (your own Python 3.12 environment):**

```bash
git --version
python --version
```

Confirm Python reports 3.12.x, then continue. If you are using your own activated Python environment, omit `uv run` and use `python lab.py ...`.

### 2. Get the lab and check it

**Recommended (uv):**

```bash
git clone https://github.com/gursharanmakol/rag-evaluation-lab.git
cd rag-evaluation-lab
uv run python lab.py check
```

The first run may take a few minutes while uv prepares Python and the dependencies. You're ready when the last line starts with `Ready.`

**Alternative (pip / venv / Conda / IDE interpreter):**

```bash
git clone https://github.com/gursharanmakol/rag-evaluation-lab.git
cd rag-evaluation-lab
pip install -r requirements.txt
python lab.py check
```

If `check` still does not pass after about 15 minutes, pause and re-check the Python version, Git, and install steps above before continuing.

## Commands

If you use your own Python environment instead of uv, drop `uv run` and use `python lab.py ...`.

```bash
uv run python lab.py evaluate
uv run python lab.py trace
uv run python lab.py inspect Q01
```

**When you run `evaluate`.** Don't try to fix anything yet. First look at the two checks at the bottom, note which one failed, and identify the questions that caused the failure. Use the rows above to see where each expected chunk ranked and whether the kept chunks reached the prompt.

| Command | What it shows |
| --- | --- |
| `uv run python lab.py check` | Python and package versions, the model, and counts of chunks, questions, and incidents |
| `uv run python lab.py evaluate` | One row per evaluation question, then the two checks |
| `uv run python lab.py trace` | The list of recorded incidents |
| `uv run python lab.py trace I1` | One incident's recorded trace: candidates by similarity, the order after reranking, the kept chunks, the prompt assembly, the full prompt, the recorded answer, and the support note |
| `uv run python lab.py inspect Q01` | The same first four sections for an evaluation question, run live on the current code |
| `uv run python lab.py inspect "your question"` | The same, for any question you type |
| `uv run python lab.py chunks` | Every chunk with its token count and heading |

## If you get stuck

Open `HINTS.md` and read one hint at a time. Each hint narrows the search a little more.

`solution/SOLUTION.md` has the full reference answer and explains what the lab teaches. Open it when you've finished, or when the hints aren't enough.

## After you finish

<details>
<summary>Reflection questions</summary>

1. Several incidents gave a similar wrong answer. Did they all need the same fix?
2. Which incidents could a bigger model have helped with, and which not at all? Why?
3. What could have gone wrong with a different fix, and which check would have caught it?

Compare your answers with "Check your reasoning" in `solution/SOLUTION.md`.

</details>

<details>
<summary>Pattern to remember after you finish</summary>

When a RAG answer is wrong, work through these steps.

1. Work out the right answer, and find the chunk that says it.
2. Look for that chunk in **Candidates by similarity**.
3. Follow it into **After reranking** and **Kept**.
4. Check **Prompt assembly**. Was it **reached** or **cut**?
5. Read the **Prompt sent to the model**, then the answer.
6. Stop at the first section where the chunk disappears, or where the answer departs from the prompt. That's the layer to fix.
7. Change code only when the evidence points to code, and verify both checks.

</details>

## Optional follow-up reading

This lab practices the method in Part 7 of the AI in Practice Hub RAG series, [Your RAG System Is Wrong. Here's How to Find Out Why.](https://aiinpracticehub.com/articles/your-rag-system-is-wrong-heres-how-to-find-out-why/). The [RAG Debugging Lab](https://aiinpracticehub.com/labs/rag-debugging/) is a shorter first lab if you'd like more practice.

## License

Code and lab content: MIT. See `LICENSE`.

Bundled embedding model: see `THIRD_PARTY_NOTICES.md`.
