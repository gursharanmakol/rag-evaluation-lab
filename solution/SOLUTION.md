# Solution

Read this after you've finished, or when the hints aren't enough.

## What you learned

Six answers were escalated, and five of them were wrong. They went wrong at three different layers, and only two of them came from the code. One recent change made the reranker see only the results it was about to keep, so a chunk that ranked low on similarity could never be lifted into the kept results. A stronger model would not fix that, because the right chunk never reached the model. The fix is one line, and the evaluation proves it, with the assembly check confirming that the fix didn't break the prompt budget.

## The pattern to remember

Follow the chunk that should have answered, section by section, and stop at the first place it disappears or is ignored.

    Expected chunk            outlet#terms
           |
           v
    1. Candidates by similarity    FOUND (rank 6)
           |
           v
    2. After reranking             MISSING (3 rows)
           |
           v
    3. Kept                        MISSING
           |
           v
    First failing layer            RETRIEVAL

That's I1. The same walk gives a different answer for other incidents. I3's chunk survives to **Kept** and is **cut** at **Prompt assembly**. I4's chunk reaches the prompt, and the answer ignores it.

## The answer key

| Incident | Failed? | First failing layer | Evidence |
| --- | --- | --- | --- |
| I1 | Yes | Retrieval | `outlet#terms` is candidate 6 (0.498), but **After reranking** has only 3 rows and it isn't among them. The kept `wh1000#returns` says 15 days. |
| I2 | Yes | Retrieval | `outlet#terms` is candidate 10 (0.445), and it's missing from **After reranking** and **Kept**. |
| I3 | Yes | Assembly | `outlet#terms` is kept at position 2, but **Prompt assembly** shows `conversation history 300`, then `outlet#terms 141 cut`. Total 434 of 500. With it, the total would have been 575. |
| I4 | Yes | Generation | `outlet#terms` is kept first and **reached**. The prompt says "Outlet purchases can be sent back for a refund within 7 days of delivery", and the answer says 15 days. |
| I5 | Yes | Generation | The answer says "You can also exchange them within 30 days." No chunk in the prompt mentions exchanges or 30 days, and neither does any chunk in the help center. |
| I6 | No | None | `firmware#v3.2` is kept first and reached, and the answer matches it exactly. Version 3.2 never claims to fix pairing. The customer needed the pairing steps in `wh1000#care`. |

The right answer for I1 to I4 is 7 days, because the customers bought from the TechNova Outlet. The help center says so in `outlet#terms`.

## Why the Outlet chunk ranked low

Customers say "refurbished". The 7-day rule lives in the Outlet purchase terms, which use the word "refurbished" once, in a sentence about what the Outlet sells. Each product page has a "Returns and warranty" section that says 15 days, and those sections look much more like a return question. So similarity ranks the product pages and general return sections above the Outlet terms, which land 6th to 10th.

The keyword reranker is what connects the two. "Refurbished" is rare in the help center, so it earns a large boost, enough to lift `outlet#terms` to the top. It can do that only if it sees the chunk.

I4 asked about "Outlet purchases", which matches the Outlet terms directly, so similarity alone ranked the chunk first. That's why I4's chunk reached the prompt, and why its failure is somewhere else.

## The code change

`CHANGES.md` says "Rerank only the results we keep, to speed up requests." `git log -p -- src/` shows the change in `retrieve()`, on this line.

    reranked = rerank(index, question, candidates[:top_k])

The reranker now sees only the first 3 similarity results, the ones that would have been kept anyway. It can reorder them, but it can never promote a chunk from further down.

The fix is one line.

    reranked = rerank(index, question, candidates)

The line that appends the remaining candidates can stay. After the fix there's nothing left to append.

## Before and after

| | Before | After |
| --- | --- | --- |
| Retrieval check | 8 of 10, FAIL | 10 of 10, PASS |
| recall@3 | 80% | 100% |
| recall@10 | 100% | 100% |
| MRR | 0.82 | 0.95 |
| Assembly check | 30 of 30 kept chunks, 0 cut, PASS | 30 of 30 kept chunks, 0 cut, PASS |
| Q09 position | 8 | 1 |
| Q10 position | 9 | 2 |

The table shows the original 10 questions. If you added a question first, as the assignment asks, your counts include it. With the reference question Q11 added, the numbers read like this.

| | Before | After |
| --- | --- | --- |
| Retrieval check | 8 of 11, FAIL | 11 of 11, PASS |
| recall@3 | 73% | 100% |
| recall@10 | 100% | 100% |
| MRR | 0.76 | 0.91 |
| Assembly check | 33 of 33 kept chunks, 0 cut, PASS | 33 of 33 kept chunks, 0 cut, PASS |

Before the fix, recall@10 is 100% while recall@3 is 80%. The right chunk was found, but below the cut-off. That gap is the signature of a ranking problem, not a search problem.

After the fix, a few unrelated chunks move into the kept results. Q08 (gift cards) now keeps `outlet#terms`, because the Outlet terms mention "partner gift cards". Q07 keeps `eb20#returns`, because it mentions cleaning. A keyword reranker trades a little precision for recall. Both questions still keep their expected chunk first, `wh1000#care` for Q07 and `returns-policy#exceptions` for Q08.

## Why the tempting fixes are wrong

| Fix | Retrieval check | Assembly check | Why it fails |
| --- | --- | --- | --- |
| Keep 4 chunks | 8 of 10, FAIL | 30 of 40, 10 cut, FAIL | The reranker now sees 4 results, still not enough, and 4 chunks never fit in 500 tokens |
| Keep 5 chunks | 8 of 10, FAIL | 30 of 50, 20 cut, FAIL | Same, with more cut |
| Keep 10 chunks | 10 of 10, PASS | 30 of 100, 70 cut, FAIL | Retrieval passes only because the reranker sees 10 results. Most kept chunks never reach the prompt. |
| Raise the budget | n/a | n/a | The lab fixes the context budget at 500 tokens. Raising it would not address the retrieval failure in I1 and I2. |
| Switch to a bigger model | Unchanged | Unchanged | A stronger model might help with I4 or I5 because the necessary evidence reached the prompt. It would not fix I1, I2, or I3, where the required evidence never reached the model. |

Every chunk here is 132 to 146 tokens, so any 3 fit (436 at most) and any 4 overflow (528 at least). Keeping more chunks fixes nothing at the layer that failed, and breaks the layer after it.

## What about I3, I4, and I5?

They're real failures, but not this ticket's code change.

- **I3, assembly.** A long conversation used 300 of the 500 tokens, so the second kept chunk was cut. In production you'd summarize or trim old turns, or reserve part of the budget for retrieved chunks. `evaluate` can't reproduce this, because evaluation questions have no history. That's a reason to add evaluation cases with long conversations.
- **I4 and I5, generation.** The right evidence was in the prompt. I4 ignored it, and I5 added a claim with no source. A stronger model, a stricter instruction, or an answer check might help here. An answer-quality judge, like the one in Part 7, would flag both.

## The regression question

`solution/questions_added.yaml` holds this question.

    - id: Q11
      question: "My refurbished SP-50 speaker arrived 8 days ago. Can I return it?"
      expected: "outlet#terms"

On the original code it fails. `outlet#terms` is at position 10, the evaluation shows 8 of 11, and Q11 is listed under Retrieval failures. After the fix it passes, at position 2, and the evaluation shows 11 of 11. It's a new product and new wording, so it tests the failure pattern rather than repeating an incident.

A good regression question targets the same failure, a rule that ranks just below the cut, with wording that isn't already in the evaluation set. Be careful with wording that names the Outlet. "Can I return a refurbished SP-50 from the Outlet after 8 days?" already keeps `outlet#terms` on the original code, because "Outlet" matches the chunk directly. It passes before the fix, so it wouldn't have caught the bug. That's why the assignment asks you to confirm the new question fails before changing the code.

## Why not edit the evaluation set?

Changing an expected chunk, or deleting Q09 and Q10, would make the retrieval check pass without changing what customers get. The evaluation exists to catch exactly this regression.

## Check your reasoning

1. **Did the incidents that gave a similar wrong answer need the same fix?** No. I1, I3, and I4 all said 15 days. I1 failed at retrieval, I3 at assembly, and I4 at generation. Only I1 (and I2) had a code fix in this ticket. Changing retrieval for I3 or I4 would have changed nothing.
2. **Which incidents could a bigger model have helped?** A stronger model might help with I4 or I5 because the necessary evidence reached the prompt. It would not fix I1, I2, or I3, where the required evidence never reached the model.
3. **What could have gone wrong with a different fix?** Keeping more chunks lifts some retrieval numbers and cuts chunks from the prompt. The assembly check catches that, because every kept chunk must reach the prompt intact.

## Where to look next time

<details>
<summary>A customer says the assistant quoted last year's shipping fee. Where do you start?</summary>

Find the chunk with this year's fee, and follow it through the trace. If it's missing from the candidates, look at the index or the documents. If it's a candidate but not kept, look at ranking. If it's kept but cut, look at assembly. If it reached the prompt, compare the prompt with the answer. Change code only where the evidence first diverges.

</details>
