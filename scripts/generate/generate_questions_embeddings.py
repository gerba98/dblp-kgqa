import logging
import math
import sys
import time

from pydantic import BaseModel, Field

from dblp_kgqa import PROJECT_ROOT
from dblp_kgqa.services.dblp_quad import DblpQuadService, DblpQuadServiceConfig
from dblp_kgqa.services.embedding import (
    EmbeddingService,
    EmbeddingServiceConfig,
)

logger = logging.getLogger(__name__)

# CONFIG ----------------------------------------------------------------------
TASK_TYPE = "SEMANTIC_SIMILARITY"
BATCH_SIZE = 100
MAX_RETRIES = 10
BASE_DELAY = 15.0

# SCHEMAS ---------------------------------------------------------------------
class QuestionEmbedding(BaseModel):
    id: str
    question_embedding: list[float]
    paraphrased_question_embedding: list[float]


class DatasetEmbeddings(BaseModel):
    samples: list[QuestionEmbedding] = Field(default_factory=list)


# UTILS -----------------------------------------------------------------------
def _questions_embeddings_path(model_name: str) -> str:
    model_slug = model_name.replace("/", "_")
    return f"data/dblp_quad/train/embeddings_{model_slug}.json"


def embed_batch_with_retry(
    embedding_service: EmbeddingService,
    texts: list[str],
    batch_label: str,
) -> list[list[float]]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return embedding_service.embed_batch(texts)
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "resource_exhausted" in err_str:
                delay = BASE_DELAY * attempt
                logger.warning(
                    f"Rate limited on {batch_label} "
                    f"(attempt {attempt}/{MAX_RETRIES}). "
                    f"Retrying in {delay:.0f}s..."
                )
                time.sleep(delay)
            else:
                raise

    raise RuntimeError(
        f"Embedding failed after {MAX_RETRIES} retries on {batch_label}"
    )


# MAIN ------------------------------------------------------------------------
def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)

    dataset_service = DblpQuadService(DblpQuadServiceConfig())
    dataset = dataset_service.load("train", "questions")
    embedding_service = EmbeddingService(
        EmbeddingServiceConfig(
            model_name="gemini-embedding-001",
            task_type=TASK_TYPE,
        )
    )

    output_file = PROJECT_ROOT / _questions_embeddings_path(
        embedding_service.config.model_name
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Resume support
    results = DatasetEmbeddings()
    processed_ids: set[str] = set()

    if output_file.exists():
        existing = DatasetEmbeddings.model_validate_json(
            output_file.read_text()
        )
        results.samples = existing.samples
        processed_ids = {s.id for s in existing.samples}
        print(f"Resumed: {len(processed_ids)} samples already processed.")

    # Filter remaining samples
    remaining = [
        s for s in dataset.questions if s.id not in processed_ids
    ]
    total = len(dataset.questions)
    errors = 0

    print(
        f"Starting embedding generation for {total} questions "
        f"({len(processed_ids)} already done, {len(remaining)} remaining)..."
    )

    # Process in batches
    num_batches = math.ceil(len(remaining) / BATCH_SIZE)

    for i in range(num_batches):
        batch = remaining[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        batch_label = f"batch {i + 1}/{num_batches}"

        questions = [s.question.string for s in batch]
        paraphrased_questions = [
            s.paraphrased_question.string for s in batch
        ]

        try:
            question_embeddings = embed_batch_with_retry(
                embedding_service, questions, f"{batch_label} (question)"
            )
            paraphrased_embeddings = embed_batch_with_retry(
                embedding_service,
                paraphrased_questions,
                f"{batch_label} (paraphrased_question)",
            )
        except Exception as e:
            errors += len(batch)
            logger.error(f"Failed on {batch_label}: {e}")
            continue

        for sample, q_emb, p_emb in zip(
            batch, question_embeddings, paraphrased_embeddings, strict=True
        ):
            results.samples.append(
                QuestionEmbedding(
                    id=sample.id,
                    question_embedding=q_emb,
                    paraphrased_question_embedding=p_emb,
                )
            )
            processed_ids.add(sample.id)

        done = len(processed_ids)
        print(f"Progress: {done}/{total} ({errors} errors) - {batch_label}")

        # Periodic save
        output_file.write_text(
            results.model_dump_json(indent=2), encoding="utf-8"
        )

    # Final save
    output_file.write_text(results.model_dump_json(indent=2), encoding="utf-8")

    print(
        f"Done! {len(results.samples)} embeddings saved to {output_file}"
    )
    if errors:
        print(f"Warning: {errors} samples failed.")


if __name__ == "__main__":
    main()
