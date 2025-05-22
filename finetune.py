#Imports & constants
import os
import torch
from datasets import Dataset
from PIL import Image
from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)
from peft import LoraConfig, get_peft_model

# Paths inside container
BASE_DIR       = "test_data/pages/washingtondb-v1.0"
TRANSCRIPT_TXT = os.path.join(BASE_DIR, "ground_truth", "transcription.txt")
LINE_DIR       = os.path.join(BASE_DIR, "data",      "line_images_normalized")
WORD_DIR       = os.path.join(BASE_DIR, "data",      "word_images_normalized")
SETS_DIR       = os.path.join(BASE_DIR, "sets")

from transformers import (
    AutoImageProcessor,
    AutoTokenizer,
    VisionEncoderDecoderModel,
)

image_processor = AutoImageProcessor.from_pretrained(
    "microsoft/trocr-base-handwritten"
)
tokenizer       = AutoTokenizer.from_pretrained(
    "microsoft/trocr-base-handwritten"
)
model           = VisionEncoderDecoderModel.from_pretrained(
    "microsoft/trocr-base-handwritten"
)

#Build a Dataset from Washington DB
records = []
with open(TRANSCRIPT_TXT, encoding="utf-8") as f:
    for line in f:
        line_id, txt = line.strip().split(" ", 1)
        img_path = os.path.join(LINE_DIR, f"{line_id}.png")
        records.append({
            "image_path": img_path,
            "transcript": txt.replace("|", " ")
        })

ds = Dataset.from_list(records)

def attach_image(example):
    example["image"] = Image.open(example["image_path"]).convert("RGB")
    return example

ds = ds.map(attach_image)

#Split into train & validation
split = ds.train_test_split(test_size=0.1, seed=42)
train_ds, val_ds = split["train"], split["test"]

#Load base model & optionally wrap with LoRA
MODEL_NAME = "microsoft/trocr-base-handwritten"
processor  = TrOCRProcessor.from_pretrained(MODEL_NAME)
model      = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)

#Optional: parameter-efficient fine-tuning
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none"
)
model = get_peft_model(model, peft_config)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

from PIL import Image

def preprocess_batch(batch):
    imgs = [Image.open(p).convert("RGB") for p in batch["image_path"]]

    pixel_values = image_processor(
        images=imgs,
        return_tensors="pt"
    ).pixel_values

    tokenized = tokenizer(
        batch["transcript"],
        padding="max_length",
        truncation=True,
        max_length=128,
        return_tensors="pt",
    )

    return {
        "pixel_values": pixel_values,
        "labels":       tokenized.input_ids,
    }

train_ds = train_ds.map(preprocess_batch, batched=True, remove_columns=["image_path","image","transcript"])
val_ds   = val_ds.map(preprocess_batch, batched=True, remove_columns=["image_path","image","transcript"])

#Training arguments & Trainer
output_dir = "app/models/trocr-finetuned"
training_args = Seq2SeqTrainingArguments(
    output_dir=output_dir,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    learning_rate=5e-5,
    num_train_epochs=3,
    logging_steps=100,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    predict_with_generate=True,
)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    tokenizer=processor,
)

#Run training & save
if __name__ == "__main__":
    trainer.train()
    # This will write:
    #   app/models/trocr-finetuned/config.json
    #   app/models/trocr-finetuned/pytorch_model.bin
    #   app/models/trocr-finetuned/preprocessor_config.json
    model.save_pretrained(output_dir)
    processor.save_pretrained(output_dir)
    print(f"Fine-tuned model saved to {output_dir}")