# Third-party notices

This repository includes third-party material that is not covered by the
repository `LICENSE`.

## potion-base-8M

- Name: potion-base-8M
- Author/organization: Minish Lab
- License: MIT
- Source: https://huggingface.co/minishlab/potion-base-8M
- Bundled path: `models/potion-base-8M/`

This embedding model is bundled for offline use.

### Verified license evidence

The bundled model card at `models/potion-base-8M/README.md` declares:

```yaml
license: mit
model_name: potion-base-8M
```

The same model card states that Model2Vec was developed by the Minish Lab
team (Stephan Tulkens and Thomas van Dongen).

No separate `LICENSE` file is present in the bundled model directory. The
upstream path
`https://huggingface.co/minishlab/potion-base-8M/raw/main/LICENSE` was also
not found at the time of this notice.

This notice does not claim that every bundled file is an unmodified copy of
the current upstream revision. At verification time, `model.safetensors`
matched the upstream file hash; `README.md`, `config.json`, `modules.json`,
and `tokenizer.json` differed from the then-current upstream `main` files.

### MIT license text

Because the model card identifies the MIT license, the standard MIT terms
are reproduced below. No upstream copyright line was present in a bundled or
upstream `LICENSE` file; attribution above is taken from the model card.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
