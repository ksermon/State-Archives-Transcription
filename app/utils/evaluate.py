#!/usr/bin/env python
import argparse
import torch
from datasets import load_dataset
import evaluate
from transformers import VisionEncoderDecoderModel, AutoProcessor
from PIL import Image
from tqdm import tqdm

def preprocess_batch(batch, processor):
    # load and preprocess images
    images = [Image.open(path).convert("RGB") for path in batch["image_path"]]
    pixel_values = processor(images=images, return_tensors="pt").pixel_values
    batch["pixel_values"] = pixel_values
    # ground-truth transcription is already in batch["ground_truth"]
    return batch

def evaluate_model(
    model_dir: str,
    dataset_name: str,
    dataset_config: str,
    split: str,
    batch_size: int,
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 1) load model & processor
    model = VisionEncoderDecoderModel.from_pretrained(model_dir).to(device)
    processor = AutoProcessor.from_pretrained(model_dir)

    # 2) load IAM test set
    ds = load_dataset(dataset_name, dataset_config, split=split)

    # 3) preprocess (this adds pixel_values to each example)
    ds = ds.map(
        lambda ex: preprocess_batch(ex, processor),
        batched=True,
        remove_columns=ds.column_names,
    )

    # 4) set up metrics
    cer_metric = evaluate.load("cer")
    wer_metric = evaluate.load("wer")

    # 5) batches of inference
    for i in range(0, len(ds), batch_size):
        batch = ds[i : i + batch_size]
        pixel_values = torch.stack(batch["pixel_values"]).to(device)
        with torch.no_grad():
            outs = model.generate(pixel_values)
        # decode predictions
        preds = [
            processor.tokenizer.decode(ids, skip_special_tokens=True)
            for ids in outs
        ]
        refs = batch["ground_truth"]

        cer_metric.add_batch(predictions=preds, references=refs)
        wer_metric.add_batch(predictions=preds, references=refs)

    # 6) compute & report
    cer = cer_metric.compute()["cer"]
    wer = wer_metric.compute()["wer"]
    print(f"→ CER: {cer:.4f}")
    print(f"→ WER: {wer:.4f}")
    return cer, wer

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Evaluate TrOCR on IAM test set")
    p.add_argument(
        "--model-dir",
        default="app/models/trocr-base-handwritten-local",
        help="path to your fine-tuned model/processor",
    )
    p.add_argument(
        "--dataset-name",
        default="iam",
        help="HuggingFace dataset name (e.g. “iam”)",
    )
    p.add_argument(
        "--dataset-config",
        default="lines",
        help="split/config of IAM (e.g. “words”, “lines”)",
    )
    p.add_argument("--split", default="test", help="which split to evaluate")
    p.add_argument("--batch-size", type=int, default=8, help="inference batch size")
    args = p.parse_args()

    evaluate_model(
        args.model_dir,
        args.dataset_name,
        args.dataset_config,
        args.split,
        args.batch_size,
    )