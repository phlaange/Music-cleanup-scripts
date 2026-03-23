#!/usr/bin/env python3
"""
cluster_sets.py — Group images into sets using CLIP visual similarity.

Dependencies:
    pip install torch transformers Pillow numpy scikit-learn hdbscan tqdm

Optional (improves clustering quality):
    pip install umap-learn

  ● Here's the script at N:/Pics/TGod/cluster_sets.py. Install the dependencies first:

  pip install torch transformers Pillow numpy scikit-learn hdbscan tqdm

  Then just run:
  python cluster_sets.py

  What it does:
  1. Generates CLIP embeddings for every image (understands visual content semantically)
  2. Saves embeddings to _embeddings.npz — so if you re-run with tweaked settings it skips the slow step
  3. Clusters with HDBSCAN (no need to specify how many sets — it figures that out)
  4. Copies files into Grouped/set_0001/, set_0002/, etc., sorted by the sequence number within each set
  5. Anything it can't confidently group goes into Grouped/unclustered/

  Tuning knobs if the results aren't right:
  - MIN_CLUSTER = 3 — raise this if you're getting lots of tiny spurious groups
  - MIN_SAMPLES = 2 — lower puts more into sets, higher sends more to unclustered
  - USE_UMAP = True — often improves clustering quality (needs pip install umap-learn)
  - CLIP_MODEL = "openai/clip-vit-large-patch14" — more accurate, slower
  - MOVE_FILES = True — once you're happy with results, switch to move instead of copy
"""

import re
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
from sklearn.preprocessing import normalize
import hdbscan
from tqdm import tqdm

# ── Configuration ──────────────────────────────────────────────────────────────

IMAGE_DIR   = Path(r"N:\Pics\TGod")
OUTPUT_DIR  = Path(r"N:\Pics\TGod\Grouped")
CACHE_FILE  = IMAGE_DIR / "_embeddings.npz"   # cached so re-runs skip re-embedding

CLIP_MODEL  = "openai/clip-vit-base-patch32"  # swap to clip-vit-large-patch14 for better accuracy
BATCH_SIZE  = 32

# Clustering: raise MIN_CLUSTER if you're getting too many tiny groups
MIN_CLUSTER = 3   # minimum images to form a set
MIN_SAMPLES = 2   # lower = more clusters, higher = more goes to "unclustered"

# Use UMAP to reduce embedding dimensions before clustering (better results, extra dependency)
USE_UMAP    = False
UMAP_DIMS   = 50

MOVE_FILES  = False   # False = copy (safe); set True to move instead

# ───────────────────────────────────────────────────────────────────────────────


def seq_num(path: Path) -> int:
    """Extract sequence number: '0000011749 - 58.jpg' → 58."""
    m = re.search(r' - (\d+)', path.stem)
    return int(m.group(1)) if m else 0


def load_image_files(directory: Path) -> list:
    exts = {'.jpg', '.jpeg', '.png', '.webp'}
    return sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in exts
    )


def build_embeddings(files: list) -> np.ndarray:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading {CLIP_MODEL} on {device}...")
    model = CLIPModel.from_pretrained(CLIP_MODEL).to(device).eval()
    processor = CLIPProcessor.from_pretrained(CLIP_MODEL)

    all_features = []
    for i in tqdm(range(0, len(files), BATCH_SIZE), desc="Embedding images"):
        batch = files[i : i + BATCH_SIZE]
        images = []
        for p in batch:
            try:
                images.append(Image.open(p).convert("RGB"))
            except Exception as e:
                print(f"\n  Skipping {p.name}: {e}")
                images.append(Image.new("RGB", (224, 224)))  # blank placeholder

        inputs = processor(images=images, return_tensors="pt", padding=True).to(device)
        with torch.no_grad():
            feats = model.get_image_features(**inputs)
        all_features.append(feats.cpu().float().numpy())

    embeddings = np.vstack(all_features)
    return normalize(embeddings)  # L2-normalise → cosine similarity via euclidean distance


def reduce_dimensions(embeddings: np.ndarray) -> np.ndarray:
    try:
        import umap
        print(f"Reducing to {UMAP_DIMS} dimensions with UMAP...")
        reducer = umap.UMAP(n_components=UMAP_DIMS, metric="cosine", random_state=42)
        return reducer.fit_transform(embeddings)
    except ImportError:
        print("umap-learn not installed — skipping dimension reduction. Install with: pip install umap-learn")
        return embeddings


def cluster_embeddings(embeddings: np.ndarray) -> np.ndarray:
    print("Clustering...")
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=MIN_CLUSTER,
        min_samples=MIN_SAMPLES,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    return clusterer.fit_predict(embeddings)


def organise_files(files: list, labels: np.ndarray):
    n_clusters = int(labels.max()) + 1 if labels.max() >= 0 else 0
    n_noise    = int((labels == -1).sum())
    print(f"\n  {n_clusters} sets found")
    print(f"  {n_noise} unclustered images")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    op = shutil.move if MOVE_FILES else shutil.copy2

    for label in tqdm(sorted(set(labels)), desc="Organising"):
        folder_name = "unclustered" if label == -1 else f"set_{label:04d}"
        dest_dir = OUTPUT_DIR / folder_name
        dest_dir.mkdir(exist_ok=True)

        # Sort by sequence number within each set
        group = [(f, seq_num(f)) for f, l in zip(files, labels) if l == label]
        group.sort(key=lambda x: x[1])

        for src, _ in group:
            op(str(src), str(dest_dir / src.name))

    print(f"\nDone — files organised in: {OUTPUT_DIR}")


def main():
    files = load_image_files(IMAGE_DIR)
    print(f"{len(files)} images found in {IMAGE_DIR}")

    # Load cached embeddings if available and file list hasn't changed
    current_names = [f.name for f in files]
    if CACHE_FILE.exists():
        print("Loading cached embeddings...")
        data = np.load(CACHE_FILE, allow_pickle=True)
        cached_names = list(data["names"])
        if cached_names == current_names:
            embeddings = data["embeddings"]
        else:
            print("File list has changed — rebuilding embeddings...")
            embeddings = build_embeddings(files)
            np.savez(CACHE_FILE, embeddings=embeddings, names=current_names)
    else:
        embeddings = build_embeddings(files)
        np.savez(CACHE_FILE, embeddings=embeddings, names=current_names)

    if USE_UMAP:
        embeddings = reduce_dimensions(embeddings)

    labels = cluster_embeddings(embeddings)
    organise_files(files, labels)


if __name__ == "__main__":
    main()
