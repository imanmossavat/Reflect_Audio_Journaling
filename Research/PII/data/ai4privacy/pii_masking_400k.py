from datasets import load_dataset

def load_pii_dataset(split: str = "train", limit: int | None = None):
    """
    Load the ai4privacy/pii-masking-400k dataset.

    Args:
        split (str): which split to load ('train', 'test', 'validation')
        limit (int | None): optionally limit number of examples

    Returns:
        datasets.Dataset: loaded dataset (optionally sliced)
    """
    ds = load_dataset("ai4privacy/pii-masking-400k", split=split)
    if limit:
        ds = ds.select(range(limit))
    return ds
