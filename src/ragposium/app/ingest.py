import json
import os
from pathlib import Path
from re import A
from typing import Iterator
import chromadb
import numpy as np
from pymilvus import MilvusClient, connections
from torch import Tensor
from tqdm import tqdm
from ragposium import DATA_DIR
from ragposium.app.arxiv import ArxivPaper
from loguru import logger
import kagglehub
from sentence_transformers import SentenceTransformer



class IngestionManager:
    """Ingest arXiv data into a Milvus database."""

    def __init__(self):

        logger.debug("Connecting to Chroma...")

        # self.chroma_client = chromadb.Client()
        self.chroma_client = chromadb.HttpClient(host='localhost', port=8000)

        if not any("ragposium"==col for col in self.chroma_client.list_collections()):
            self.chroma_client.create_collection(name="ragposium")

        self.collection = self.chroma_client.get_collection(name="ragposium")

        logger.success("Successfully connected to Chroma.")


        self.dataset_dir = self.download_datasets()
        self.arxiv_dataset = self.dataset_dir / "arxiv-metadata-oai-snapshot.json"


    def download_datasets(self) -> Path:
        """Download the necessary datasets. Cashes using kaggle.
        
        Returns:
            A path to the dataset download dir.
        """

        # Download latest version
        return Path(kagglehub.dataset_download("Cornell-University/arxiv"))


    def count_datasets(self) -> int:
        """Count the number of datasets."""

        logger.info("Counting entries....")
        i = 0
        with self.arxiv_dataset.open('r') as f:
            for _ in f:
                i += 1

        logger.info(f"Counted {i} entries")
        return i
        


    def iter_arxiv(self) -> Iterator[ArxivPaper]:
        """Iterate over the ArXiv papers available."""
        
        MAX_ITER = 10

        with self.arxiv_dataset.open('r') as f:
            for i, line in enumerate(f.readlines()):
                if i > MAX_ITER:
                    return
                yield ArxivPaper(**json.loads(line))


    def embed_abstract(self, abstract: str) -> Tensor:
        """Run the abstract of a paper through an embedding matrix.
        """

        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(abstract)


    def run(self):

        embeddings = []

        total_entries = self.count_datasets()
        for paper in tqdm(self.iter_arxiv(), total=total_entries, desc="Ingesting"):
            if paper.abstract:
                embeddings.append(
                    self.embed_abstract(paper.abstract)
                    )


        logger.info(f"Created {len(embeddings)} tensors")

        

