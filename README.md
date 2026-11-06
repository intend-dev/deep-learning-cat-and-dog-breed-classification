# Deep Learning Systems: Cat and Dog Breed Classification

## Overview

This project compares a small CNN trained from scratch against a ResNet18 fine-tuned from ImageNet weights on the Oxford-IIIT Pet dataset: `37` cat and dog breeds, `7,349` photographs, identical training rules for both models. The pretrained model reaches `0.8940` test accuracy against `0.2044` from scratch, with per-class results, a confusion matrix, and error examples all in the notebook.
Repository: https://github.com/intend-dev/MS-09-CAP-05-DLS

## Repository

- `deep_learning.ipynb`: executed notebook with data loading, training, evaluation, figures, and a final headline block of reproducible numbers
- `module_summary.md` and `module_summary.pdf`: the written report and the print-ready report
- `figures/`: the two report figures, exported by the notebook
- `DATASET.md`: dataset access, contents, checksums, license
- `requirements.txt`: pinned package versions
- `data/`: the dataset lands here on first run (see DATASET.md)

## Reproduce

`requirements.txt` was generated with `pip freeze`, so install its pinned packages with `pip install -r requirements.txt` in an activated Python `3.13` environment.
The `uv` commands below show the same setup with `uv`, the alternative used for this rebuild; the CUDA wheel index is required because `torch==2.11.0+cu128` is not on PyPI:

```powershell
uv venv --python 3.13 .venv
uv pip install --python .venv\Scripts\python.exe --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match -r requirements.txt
.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace deep_learning.ipynb
```

The first execution downloads Oxford-IIIT Pet under `data/oxford-iiit-pet/` (about `811` MB) and is offline-safe afterward.
If you regenerate `requirements.txt`, avoid PowerShell `>` because it writes UTF-16.
A CPU-only machine runs the same code, only slower.

## Dataset

- [Oxford-IIIT Pet](https://www.robots.ox.ac.uk/~vgg/data/pets/) from Oxford VGG
- `7,349` photographs covering `37` breeds; `3,680` trainval, `3,669` test
- First-run download: images.tar.gz (`792` MB) and annotations.tar.gz (`19` MB), about `811` MB together
- Recorded checksums from the original download (`2026-10-10`):
  - images: `SHA256 67195C5E1C01F1AB5F9B6A5D22B8C27A580D896ECE458917E61D459337FA318D`
  - annotations: `SHA256 52425FB6DE5C424942B7626B428656FCBD798DB970A937DF61750C0F1D358E91`
- License: CC BY-SA 4.0

## License

Shared for portfolio and review purposes only, no reuse license is granted, and no license file is included.
The dataset is public data under its own terms (CC BY-SA 4.0); see `DATASET.md`.
