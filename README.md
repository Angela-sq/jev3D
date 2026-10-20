# AI Workshop Research Paper

Generic, two-column LaTeX starter for drafting an AI workshop paper.
This is not an official conference style and imposes no venue page limit.
Once you select a workshop, use its required style and submission rules.

## Overleaf setup

1. Download `ai-workshop-overleaf.zip` from this project.
2. In Overleaf, choose **New Project → Upload Project** and select the ZIP.
3. Set the main document to `main.tex` and compiler to **pdfLaTeX**.
4. Click **Recompile**. Overleaf runs BibTeX automatically as needed.

## Writing

- Set the title and author information in `main.tex`.
- Anonymous mode is on by default. Change `\anonymoustrue` to
  `\anonymousfalse` to show authors and acknowledgments. This switch hides
  the author block only; check prose, citations, figures, and artifact links
  separately when preparing an anonymous submission.
- Edit the numbered files in `sections/` for the body and appendix.
- Add bibliography entries to `references.bib`; use `\citet{key}` for
  narrative citations and `\citep{key}` for parenthetical citations.
- Add images under `figures/` and replace the example figure box.
- Replace all prompts and placeholder results before submission.
- Remove unused sections, examples, and the example citation.

Included: abstract, introduction, related work, method, experiments,
ablations, discussion/limitations, conclusion, references, and appendix;
figure/table/equation examples; theorem environments and linked references.

## Local build

With a LaTeX distribution and latexmk installed:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex
```

The output is `build/main.pdf`. The ZIP contains the editable source only.

## Minecraft benchmark (mcbench)

`tools/mcbench/` scores how well a model plays Minecraft from screenshots
alone. Setup, commands, method, and limitations: [`tools/mcbench/README.md`](tools/mcbench/README.md).
Claude Fable 5.1 results: [`experiments/minecraft-fable-2026-10-19/`](experiments/minecraft-fable-2026-10-19/)
(`RESULTS.txt`, `report.pdf`).

```sh
cd tools/mcbench
uv sync && ./docker/run.sh
uv run pytest
uv run mcbench smoke
```
