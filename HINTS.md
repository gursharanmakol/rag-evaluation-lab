# Hints

Open one hint at a time. Try the next step on your own before you open the next hint.

<details>
<summary>Hint 1: Follow one chunk through the trace</summary>

Pick one incident where the customer ended up worse off. Use the support note to work out what the right answer was, then find the chunk that says it. `uv run python lab.py chunks` lists every chunk.

Now run `trace` for that incident and follow the chunk through each numbered section, from **1. Candidates by similarity** to **5. Prompt sent to the model**. In which section does it stop appearing? If it never stops appearing, compare the prompt with the answer.

Do the same for each incident. They don't all stop in the same place.

</details>

<details>
<summary>Hint 2: Compare two sections, then look at recent changes</summary>

For the incidents where the right chunk is in section 1 but not in section 3, compare **1. Candidates by similarity** with **2. After reranking**. How many rows does each have? Where was the chunk you were looking for?

Then run `inspect` on the same question to see what the current code does.

Now look at what changed recently. Read `CHANGES.md`, then look at the history of the code with this command.

    git log -p -- src/

Press `q` to leave the log.

</details>

<details>
<summary>Hint 3: Read the retrieval code</summary>

Open `retrieve()` in `src/pipeline.py`. Which chunks does the reranker get to see, all the candidates or only some? Which should it see, so that a chunk ranked low by similarity can still be lifted into the kept results, without keeping more chunks than the prompt can hold?

Before changing the code, add your new evaluation question and run `evaluate`. A useful regression question should fail on the current code for the same reason as the code-related incidents. After your fix, the same question should pass.

</details>
