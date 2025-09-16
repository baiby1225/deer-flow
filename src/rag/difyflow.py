# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
import json
import logging
import os
from typing import List, Optional
from urllib.parse import urlparse

import requests

from src.rag.retriever import Chunk, Document, Resource, Retriever


class DifyFlowProvider(Retriever):
    """
    DifyFlowProvider is a provider that uses Dify knowledge bases to retrieve documents.
    Supports querying from multiple knowledge bases automatically.
    """

    api_url: str
    api_key: str
    page_size: int = 10
    max_knowledge_bases: int = 10  # Maximum number of knowledge bases to query

    def __init__(self):
        api_url = os.getenv("DIFY_API_URL")
        if not api_url:
            raise ValueError("DIFY_API_URL is not set")
        self.api_url = api_url

        api_key = os.getenv("DIFY_API_KEY")
        if not api_key:
            raise ValueError("DIFY_API_KEY is not set")
        self.api_key = api_key

        page_size = os.getenv("DIFY_PAGE_SIZE")
        if page_size:
            self.page_size = int(page_size)

        max_kb = os.getenv("DIFY_MAX_KNOWLEDGE_BASES")
        if max_kb:
            self.max_knowledge_bases = int(max_kb)

    def query_relevant_documents(
            self, query: str, resources: list[Resource] = []
    ) -> list[Document]:
        """
        Query relevant documents from Dify knowledge bases.
        
        Args:
            query: The search query
            resources: List of resources to search in (optional, queries all knowledge bases if empty)
            
        Returns:
            List of relevant documents from all specified knowledge bases
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Determine which knowledge bases to query
        knowledge_base_ids = []

        if resources:
            # Use specific knowledge bases from resources
            for resource in resources:
                kb_id = self._parse_uri(resource.uri)
                if kb_id and kb_id not in knowledge_base_ids:
                    knowledge_base_ids.append(kb_id)
        else:
            # Get all available knowledge bases
            try:
                all_resources = self.list_resources()
                for resource in all_resources[:self.max_knowledge_bases]:
                    kb_id = self._parse_uri(resource.uri)
                    if kb_id and kb_id not in knowledge_base_ids:
                        knowledge_base_ids.append(kb_id)
            except Exception as e:
                raise Exception(f"Failed to get knowledge bases: {str(e)}")

        if not knowledge_base_ids:
            raise Exception("No knowledge bases available for querying")

        # Query each knowledge base and aggregate results
        all_documents = []
        doc_id_counter = 0  # To ensure unique document IDs across knowledge bases

        for kb_id in knowledge_base_ids:
            try:
                payload = {
                    "query": query,
                    # "retrieval_model": {
                    #     "search_method": "hybrid_search",
                    #     "reranking_enable": "true",
                    #     "reranking_mode": "reranking_model",
                    #     "reranking_model": {
                    #         "reranking_provider_name": "langgenius/siliconflow/siliconflow",
                    #         "reranking_model_name": "BAAI/bge-reranker-v2-m3"
                    #     },
                    #     "weights": {
                    #         "weight_type": "customized",
                    #         "keyword_setting": {
                    #             "keyword_weight": 0.3
                    #         },
                    #         "vector_setting": {
                    #             "vector_weight": 0.7,
                    #             "embedding_model_name": "text-embedding-v4",
                    #             "embedding_provider_name": "langgenius/tongyi/tongyi"
                    #         }
                    #     },
                    #     "top_k": 5,
                    #     "score_threshold_enabled": "true",
                    #     "score_threshold": 0.1
                    # }
                }
                response = requests.post(
                    f"{self.api_url}/datasets/{kb_id}/retrieve",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    documents = self._parse_dify_response(result, kb_id, doc_id_counter)
                    all_documents.extend(documents)
                    doc_id_counter += len(documents)
                else:
                    # Log error but continue with other knowledge bases
                    logging.error(
                        f"Warning: Failed to query knowledge base {kb_id}: {response.status_code} - {response.text}")
                    continue

            except Exception as e:
                # Log error but continue with other knowledge bases
                logging.error(f"Warning: Network error while querying knowledge base {kb_id}: {str(e)}")
                continue

        # Sort documents by similarity score (highest first)
        all_documents.sort(key=lambda doc: max(chunk.similarity for chunk in doc.chunks) if doc.chunks else 0,
                           reverse=True)

        # Limit total results to avoid overwhelming the system
        max_total_results = self.page_size * len(knowledge_base_ids)

        return all_documents[:max_total_results]

    def list_resources(self, query: str | None = None) -> list[Resource]:
        """
        List available knowledge bases from Dify.

        Args:
            query: Optional search query to filter knowledge bases

        Returns:
            List of available knowledge base resources
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            # 构建查询参数
            params = {
                "page": 1,
                "limit": 100,  # 获取更多知识库
            }

            # 如果有搜索关键词，添加到参数中
            if query:
                params["keyword"] = query

            # List datasets (knowledge bases)
            response = requests.get(
                f"{self.api_url}/datasets",
                headers=headers,
                params=params,
                timeout=30
            )

            if response.status_code != 200:
                raise Exception(f"Failed to list Dify datasets: {response.status_code} - {response.text}")

            result = response.json()
            resources = []

            for dataset in result.get("data", []):
                dataset_id = dataset.get("id")
                dataset_name = dataset.get("name", "")
                dataset_description = dataset.get("description", "")

                # Filter by query if provided (now handled by API keyword parameter)
                # Keep this for additional client-side filtering if needed
                if query and query.lower() not in dataset_name.lower() and query.lower() not in dataset_description.lower():
                    continue

                resource = Resource(
                    uri=f"dify://dataset/{dataset_id}",
                    title=dataset_name,
                    description=dataset_description,
                )
                resources.append(resource)

            return resources

        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error while listing Dify datasets: {str(e)}")

    def _parse_dify_response(self, response: dict, knowledge_base_id: str = "", doc_id_offset: int = 0) -> list[
        Document]:
        """
        Parse Dify API response and convert to Document format.

        Args:
            response: Dify API response dictionary
            knowledge_base_id: The knowledge base ID for context
            doc_id_offset: Offset for document ID to ensure uniqueness across knowledge bases

        Returns:
            List of Document objects
        """
        documents = []
        records = response.get("records", [])

        # Group records by document
        doc_map = {}

        for record in records:
            # Extract data from the nested structure
            segment = record.get("segment", {})
            score = record.get("score", 0.0)

            # Get document information from segment
            original_doc_id = segment.get("document_id", "")
            doc_name = segment.get("document", {}).get("name", "")
            content = segment.get("content", "")

            # Create unique document ID across knowledge bases
            unique_doc_id = f"{knowledge_base_id}_{original_doc_id}_{doc_id_offset + len(doc_map)}"

            if unique_doc_id not in doc_map:
                doc_map[unique_doc_id] = Document(
                    id=unique_doc_id,
                    title=f"[{knowledge_base_id}] {doc_name}" if knowledge_base_id else doc_name,
                    chunks=[]
                )

            # Add chunk to document
            chunk = Chunk(
                content=content,
                similarity=score
            )
            doc_map[unique_doc_id].chunks.append(chunk)

        return list(doc_map.values())

    def _parse_uri(self, uri: str) -> str | None:
        """
        Parse Dify URI to extract dataset ID.

        Args:
            uri: URI in format dify://dataset/{dataset_id} or dify://knowledge_base/{knowledge_base_id}

        Returns:
            Dataset ID or None if invalid format
        """
        try:
            parsed = urlparse(uri)
            if parsed.scheme != "dify":
                return None

            path_parts = parsed.path.split("/")
            return path_parts[-1]
        except Exception:
            return None


def parse_uri(uri: str) -> tuple[str, str]:
    """
    Parse Dify URI to extract knowledge base ID and document ID.
    
    Args:
        uri: URI in format dify://knowledge_base/{knowledge_base_id}/document/{document_id}
        
    Returns:
        Tuple of (knowledge_base_id, document_id)
    """
    parsed = urlparse(uri)
    if parsed.scheme != "dify":
        raise ValueError(f"Invalid URI scheme: {uri}")

    path_parts = parsed.path.split("/")
    if len(path_parts) < 3 or path_parts[1] != "knowledge_base":
        raise ValueError(f"Invalid Dify URI format: {uri}")

    knowledge_base_id = path_parts[2]
    document_id = ""

    # Check if document ID is provided
    if len(path_parts) >= 5 and path_parts[3] == "document":
        document_id = path_parts[4]

    return knowledge_base_id, document_id
