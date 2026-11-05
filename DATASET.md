# Dataset access

**Dataset:** Oxford-IIIT Pet, the Oxford VGG cat and dog photograph dataset.

**Task:** fine-grained image classification over `37` breeds.

**Contents:** `7,349` photographs in two splits, `3,680` in `trainval` and `3,669` in `test`, with about `200` images per breed.

**Source:** the official page is `https://www.robots.ox.ac.uk/~vgg/data/pets/`, which publishes the `images.tar.gz` and `annotations.tar.gz` archives.

**Access in the notebook:** `deep_learning.ipynb` loads the data with `torchvision.datasets.OxfordIIITPet(root="data", split=..., download=True)` on first run. The first execution downloads and unpacks both archives (about `811` MB: `792` MB of images plus `19` MB of annotations) under `data/oxford-iiit-pet/` (torchvision's base folder is `data/`); later runs reuse it with `download=False` and are offline-safe. No manual download is required.

**Integrity:** the two archives were measured when the dataset was first downloaded (`2026-10-10`). The package ships no dataset files and no notebook cell re-checks these values, so they record the original download rather than a live verification:

- images: `SHA256 67195C5E1C01F1AB5F9B6A5D22B8C27A580D896ECE458917E61D459337FA318D` (`791918971` bytes)
- annotations: `SHA256 52425FB6DE5C424942B7626B428656FCBD798DB970A937DF61750C0F1D358E91` (`19173078` bytes)

**License:** Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0). Copyright of the photographs stays with the original owners; any redistribution must keep the attribution and share-alike terms.

**Not reused:** this dataset was not used in a previous capstone project. EuroSAT was the second candidate and was not used.
